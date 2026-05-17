from datetime import UTC, datetime

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db.models import Analysis, User
from app.main import app
from app.persistence.analyses import record_run, revoke_share_slug, set_share_slug, upsert_analysis


async def _seed_public_analysis(db) -> str:
    u = User(github_id=1, github_login="owner")
    db.add(u)
    await db.flush()
    a = await upsert_analysis(db, user_id=u.id, target_login="octocat")
    await record_run(
        db, analysis_id=a.id, report_json={"username": "octocat", "total": 80},
        total_score=80, tier_name="Senior Engineer", scores_hash="h",
        started_at=datetime.now(UTC), completed_at=datetime.now(UTC), latency_ms=10,
    )
    slug = await set_share_slug(db, analysis_id=a.id, owner_id=u.id)
    await db.commit()
    return slug


async def test_share_returns_report_and_owner(db):
    slug = await _seed_public_analysis(db)
    from app.db.session import get_db
    async def _o(): yield db
    app.dependency_overrides[get_db] = _o
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.get(f"/share/{slug}")
    app.dependency_overrides.clear()
    assert r.status_code == 200
    body = r.json()
    assert body["report"]["total"] == 80
    assert body["owner"]["login"] == "owner"
    assert "shared_at" in body


async def test_share_unknown_slug_returns_404(db):
    from app.db.session import get_db
    async def _o(): yield db
    app.dependency_overrides[get_db] = _o
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.get("/share/nope12345xyz")
    app.dependency_overrides.clear()
    assert r.status_code == 404


async def test_revoked_share_returns_404(db):
    slug = await _seed_public_analysis(db)
    a = await db.scalar(select(Analysis).where(Analysis.share_slug == slug))
    await revoke_share_slug(db, analysis_id=a.id, owner_id=a.user_id)
    await db.commit()
    from app.db.session import get_db
    async def _o(): yield db
    app.dependency_overrides[get_db] = _o
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.get(f"/share/{slug}")
    app.dependency_overrides.clear()
    assert r.status_code == 404
