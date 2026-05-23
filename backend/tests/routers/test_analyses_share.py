import base64
import secrets

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.auth.sessions import create_session
from app.db.models import Analysis, User
from app.main import app
from app.persistence.analyses import upsert_analysis


async def _setup(db, monkeypatch):
    monkeypatch.setenv(
        "SESSION_TOKEN_ENC_KEY", base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    )
    u = User(github_id=1, github_login="o")
    db.add(u)
    await db.flush()
    sid = await create_session(db, user_id=u.id, github_access_token="t", ttl_days=30)
    a = await upsert_analysis(db, user_id=u.id, target_login="x")
    await db.commit()
    return sid, a.id


async def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_share_creates_slug(db, monkeypatch):
    sid, aid = await _setup(db, monkeypatch)
    from app.db.session import get_db

    async def _o():
        yield db

    app.dependency_overrides[get_db] = _o

    async with await _client() as ac:
        ac.cookies.set("si_session", sid)
        r = await ac.post(f"/analyses/{aid}/share")
    app.dependency_overrides.clear()
    assert r.status_code == 200
    body = r.json()
    assert len(body["share_slug"]) == 12
    assert body["share_url"].endswith(f"/share/{body['share_slug']}")


async def test_revoke_share_returns_204(db, monkeypatch):
    sid, aid = await _setup(db, monkeypatch)
    from app.db.session import get_db

    async def _o():
        yield db

    app.dependency_overrides[get_db] = _o

    async with await _client() as ac:
        ac.cookies.set("si_session", sid)
        await ac.post(f"/analyses/{aid}/share")
        r = await ac.delete(f"/analyses/{aid}/share")
    app.dependency_overrides.clear()
    assert r.status_code == 204
    row = await db.scalar(select(Analysis).where(Analysis.id == aid))
    assert row.share_slug is None
    assert row.is_public is False


async def test_share_wrong_owner_returns_403(db, monkeypatch):
    _sid_owner, aid = await _setup(db, monkeypatch)
    u2 = User(github_id=99, github_login="other")
    db.add(u2)
    await db.flush()
    sid_other = await create_session(db, user_id=u2.id, github_access_token="t", ttl_days=30)
    await db.commit()
    from app.db.session import get_db

    async def _o():
        yield db

    app.dependency_overrides[get_db] = _o

    async with await _client() as ac:
        ac.cookies.set("si_session", sid_other)
        r = await ac.post(f"/analyses/{aid}/share")
    app.dependency_overrides.clear()
    assert r.status_code == 403
