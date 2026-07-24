import secrets
from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient


async def _client():
    from app.main import app

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_cron_missing_auth_returns_401(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", secrets.token_hex(16))
    # Force settings reload by clearing the cached singleton.
    from app import settings as settings_module

    settings_module.settings = settings_module.Settings()

    async with await _client() as ac:
        r = await ac.post("/cron/refresh-saved-analyses")
    assert r.status_code == 401
    assert r.json() == {"detail": "Unauthorized"}


async def test_cron_get_is_routed_not_405(monkeypatch):
    # Regression: Vercel Cron fires the path with GET. The route must accept GET
    # and reach require_cron_auth (401 without a bearer) rather than 405'ing
    # because it was POST-only. A 401 here proves GET is routed to the handler.
    monkeypatch.setenv("CRON_SECRET", secrets.token_hex(16))
    from app import settings as settings_module

    settings_module.settings = settings_module.Settings()

    async with await _client() as ac:
        r = await ac.get("/cron/refresh-saved-analyses")
    assert r.status_code == 401
    assert r.json() == {"detail": "Unauthorized"}


async def test_cron_wrong_bearer_returns_401(monkeypatch):
    expected = secrets.token_hex(16)
    monkeypatch.setenv("CRON_SECRET", expected)
    from app import settings as settings_module

    settings_module.settings = settings_module.Settings()

    async with await _client() as ac:
        r = await ac.post(
            "/cron/refresh-saved-analyses",
            headers={"Authorization": "Bearer not-the-real-secret"},
        )
    assert r.status_code == 401


async def test_cron_unset_secret_returns_503(monkeypatch):
    monkeypatch.delenv("CRON_SECRET", raising=False)
    from app import settings as settings_module

    settings_module.settings = settings_module.Settings()

    async with await _client() as ac:
        r = await ac.post(
            "/cron/refresh-saved-analyses",
            headers={"Authorization": "Bearer anything"},
        )
    assert r.status_code == 503
    assert r.json() == {"detail": "cron_disabled"}


async def test_cron_correct_bearer_runs_chunk(monkeypatch):
    secret = "the-real-secret"
    monkeypatch.setenv("CRON_SECRET", secret)
    from app import settings as settings_module

    settings_module.settings = settings_module.Settings()

    from app.cron.refresh import RefreshChunkSummary

    canned = RefreshChunkSummary(
        processed=2,
        succeeded=2,
        skipped=0,
        rate_limited=0,
        deadline_reached=False,
    )

    # The router does `from app.cron import run_refresh_chunk`, which binds
    # the name into app.routers.cron's namespace. Patch THAT binding — patching
    # app.cron.run_refresh_chunk would only affect new importers.
    from app.routers import cron as cron_router

    monkeypatch.setattr(cron_router, "run_refresh_chunk", AsyncMock(return_value=canned))
    monkeypatch.setattr(cron_router, "purge_expired_sessions", AsyncMock(return_value=3))

    # Bypass the db dependency.
    from app.db.session import get_db
    from app.main import app

    async def _stub_db():
        class _DummyAsyncSession:
            async def commit(self):
                return None

            async def rollback(self):
                return None

            async def close(self):
                return None

        yield _DummyAsyncSession()

    app.dependency_overrides[get_db] = _stub_db

    async with await _client() as ac:
        r = await ac.post(
            "/cron/refresh-saved-analyses",
            headers={"Authorization": f"Bearer {secret}"},
        )

    app.dependency_overrides.clear()

    assert r.status_code == 200
    body = r.json()
    assert body["processed"] == 2
    assert body["succeeded"] == 2
    assert body["skipped"] == 0
    assert body["rate_limited"] == 0
    assert body["deadline_reached"] is False
    # v1.0.7 SI-18: the who-analyzed-whom mapping must not ride in the response
    # body (it would land in Vercel/CDN access logs + Sentry request captures).
    assert "outcomes" not in body
    assert "owner_user_id" not in r.text
    assert "target_login" not in r.text
    assert body["purged_sessions"] == 3
