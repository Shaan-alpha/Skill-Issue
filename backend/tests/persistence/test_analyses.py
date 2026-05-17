from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.db.models import Analysis, User
from app.persistence.analyses import (
    AnalysisNotFound,
    get_analysis_by_slug,
    list_user_analyses,
    record_run,
    revoke_share_slug,
    set_share_slug,
    upsert_analysis,
)


async def _user(db, gh_id=1, login="u") -> User:
    u = User(github_id=gh_id, github_login=login); db.add(u); await db.flush()
    return u


async def test_upsert_insert_new_analysis(db):
    u = await _user(db)
    a = await upsert_analysis(db, user_id=u.id, target_login="octocat", target_github_id=583231)
    assert a.target_login == "octocat"
    assert a.target_github_id == 583231
    assert a.is_public is False


async def test_upsert_returns_existing_on_same_user_target(db):
    u = await _user(db)
    a1 = await upsert_analysis(db, user_id=u.id, target_login="o")
    a2 = await upsert_analysis(db, user_id=u.id, target_login="o")
    assert a1.id == a2.id


async def test_record_run_attaches_run_and_updates_latest(db):
    u = await _user(db); a = await upsert_analysis(db, user_id=u.id, target_login="t")
    run = await record_run(
        db, analysis_id=a.id, report_json={"k": "v"}, total_score=72,
        tier_name="Senior Engineer", scores_hash="h",
        started_at=datetime.now(UTC), completed_at=datetime.now(UTC),
        latency_ms=1234,
    )
    assert run.analysis_id == a.id
    refreshed = await db.scalar(select(Analysis).where(Analysis.id == a.id))
    assert refreshed.latest_run_id == run.id


async def test_set_share_slug_marks_public_and_returns_slug(db):
    u = await _user(db); a = await upsert_analysis(db, user_id=u.id, target_login="t")
    slug = await set_share_slug(db, analysis_id=a.id, owner_id=u.id)
    assert len(slug) == 12
    refreshed = await db.scalar(select(Analysis).where(Analysis.id == a.id))
    assert refreshed.is_public is True
    assert refreshed.share_slug == slug


async def test_set_share_slug_resharing_rotates_slug(db):
    u = await _user(db); a = await upsert_analysis(db, user_id=u.id, target_login="t")
    s1 = await set_share_slug(db, analysis_id=a.id, owner_id=u.id)
    await revoke_share_slug(db, analysis_id=a.id, owner_id=u.id)
    s2 = await set_share_slug(db, analysis_id=a.id, owner_id=u.id)
    assert s1 != s2


async def test_set_share_slug_wrong_owner_raises(db):
    u1 = await _user(db, 1, "u1"); u2 = await _user(db, 2, "u2")
    a = await upsert_analysis(db, user_id=u1.id, target_login="t")
    with pytest.raises(AnalysisNotFound):
        await set_share_slug(db, analysis_id=a.id, owner_id=u2.id)


async def test_get_by_slug_returns_only_public(db):
    u = await _user(db); a = await upsert_analysis(db, user_id=u.id, target_login="t")
    assert await get_analysis_by_slug(db, "nope") is None
    slug = await set_share_slug(db, analysis_id=a.id, owner_id=u.id)
    got = await get_analysis_by_slug(db, slug)
    assert got is not None
    await revoke_share_slug(db, analysis_id=a.id, owner_id=u.id)
    assert await get_analysis_by_slug(db, slug) is None


async def test_list_user_analyses_sorts_by_latest_run_desc(db):
    u = await _user(db)
    a1 = await upsert_analysis(db, user_id=u.id, target_login="early")
    await record_run(db, analysis_id=a1.id, report_json={}, total_score=50, tier_name="X",
                    scores_hash="h", started_at=datetime(2026, 5, 1, tzinfo=UTC),
                    completed_at=datetime(2026, 5, 1, tzinfo=UTC), latency_ms=1)
    a2 = await upsert_analysis(db, user_id=u.id, target_login="later")
    await record_run(db, analysis_id=a2.id, report_json={}, total_score=80, tier_name="Y",
                    scores_hash="h", started_at=datetime(2026, 5, 15, tzinfo=UTC),
                    completed_at=datetime(2026, 5, 15, tzinfo=UTC), latency_ms=1)
    rows, total = await list_user_analyses(db, user_id=u.id, sort="recent", page=1, page_size=20)
    assert total == 2
    assert [r.target_login for r in rows] == ["later", "early"]


async def test_list_user_analyses_sort_score_desc(db):
    u = await _user(db)
    a1 = await upsert_analysis(db, user_id=u.id, target_login="lo")
    await record_run(db, analysis_id=a1.id, report_json={}, total_score=20, tier_name="X",
                    scores_hash="h", started_at=datetime.now(UTC),
                    completed_at=datetime.now(UTC), latency_ms=1)
    a2 = await upsert_analysis(db, user_id=u.id, target_login="hi")
    await record_run(db, analysis_id=a2.id, report_json={}, total_score=90, tier_name="X",
                    scores_hash="h", started_at=datetime.now(UTC),
                    completed_at=datetime.now(UTC), latency_ms=1)
    rows, _ = await list_user_analyses(db, user_id=u.id, sort="score_desc", page=1, page_size=20)
    assert [r.target_login for r in rows] == ["hi", "lo"]
