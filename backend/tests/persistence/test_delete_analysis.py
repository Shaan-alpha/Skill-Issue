from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.db.models import Narrative, User
from app.persistence.analyses import (
    AnalysisNotFound,
    delete_analysis,
    record_run,
    set_share_slug,
    upsert_analysis,
)


async def _make_user(db, github_id: int = 1, login: str = "owner") -> User:
    u = User(github_id=github_id, github_login=login)
    db.add(u)
    await db.flush()
    return u


async def _make_run(db, analysis_id: int):
    now = datetime.now(UTC)
    return await record_run(
        db,
        analysis_id=analysis_id,
        report_json={"username": "x"},
        total_score=50,
        tier_name="Hobbyist",
        scores_hash="h",
        started_at=now,
        completed_at=now,
        latency_ms=10,
    )


async def test_delete_removes_analysis_and_runs(db):
    user = await _make_user(db)
    a = await upsert_analysis(db, user_id=user.id, target_login="octocat")
    run = await _make_run(db, a.id)
    db.add(Narrative(analysis_run_id=run.id, mode="roast", text="t", provider="groq"))
    await db.flush()

    removed = await delete_analysis(db, analysis_id=a.id, owner_id=user.id)

    assert removed is None  # was private
    assert await db.get(type(a), a.id) is None
    assert await db.get(type(run), run.id) is None  # cascade


async def test_delete_returns_slug_when_public(db):
    user = await _make_user(db, github_id=2, login="owner2")
    a = await upsert_analysis(db, user_id=user.id, target_login="torvalds")
    slug = await set_share_slug(db, analysis_id=a.id, owner_id=user.id)

    removed = await delete_analysis(db, analysis_id=a.id, owner_id=user.id)

    assert removed == slug


async def test_delete_rejects_non_owner(db):
    owner = await _make_user(db, github_id=3, login="owner3")
    other = await _make_user(db, github_id=4, login="other")
    a = await upsert_analysis(db, user_id=owner.id, target_login="octocat")

    with pytest.raises(AnalysisNotFound):
        await delete_analysis(db, analysis_id=a.id, owner_id=other.id)
