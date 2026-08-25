from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from app.models import Report, ScoreBreakdown, ScoreResult, TierInfo
from app.narrative.budget import DailyBudget
from app.narrative.cache import NarrativeCache
from app.narrative.llm import FakeNarrativeLLM
from app.narrative.service import NarrativeService, NarrativeStreamMeta


class _BoomLLM(FakeNarrativeLLM):
    """Stub LLM whose stream raises before yielding anything."""

    def __init__(self) -> None:
        super().__init__(tokens=[])
        self.calls = 0

    async def stream_chat(self, messages, **kwargs):  # type: ignore[no-untyped-def, override]
        self.calls += 1
        raise RuntimeError("provider 502")
        yield ""  # pragma: no cover - keeps function a generator


def _report(username: str = "octo", total: int = 50) -> Report:
    z = ScoreResult(points=0, max_points=1)
    b = ScoreBreakdown(
        repo_quality=z,
        engineering_maturity=z,
        oss_collab=z,
        consistency=z,
        recruiter_signal=z,
        learning_trajectory=z,
    )
    return Report(
        username=username,
        tier=TierInfo(
            name="Professional Developer",
            sub_rank=50,
            band=(50, 65),
            next_tier="Senior Engineer",
            pts_to_next=5,
            prev_tier="Entry-Level Engineer",
            pts_above_prev=10,
        ),
        badges=[],
        breakdown=b,
        total=total,
        generated_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_service_returns_cached_narrative_immediately() -> None:
    cache = NarrativeCache()
    rep = _report("octo", 50)
    key = cache.key(rep.username, cache.scores_hash(rep), "roast")
    cache.put(key, "Cached roast!")
    budget = DailyBudget(limit=10)
    llm = FakeNarrativeLLM(tokens=["Never", " called"])
    svc = NarrativeService(cache=cache, budget=budget, llm=llm)

    out: list[str] = []
    async for chunk in svc.stream_narrative("roast", rep):
        out.append(chunk)
    assert "".join(out) == "Cached roast!"
    assert llm.calls == 0


@pytest.mark.asyncio
async def test_service_uses_fallback_when_budget_exhausted() -> None:
    cache = NarrativeCache()
    budget = DailyBudget(limit=0)  # Exhausted
    llm = FakeNarrativeLLM(tokens=["Never", " called"])
    svc = NarrativeService(cache=cache, budget=budget, llm=llm)

    out: list[str] = []
    async for chunk in svc.stream_narrative("roast", _report("octo", 50)):
        out.append(chunk)
    res = "".join(out)
    assert "[AI narrator offline" in res
    assert llm.calls == 0


@pytest.mark.asyncio
async def test_service_forwards_configured_output_token_cap() -> None:
    """Regression: the cap must reach the provider call.

    On Groq's gpt-oss reasoning models the model's thinking is drawn from the
    same completion budget as the visible answer. The previous hardcoded 600 —
    sized for the non-reasoning llama-3.3-70b — left roughly 90-190 tokens for
    prose and truncated every narrative mid-sentence in production. If this
    value stops being plumbed through, that regression returns silently: the
    stream still ends cleanly, it just ends early.
    """
    cache = NarrativeCache()
    budget = DailyBudget(limit=10)
    llm = FakeNarrativeLLM(tokens=["ok"])
    svc = NarrativeService(cache=cache, budget=budget, llm=llm, max_output_tokens=1500)

    async for _ in svc.stream_narrative("roast", _report("octo", 50)):
        pass

    assert llm.last_max_output_tokens == 1500


@pytest.mark.asyncio
async def test_service_default_cap_leaves_room_for_reasoning_plus_prose() -> None:
    """The default must clear the longest prompt target plus reasoning overhead.

    Roast asks for 250-350 words (~475 tokens at 4 chars/token); reasoning at
    the provider's default `medium` effort consumed ~400-500 tokens in the
    2026-08-19 incident. 600 could not cover both.
    """
    cache = NarrativeCache()
    budget = DailyBudget(limit=10)
    llm = FakeNarrativeLLM(tokens=["ok"])
    svc = NarrativeService(cache=cache, budget=budget, llm=llm)

    async for _ in svc.stream_narrative("roast", _report("octo", 50)):
        pass

    assert llm.last_max_output_tokens >= 1000


@pytest.mark.asyncio
async def test_service_streams_from_llm_and_caches_result() -> None:
    cache = NarrativeCache()
    budget = DailyBudget(limit=10)
    llm = FakeNarrativeLLM(tokens=["Live", " ", "narrative", "!"])
    svc = NarrativeService(cache=cache, budget=budget, llm=llm)

    rep = _report("octo", 50)
    out: list[str] = []
    async for chunk in svc.stream_narrative("roast", rep):
        out.append(chunk)
    assert "".join(out) == "Live narrative!"
    assert llm.calls == 1
    assert budget._remaining == 9

    key = cache.key(rep.username, cache.scores_hash(rep), "roast")
    assert cache.get(key) == "Live narrative!"


@pytest.mark.asyncio
async def test_service_uses_error_fallback_when_llm_raises() -> None:
    cache = NarrativeCache()
    budget = DailyBudget(limit=10)
    llm = _BoomLLM()
    svc = NarrativeService(cache=cache, budget=budget, llm=llm)

    rep = _report("octo", 50)
    out: list[str] = []
    async for chunk in svc.stream_narrative("roast", rep):
        out.append(chunk)
    res = "".join(out)
    assert "upstream hiccup" in res
    assert "daily cap reached" not in res
    assert llm.calls == 1
    # Failed runs must not poison the cache.
    key = cache.key(rep.username, cache.scores_hash(rep), "roast")
    assert cache.get(key) is None


@pytest.mark.asyncio
async def test_stream_meta_flags_budget_fallback() -> None:
    """meta.is_fallback must fire when budget is exhausted."""
    cache = NarrativeCache()
    budget = DailyBudget(limit=0)
    llm = FakeNarrativeLLM(tokens=["never"])
    svc = NarrativeService(cache=cache, budget=budget, llm=llm)
    meta = NarrativeStreamMeta()

    async for _ in svc.stream_narrative("roast", _report("octo", 50), meta=meta):
        pass

    assert meta.is_fallback is True
    assert meta.fallback_reason == "budget"
    assert meta.cache_hit is False


@pytest.mark.asyncio
async def test_stream_meta_flags_error_fallback() -> None:
    """meta.is_fallback must fire when the upstream LLM raises."""
    cache = NarrativeCache()
    budget = DailyBudget(limit=10)
    svc = NarrativeService(cache=cache, budget=budget, llm=_BoomLLM())
    meta = NarrativeStreamMeta()

    async for _ in svc.stream_narrative("roast", _report("octo", 50), meta=meta):
        pass

    assert meta.is_fallback is True
    assert meta.fallback_reason == "error"


@pytest.mark.asyncio
async def test_stream_meta_clean_on_live_stream() -> None:
    """A successful live stream must NOT flag fallback."""
    cache = NarrativeCache()
    budget = DailyBudget(limit=10)
    llm = FakeNarrativeLLM(tokens=["live", " text"])
    svc = NarrativeService(cache=cache, budget=budget, llm=llm)
    meta = NarrativeStreamMeta()

    async for _ in svc.stream_narrative("roast", _report("octo", 50), meta=meta):
        pass

    assert meta.is_fallback is False
    assert meta.fallback_reason is None
    assert meta.cache_hit is False


@pytest.mark.asyncio
async def test_stream_meta_flags_cache_hit() -> None:
    """meta.cache_hit must fire when the narrative comes from cache."""
    cache = NarrativeCache()
    rep = _report("octo", 50)
    cache.put(cache.key(rep.username, cache.scores_hash(rep), "roast"), "cached body")
    budget = DailyBudget(limit=10)
    llm = FakeNarrativeLLM(tokens=["never"])
    svc = NarrativeService(cache=cache, budget=budget, llm=llm)
    meta = NarrativeStreamMeta()

    async for _ in svc.stream_narrative("roast", rep, meta=meta):
        pass

    assert meta.cache_hit is True
    assert meta.is_fallback is False
    assert llm.calls == 0


@pytest.mark.asyncio
async def test_refund_delegates_to_budget() -> None:
    from app.narrative.service import NarrativeService

    calls: dict[str, tuple] = {}

    class _Budget:
        async def arefund(self, *, subject=None, consumed_day=None):
            calls["args"] = (subject, consumed_day)

    svc = NarrativeService(cache=object(), budget=_Budget(), llm=object())
    await svc.refund(subject="ip:1.2.3.4", consumed_day="2026-07-24")
    assert calls["args"] == ("ip:1.2.3.4", "2026-07-24")


# --- Empty and truncated streams (v1.0.12) ---


@pytest.mark.asyncio
async def test_empty_stream_falls_back_instead_of_yielding_nothing() -> None:
    """A reasoning model can spend its whole budget thinking and emit no prose.
    Yielding nothing renders a blank card; serve the fallback instead."""
    cache = NarrativeCache()
    budget = DailyBudget(limit=10)
    llm = FakeNarrativeLLM(tokens=[])
    svc = NarrativeService(cache=cache, budget=budget, llm=llm)

    meta = NarrativeStreamMeta()
    out = "".join([c async for c in svc.stream_narrative("roast", _report(), meta=meta)])

    assert out != ""
    assert "[AI narrator offline" in out
    assert meta.is_fallback is True
    assert meta.fallback_reason == "error"


@pytest.mark.asyncio
async def test_empty_stream_is_never_cached() -> None:
    """Caching '' poisons the key for the full 24h TTL, because `aget` returns
    '' and the service treats any non-None value as a hit."""
    cache = NarrativeCache()
    budget = DailyBudget(limit=10)
    llm = FakeNarrativeLLM(tokens=[])
    svc = NarrativeService(cache=cache, budget=budget, llm=llm)

    report = _report()
    async for _ in svc.stream_narrative("roast", report):
        pass

    key = cache.key(report.username, cache.scores_hash(report), "roast")
    assert await cache.aget(key) is None


@pytest.mark.asyncio
async def test_truncated_stream_is_flagged_and_not_cached() -> None:
    """A guillotined narrative must not be served from cache for 24h as though
    it were complete."""
    cache = NarrativeCache()
    budget = DailyBudget(limit=10)
    llm = FakeNarrativeLLM(tokens=["Half a roast that stops mid-"], finish_reason="length")
    svc = NarrativeService(cache=cache, budget=budget, llm=llm)

    report = _report()
    meta = NarrativeStreamMeta()
    out = "".join([c async for c in svc.stream_narrative("roast", report, meta=meta)])

    assert out == "Half a roast that stops mid-"
    assert meta.truncated is True
    key = cache.key(report.username, cache.scores_hash(report), "roast")
    assert await cache.aget(key) is None


@pytest.mark.asyncio
async def test_complete_stream_is_still_cached_and_unflagged() -> None:
    cache = NarrativeCache()
    budget = DailyBudget(limit=10)
    llm = FakeNarrativeLLM(tokens=["A whole roast."], finish_reason="stop")
    svc = NarrativeService(cache=cache, budget=budget, llm=llm)

    report = _report()
    meta = NarrativeStreamMeta()
    async for _ in svc.stream_narrative("roast", report, meta=meta):
        pass

    assert meta.truncated is False
    key = cache.key(report.username, cache.scores_hash(report), "roast")
    assert await cache.aget(key) == "A whole roast."


@pytest.mark.asyncio
async def test_service_forwards_reasoning_effort() -> None:
    """Thinking is billed from the same budget as the prose, so effort must be
    turned down or the visible answer gets squeezed out."""
    cache = NarrativeCache()
    budget = DailyBudget(limit=10)
    llm = FakeNarrativeLLM(tokens=["x"], finish_reason="stop")
    svc = NarrativeService(cache=cache, budget=budget, llm=llm, reasoning_effort="low")

    async for _ in svc.stream_narrative("roast", _report()):
        pass

    assert llm.last_reasoning_effort == "low"


# --- Fallback is reported as an alertable signal (v1.0.12) ---


@pytest.mark.asyncio
async def test_upstream_failure_reports_an_alertable_fallback() -> None:
    """The 2026-08-16 model retirement served stand-in text for three days with
    green health checks. The degradation itself must be the signal."""
    cache = NarrativeCache()
    budget = DailyBudget(limit=10)
    svc = NarrativeService(cache=cache, budget=budget, llm=_BoomLLM())

    with patch("app.narrative.service.record_narrative_fallback") as report:
        async for _ in svc.stream_narrative("roast", _report()):
            pass

    assert report.call_count == 1
    assert report.call_args.kwargs["reason"] == "error"


@pytest.mark.asyncio
async def test_empty_completion_reports_an_alertable_fallback() -> None:
    cache = NarrativeCache()
    budget = DailyBudget(limit=10)
    svc = NarrativeService(cache=cache, budget=budget, llm=FakeNarrativeLLM(tokens=[]))

    with patch("app.narrative.service.record_narrative_fallback") as report:
        async for _ in svc.stream_narrative("roast", _report()):
            pass

    assert report.call_args.kwargs["reason"] == "error"


@pytest.mark.asyncio
async def test_budget_exhaustion_reports_as_budget_not_error() -> None:
    """Hitting the cap is capacity behaviour. Reporting it as an error would
    make the real alert noisy enough to ignore."""
    cache = NarrativeCache()
    budget = DailyBudget(limit=0)
    svc = NarrativeService(cache=cache, budget=budget, llm=FakeNarrativeLLM(tokens=["x"]))

    with patch("app.narrative.service.record_narrative_fallback") as report:
        async for _ in svc.stream_narrative("roast", _report()):
            pass

    assert report.call_args.kwargs["reason"] == "budget"


@pytest.mark.asyncio
async def test_healthy_stream_reports_no_fallback() -> None:
    cache = NarrativeCache()
    budget = DailyBudget(limit=10)
    llm = FakeNarrativeLLM(tokens=["A whole roast."], finish_reason="stop")
    svc = NarrativeService(cache=cache, budget=budget, llm=llm)

    with patch("app.narrative.service.record_narrative_fallback") as report:
        async for _ in svc.stream_narrative("roast", _report()):
            pass

    assert report.call_count == 0
