import secrets

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
