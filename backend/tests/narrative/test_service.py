from datetime import UTC, datetime

import pytest

from app.models import Report, ScoreBreakdown, ScoreResult, TierInfo
from app.narrative.budget import DailyBudget
from app.narrative.cache import NarrativeCache
from app.narrative.llm import FakeNarrativeLLM
from app.narrative.service import NarrativeService


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
