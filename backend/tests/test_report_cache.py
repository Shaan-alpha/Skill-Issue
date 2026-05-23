"""Unit tests for the Layer A Report cache wrap in get_report_for_user.

Strategy: monkey-patch _live_ingest so we can count how many times it runs.
First call should hit _live_ingest (cold cache); second call for the same
user should NOT hit it (cache hit).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from app import dependencies as dep_module
from app.dependencies import get_cache, get_report_for_user
from app.models import Report, ScoreBreakdown, ScoreResult, TierInfo


def _stub_report(username: str, total: int = 78) -> Report:
    z = ScoreResult(points=10, max_points=30)
    return Report(
        username=username,
        tier=TierInfo(
            name="Senior Engineer",
            sub_rank=47,
            band=(65, 80),
            next_tier="Staff Engineer",
            pts_to_next=12,
            prev_tier="Professional Developer",
            pts_above_prev=5,
        ),
        badges=[],
        breakdown=ScoreBreakdown(
            repo_quality=z,
            engineering_maturity=z,
            oss_collab=z,
            consistency=z,
            recruiter_signal=z,
            learning_trajectory=z,
        ),
        total=total,
        generated_at=datetime.now(UTC),
    )


@pytest.fixture
def patched_live_ingest(monkeypatch, fake_cache):
    """Patch _live_ingest to return a stub Report and count invocations.
    Also overrides get_cache.cache_clear() and the @lru_cache so the fake
    cache is returned."""
    call_count = {"n": 0}

    async def fake_ingest(username: str, session: Any, cache: Any) -> Report:
        call_count["n"] += 1
        return _stub_report(username)

    monkeypatch.setattr(dep_module, "_live_ingest", fake_ingest)

    # Clear @lru_cache on get_cache and inject the fake.
    get_cache.cache_clear()
    monkeypatch.setattr(dep_module, "get_cache", lambda: fake_cache)

    return call_count


@pytest.mark.asyncio
async def test_cold_call_hits_live_ingest(patched_live_ingest) -> None:
    report = await get_report_for_user("octocat")
    assert report.username == "octocat"
    assert patched_live_ingest["n"] == 1


@pytest.mark.asyncio
async def test_second_call_hits_cache_not_live_ingest(patched_live_ingest) -> None:
    first = await get_report_for_user("octocat")
    second = await get_report_for_user("octocat")
    assert first.username == "octocat"
    assert second.username == "octocat"
    assert first.total == second.total
    # Only one ingest — the second was a cache hit.
    assert patched_live_ingest["n"] == 1


@pytest.mark.asyncio
async def test_case_insensitive_username_cache_lookup(patched_live_ingest) -> None:
    """Shaan-alpha and shaan-alpha must hit the same cache entry."""
    await get_report_for_user("Shaan-alpha")
    await get_report_for_user("shaan-alpha")
    # The cached Report's `username` is whatever the first ingest produced
    # (canonical case "Shaan-alpha" returned by GitHub). Subsequent calls
    # against either case fetch the same row.
    assert patched_live_ingest["n"] == 1


@pytest.mark.asyncio
async def test_invalid_username_returns_400_before_cache(patched_live_ingest) -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        await get_report_for_user("--bad")
    assert exc.value.status_code == 400
    assert patched_live_ingest["n"] == 0


@pytest.mark.asyncio
async def test_no_cache_configured_falls_through(monkeypatch) -> None:
    """When get_cache() returns None, every call hits _live_ingest."""
    call_count = {"n": 0}

    async def fake_ingest(username: str, session: Any, cache: Any) -> Report:
        call_count["n"] += 1
        return _stub_report(username)

    monkeypatch.setattr(dep_module, "_live_ingest", fake_ingest)
    get_cache.cache_clear()
    monkeypatch.setattr(dep_module, "get_cache", lambda: None)

    await get_report_for_user("octocat")
    await get_report_for_user("octocat")
    assert call_count["n"] == 2  # both calls hit the live path
