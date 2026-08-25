from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI

# Models that draw their reasoning from the same completion budget as the
# visible answer, and that accept `reasoning_effort`. The parameter is gated on
# the model name because the OpenAI default path (gpt-4o) rejects it with a 400.
_REASONING_MODEL_MARKERS = ("gpt-oss",)


def supports_reasoning_effort(model: str) -> bool:
    """Whether `model` accepts the `reasoning_effort` parameter."""
    lowered = model.lower()
    return any(marker in lowered for marker in _REASONING_MODEL_MARKERS)


@dataclass
class StreamOutcome:
    """Per-call sink for stream metadata the `str` yield contract can't carry.

    Passed in by the caller rather than kept on the client: `get_narrative_service`
    is `@lru_cache`d, so one `NarrativeLLM` is shared by every concurrent request
    and instance state would race across streams.
    """

    finish_reason: str | None = None

    @property
    def truncated(self) -> bool:
        """True when the model hit the completion ceiling mid-sentence."""
        return self.finish_reason == "length"


class NarrativeLLM:
    """Single-file boundary to OpenAI-compatible chat APIs.

    Passing `base_url` points the client at any OpenAI-compatible endpoint
    (Groq, OpenRouter, Cerebras, vLLM/Ollama for local dev, etc.) so we can
    swap providers without rewriting the streaming pipeline.
    """

    def __init__(self, *, api_key: str, model: str, base_url: str | None = None) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        *,
        max_output_tokens: int = 1200,
        temperature: float = 0.7,
        reasoning_effort: str | None = None,
        outcome: StreamOutcome | None = None,
    ) -> AsyncIterator[str]:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "stream": True,
            "max_tokens": max_output_tokens,
            "temperature": temperature,
        }
        if reasoning_effort is not None and supports_reasoning_effort(self._model):
            kwargs["reasoning_effort"] = reasoning_effort

        stream = await self._client.chat.completions.create(**kwargs)
        async for chunk in stream:
            # Usage-only and keepalive chunks carry an empty `choices` list;
            # indexing [0] on one raises IndexError, which the service would
            # convert into a fallback narrative for an otherwise healthy stream.
            choices = getattr(chunk, "choices", None)
            if not choices:
                continue
            choice = choices[0]

            finish_reason = getattr(choice, "finish_reason", None)
            if finish_reason and outcome is not None:
                outcome.finish_reason = finish_reason

            delta = getattr(choice, "delta", None)
            content = getattr(delta, "content", None) if delta is not None else None
            if content:
                yield content


class FakeNarrativeLLM:
    """Test double. Yields a scripted list of tokens, records calls."""

    def __init__(self, tokens: list[str], *, finish_reason: str | None = None) -> None:
        self._tokens = tokens
        self._finish_reason = finish_reason
        self.calls = 0
        self.last_messages: list[dict[str, str]] | None = None
        self.last_reasoning_effort: str | None = None

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        *,
        max_output_tokens: int = 1200,
        temperature: float = 0.7,
        reasoning_effort: str | None = None,
        outcome: StreamOutcome | None = None,
    ) -> AsyncIterator[str]:
        self.calls += 1
        self.last_messages = messages
        self.last_max_output_tokens = max_output_tokens
        self.last_temperature = temperature
        self.last_reasoning_effort = reasoning_effort
        for tok in self._tokens:
            yield tok
        if outcome is not None and self._finish_reason is not None:
            outcome.finish_reason = self._finish_reason
