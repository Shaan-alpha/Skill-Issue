import pytest

from app.narrative.llm import FakeNarrativeLLM, NarrativeLLM, StreamOutcome


@pytest.mark.asyncio
async def test_fake_llm_yields_scripted_tokens() -> None:
    fake = FakeNarrativeLLM(tokens=["Hello", " ", "world"])
    out: list[str] = []
    async for tok in fake.stream_chat([{"role": "user", "content": "x"}]):
        out.append(tok)
    assert out == ["Hello", " ", "world"]
    assert fake.calls == 1
    assert fake.last_messages == [{"role": "user", "content": "x"}]


@pytest.mark.asyncio
async def test_fake_llm_can_be_called_multiple_times() -> None:
    fake = FakeNarrativeLLM(tokens=["a"])
    async for _ in fake.stream_chat([]):
        pass
    async for _ in fake.stream_chat([]):
        pass
    assert fake.calls == 2


def test_real_client_constructs_without_network() -> None:
    # Smoke: instantiating with an api_key shouldn't make any HTTP calls.
    NarrativeLLM(api_key="sk-test", model="gpt-4o")


# --- Reasoning-model handling (truncation, empty chunks, effort) ---


class _FakeDelta:
    def __init__(self, content: str | None) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str | None = None, finish_reason: str | None = None) -> None:
        self.delta = _FakeDelta(content)
        self.finish_reason = finish_reason


class _FakeChunk:
    def __init__(self, choices: list[_FakeChoice]) -> None:
        self.choices = choices


class _FakeCompletions:
    """Stands in for client.chat.completions, recording create() kwargs."""

    def __init__(self, chunks: list[_FakeChunk]) -> None:
        self._chunks = chunks
        self.last_kwargs: dict = {}

    async def create(self, **kwargs):  # type: ignore[no-untyped-def]
        self.last_kwargs = kwargs

        async def _gen():  # type: ignore[no-untyped-def]
            for c in self._chunks:
                yield c

        return _gen()


def _client_with(chunks: list[_FakeChunk], *, model: str) -> tuple[NarrativeLLM, _FakeCompletions]:
    llm = NarrativeLLM(api_key="sk-test", model=model)
    completions = _FakeCompletions(chunks)
    llm._client.chat.completions = completions  # type: ignore[assignment]
    return llm, completions


async def test_stream_records_length_finish_reason_as_truncated() -> None:
    """A stream guillotined by the token ceiling must be distinguishable from a
    finished one — previously nothing downstream could tell them apart."""
    llm, _ = _client_with(
        [
            _FakeChunk([_FakeChoice(content="Your commit history ")]),
            _FakeChunk([_FakeChoice(content="stops mid-sen")]),
            _FakeChunk([_FakeChoice(finish_reason="length")]),
        ],
        model="openai/gpt-oss-120b",
    )
    outcome = StreamOutcome()
    out = [t async for t in llm.stream_chat([], outcome=outcome)]

    assert "".join(out) == "Your commit history stops mid-sen"
    assert outcome.finish_reason == "length"
    assert outcome.truncated is True


async def test_stream_marks_clean_stop_as_not_truncated() -> None:
    llm, _ = _client_with(
        [
            _FakeChunk([_FakeChoice(content="A complete roast.")]),
            _FakeChunk([_FakeChoice(finish_reason="stop")]),
        ],
        model="openai/gpt-oss-120b",
    )
    outcome = StreamOutcome()
    [t async for t in llm.stream_chat([], outcome=outcome)]

    assert outcome.truncated is False


async def test_stream_survives_chunks_with_no_choices() -> None:
    """Usage/keepalive chunks carry an empty choices list; indexing [0] on one
    raises IndexError, which the service converts into a fallback narrative."""
    llm, _ = _client_with(
        [
            _FakeChunk([_FakeChoice(content="alive")]),
            _FakeChunk([]),  # usage-only chunk
            _FakeChunk([_FakeChoice(content=" and well")]),
        ],
        model="openai/gpt-oss-120b",
    )
    out = [t async for t in llm.stream_chat([])]
    assert "".join(out) == "alive and well"


async def test_reasoning_effort_sent_for_reasoning_models() -> None:
    """gpt-oss bills thinking from the same budget as the prose, so effort must
    be turned down or the visible answer gets squeezed out."""
    llm, completions = _client_with(
        [_FakeChunk([_FakeChoice(content="x", finish_reason="stop")])],
        model="openai/gpt-oss-120b",
    )
    [t async for t in llm.stream_chat([], reasoning_effort="low")]
    assert completions.last_kwargs["reasoning_effort"] == "low"


async def test_reasoning_effort_omitted_for_non_reasoning_models() -> None:
    """gpt-4o rejects reasoning_effort with a 400 — the OpenAI default path must
    never receive it."""
    llm, completions = _client_with(
        [_FakeChunk([_FakeChoice(content="x", finish_reason="stop")])],
        model="gpt-4o",
    )
    [t async for t in llm.stream_chat([], reasoning_effort="low")]
    assert "reasoning_effort" not in completions.last_kwargs
