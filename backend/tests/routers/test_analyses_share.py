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


async def test_share_post_schedules_revalidation(db, monkeypatch):
    """v0.8.6: share_analysis must enqueue revalidate_share_slug with the new slug."""
    sid, aid = await _setup(db, monkeypatch)

    captured: list[str] = []

    async def fake_revalidate(slug: str) -> None:
        captured.append(slug)

    # Patch where the router imports it — not the source module.
    monkeypatch.setattr("app.routers.analyses.revalidate_share_slug", fake_revalidate)

    from app.db.session import get_db

    async def _o():
        yield db

    app.dependency_overrides[get_db] = _o
    try:
        async with await _client() as ac:
            ac.cookies.set("si_session", sid)
            r = await ac.post(f"/analyses/{aid}/share")
        assert r.status_code == 200
        body = r.json()
        # FastAPI runs BackgroundTasks after the response is sent;
        # AsyncClient/ASGITransport awaits this — so by the time we have
        # `body`, the task has run.
        assert captured == [body["share_slug"]]
    finally:
        app.dependency_overrides.clear()


async def test_revoke_delete_schedules_revalidation_with_removed_slug(db, monkeypatch):
    """v0.8.6: revoke_share must enqueue revalidate_share_slug with the just-removed slug."""
    sid, aid = await _setup(db, monkeypatch)

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
            posted = await ac.post(f"/analyses/{aid}/share")
            new_slug = posted.json()["share_slug"]
            r = await ac.delete(f"/analyses/{aid}/share")
        assert r.status_code == 204
        # POST captured one slug; DELETE captured the same slug being torn down.
        assert captured == [new_slug, new_slug]
    finally:
        app.dependency_overrides.clear()


async def test_revoke_on_already_revoked_does_not_schedule(db, monkeypatch):
    """v0.8.6: if removed_slug is empty (analysis was never shared / already
    revoked), the route must not enqueue a webhook with an empty tag."""
    sid, aid = await _setup(db, monkeypatch)

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
            # DELETE without a prior share — removed_slug is "".
            r = await ac.delete(f"/analyses/{aid}/share")
        assert r.status_code == 204
        assert captured == []
    finally:
        app.dependency_overrides.clear()


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


async def test_share_rejects_foreign_origin(db, monkeypatch):
    # v1.0.8 SI-16: a state-changing mutation from an untrusted Origin is 403'd,
    # even with a valid session cookie.
    sid, aid = await _setup(db, monkeypatch)
    from app.db.session import get_db

    async def _o():
        yield db

    app.dependency_overrides[get_db] = _o
    async with await _client() as ac:
        ac.cookies.set("si_session", sid)
        r = await ac.post(f"/analyses/{aid}/share", headers={"Origin": "https://evil.example.com"})
    app.dependency_overrides.clear()
    assert r.status_code == 403
    assert r.json()["error"] == "bad_origin"
