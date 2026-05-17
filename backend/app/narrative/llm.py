from collections.abc import AsyncIterator

from openai import AsyncOpenAI


class NarrativeLLM:
    """Single-file boundary to OpenAI-compatible chat APIs.

    Passing `base_url` points the client at any OpenAI-compatible endpoint
    (Groq, OpenRouter, Cerebras, vLLM/Ollama for local dev, etc.) so we can
    swap providers without rewriting the streaming pipeline.
    """

    def __init__(
        self, *, api_key: str, model: str, base_url: str | None = None
    ) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        *,
        max_output_tokens: int = 600,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            stream=True,
            max_tokens=max_output_tokens,
            temperature=temperature,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


class FakeNarrativeLLM:
    """Test double. Yields a scripted list of tokens, records calls."""

    def __init__(self, tokens: list[str]) -> None:
        self._tokens = tokens
        self.calls = 0
        self.last_messages: list[dict[str, str]] | None = None

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        *,
        max_output_tokens: int = 600,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        self.calls += 1
        self.last_messages = messages
        self.last_max_output_tokens = max_output_tokens
        self.last_temperature = temperature
        for tok in self._tokens:
            yield tok
