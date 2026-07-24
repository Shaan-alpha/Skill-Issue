from datetime import UTC, datetime

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

    async def stream_chat(self, messages, temperature):  # type: ignore[no-untyped-def, override]
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
