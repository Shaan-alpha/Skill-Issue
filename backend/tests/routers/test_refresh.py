import base64
import secrets

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.auth.sessions import create_session
from app.db.models import User
from app.persistence.analyses import upsert_analysis


async def _setup_signed_in(db, monkeypatch) -> str:
    monkeypatch.setenv(
        "SESSION_TOKEN_ENC_KEY", base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    )
    from app import settings as settings_module

    settings_module.settings = settings_module.Settings()

    u = User(github_id=1, github_login="alice", name="A", avatar_url=None)
    db.add(u)
    await db.flush()
    sid = await create_session(db, user_id=u.id, github_access_token="gh-tok")
    await db.commit()
    return sid


async def _client():
    from app.main import app

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_refresh_without_session_returns_401():
    async with await _client() as ac:
        r = await ac.post("/me/refresh/octocat")
    assert r.status_code == 401


async def test_refresh_unsaved_target_returns_404(db, monkeypatch):
    sid = await _setup_signed_in(db, monkeypatch)
    from app.db.session import get_db
    from app.main import app

    async def _o():
        yield db

    app.dependency_overrides[get_db] = _o

    try:
        async with await _client() as ac:
            ac.cookies.set("si_session", sid)
            r = await ac.post("/me/refresh/never-saved")
        assert r.status_code == 404
        assert r.json() == {"detail": "no_saved_analysis"}
    finally:
        app.dependency_overrides.clear()


async def test_refresh_rate_limit_hits_429_on_11th_call(db, monkeypatch):
    sid = await _setup_signed_in(db, monkeypatch)
    u = await db.scalar(select(User).where(User.github_login == "alice"))
    assert u is not None
    await upsert_analysis(db, user_id=u.id, target_login="octocat")
    await db.commit()

    from app.db.session import get_db
    from app.main import app

    async def _o():
        yield db

    app.dependency_overrides[get_db] = _o

    # Inject a FakeRedis-backed cache so get_cache() returns it.
    from app.cache.client import RedisCache
    from tests.conftest import FakeRedis

    fake = FakeRedis()
    cache = RedisCache(redis=fake)
    monkeypatch.setattr("app.dependencies.get_cache", lambda: cache)
    monkeypatch.setattr("app.routers.refresh.get_cache", lambda: cache, raising=False)

    try:
        async with await _client() as ac:
            ac.cookies.set("si_session", sid)
            # First 10 calls — won't get past Task-6-stub (501) but we only
            # care about the rate-limit decision here, which is checked
            # BEFORE Task 6's pipeline.
            for i in range(10):
                r = await ac.post("/me/refresh/octocat")
                assert r.status_code != 429, f"call {i + 1} unexpectedly rate-limited"
            r11 = await ac.post("/me/refresh/octocat")
        assert r11.status_code == 429
        body = r11.json()
        assert body["detail"] == "rate_limited"
        assert body["retry_after_seconds"] > 0
        assert "retry-after" in {h.lower() for h in r11.headers}
    finally:
        app.dependency_overrides.clear()


async def test_refresh_saved_target_does_not_404_on_ownership(db, monkeypatch):
    """Signed-in user + saved target should NOT hit the 404 ownership branch.
    Will 501 here because Task 6 hasn't wired the live pipeline yet."""
    sid = await _setup_signed_in(db, monkeypatch)
    u = await db.scalar(select(User).where(User.github_login == "alice"))
    assert u is not None
    await upsert_analysis(db, user_id=u.id, target_login="octocat")
    await db.commit()

    from app.db.session import get_db
    from app.main import app

    async def _o():
        yield db

    app.dependency_overrides[get_db] = _o

    try:
        async with await _client() as ac:
            ac.cookies.set("si_session", sid)
            r = await ac.post("/me/refresh/octocat")
        # Anything except 404 with detail="no_saved_analysis" means we got past
        # the ownership check.
        assert not (r.status_code == 404 and r.json() == {"detail": "no_saved_analysis"})
    finally:
        app.dependency_overrides.clear()
