from datetime import UTC, datetime, timedelta

from app.db.models import User
from app.persistence.analyses import record_run, upsert_analysis
from app.persistence.refresh import iter_stale_analyses


async def _user(db, login="alice") -> User:
    u = User(github_id=hash(login) & 0xFFFF, github_login=login, name=login, avatar_url=None)
    db.add(u)
    await db.flush()
    return u


async def _persisted(db, *, user_id: int, target: str, completed_at: datetime | None):
    a = await upsert_analysis(db, user_id=user_id, target_login=target)
    if completed_at is not None:
        await record_run(
            db,
            analysis_id=a.id,
            report_json={"username": target},
            total_score=50,
            tier_name="Hobbyist",
            scores_hash="abc",
            started_at=completed_at - timedelta(seconds=1),
            completed_at=completed_at,
            latency_ms=1000,
        )
    return a


async def test_orders_oldest_first(db):
    user = await _user(db)
    now = datetime.now(UTC)
    await _persisted(db, user_id=user.id, target="fresh", completed_at=now - timedelta(hours=1))
    old = await _persisted(db, user_id=user.id, target="old", completed_at=now - timedelta(days=2))
    oldest = await _persisted(
        db, user_id=user.id, target="oldest", completed_at=now - timedelta(days=10)
    )
    await db.commit()

    rows = await iter_stale_analyses(db, limit=5)
    ids = [r.id for r in rows]
    # "fresh" is within 24h so it's excluded; remaining ordered oldest first.
    assert ids == [oldest.id, old.id]


async def test_analyses_with_no_run_sort_first(db):
    user = await _user(db)
    now = datetime.now(UTC)
    no_run = await _persisted(db, user_id=user.id, target="no-run", completed_at=None)
    old = await _persisted(db, user_id=user.id, target="old", completed_at=now - timedelta(days=3))
    await db.commit()

    rows = await iter_stale_analyses(db, limit=5)
    assert [r.id for r in rows] == [no_run.id, old.id]


async def test_respects_limit(db):
    user = await _user(db)
    now = datetime.now(UTC)
    for i in range(5):
        await _persisted(
            db, user_id=user.id, target=f"stale-{i}", completed_at=now - timedelta(days=i + 1)
        )
    await db.commit()

    rows = await iter_stale_analyses(db, limit=3)
    assert len(rows) == 3
