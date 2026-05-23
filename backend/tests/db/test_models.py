from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Analysis, AnalysisRun, Narrative, Session, User


async def test_user_unique_github_id(db: AsyncSession):
    db.add(User(github_id=1, github_login="alice"))
    db.add(User(github_id=1, github_login="alice2"))
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_analysis_unique_user_target(db: AsyncSession):
    u = User(github_id=2, github_login="bob")
    db.add(u)
    await db.flush()
    db.add(Analysis(user_id=u.id, target_login="octocat"))
    db.add(Analysis(user_id=u.id, target_login="octocat"))
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_narrative_mode_check_constraint(db: AsyncSession):
    u = User(github_id=3, github_login="c")
    db.add(u)
    await db.flush()
    a = Analysis(user_id=u.id, target_login="x")
    db.add(a)
    await db.flush()
    r = AnalysisRun(
        analysis_id=a.id,
        report_json={},
        total_score=50,
        tier_name="X",
        scores_hash="h",
        ingestion_started_at=datetime.now(UTC),
        ingestion_completed_at=datetime.now(UTC),
        ingestion_latency_ms=10,
    )
    db.add(r)
    await db.flush()
    db.add(
        Narrative(
            analysis_run_id=r.id,
            mode="banana",
            text="t",
            provider="openai",
        )
    )
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_user_cascade_deletes_everything(db: AsyncSession):
    u = User(github_id=4, github_login="d")
    db.add(u)
    await db.flush()
    db.add(
        Session(
            id="s1",
            user_id=u.id,
            access_token_ct=b"x",
            access_token_nonce=b"n",
            expires_at=datetime.now(UTC),
        )
    )
    a = Analysis(user_id=u.id, target_login="t")
    db.add(a)
    await db.flush()
    r = AnalysisRun(
        analysis_id=a.id,
        report_json={},
        total_score=1,
        tier_name="X",
        scores_hash="h",
        ingestion_started_at=datetime.now(UTC),
        ingestion_completed_at=datetime.now(UTC),
        ingestion_latency_ms=1,
    )
    db.add(r)
    await db.flush()
    db.add(Narrative(analysis_run_id=r.id, mode="roast", text="t", provider="openai"))
    await db.flush()

    await db.delete(u)
    await db.flush()

    assert (await db.scalar(select(Analysis).where(Analysis.user_id == u.id))) is None
    assert (await db.scalar(select(Session).where(Session.user_id == u.id))) is None
