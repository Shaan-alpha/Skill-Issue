import base64
import secrets

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.auth.sessions import create_session
from app.db.models import Analysis, User
from app.main import app
from app.persistence.analyses import set_share_slug, upsert_analysis


async def _setup(db, monkeypatch, *, github_id: int = 1, login: str = "o"):
    monkeypatch.setenv(
        "SESSION_TOKEN_ENC_KEY", base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    )
    u = User(github_id=github_id, github_login=login)
    db.add(u)
    await db.flush()
    sid = await create_session(db, user_id=u.id, github_access_token="t", ttl_days=30)
    a = await upsert_analysis(db, user_id=u.id, target_login="octocat")
    await db.commit()
    return sid, a.id, u.id


async def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_delete_owned_analysis_returns_204(db, monkeypatch):
    sid, aid, _ = await _setup(db, monkeypatch)
    from app.db.session import get_db

    async def _o():
        yield db

    app.dependency_overrides[get_db] = _o
    try:
        async with await _client() as ac:
            ac.cookies.set("si_session", sid)
            r = await ac.delete(f"/analyses/{aid}")
        assert r.status_code == 204
        row = await db.scalar(select(Analysis).where(Analysis.id == aid))
        assert row is None
    finally:
        app.dependency_overrides.clear()


async def test_delete_not_owned_returns_403(db, monkeypatch):
    _sid_owner, aid, _ = await _setup(db, monkeypatch)
    u2 = User(github_id=99, github_login="other")
    db.add(u2)
    await db.flush()
    sid_other = await create_session(db, user_id=u2.id, github_access_token="t", ttl_days=30)
    await db.commit()
    from app.db.session import get_db

    async def _o():
        yield db

    app.dependency_overrides[get_db] = _o
    try:
        async with await _client() as ac:
            ac.cookies.set("si_session", sid_other)
            r = await ac.delete(f"/analyses/{aid}")
        assert r.status_code == 403
    finally:
        app.dependency_overrides.clear()


async def test_delete_public_analysis_fires_revalidate(db, monkeypatch):
    sid, aid, owner_id = await _setup(db, monkeypatch)
    slug = await set_share_slug(db, analysis_id=aid, owner_id=owner_id)
    await db.commit()

    captured: list[str] = []

    async def fake_revalidate(slug: str) -> None:
        captured.append(slug)

    monkeypatch.setattr("app.routers.analyses.revalidate_share_slug", fake_revalidate)

    from app.db.session import get_db

    async def _o():
        yield db

    app.dependency_overrides[get_db] = _o
    try:
        async with await _client() as ac:
            ac.cookies.set("si_session", sid)
            r = await ac.delete(f"/analyses/{aid}")
        assert r.status_code == 204
        assert captured == [slug]
    finally:
        app.dependency_overrides.clear()
