import pytest

from app.narrative.llm import FakeNarrativeLLM, NarrativeLLM


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
