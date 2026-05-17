from importlib import reload
from urllib.parse import parse_qs, urlparse

from httpx import ASGITransport, AsyncClient

from app.main import app


async def _client() -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=False,
    )


async def test_login_redirects_to_github_with_state(monkeypatch):
    # The route needs github_oauth_client_id and oauth_redirect_url.
    # They are str | None in Settings; the build_authorize_url helper
    # tolerates None with fallback to "" — but the route should still emit
    # a valid querystring with state.
    monkeypatch.setenv("GITHUB_OAUTH_CLIENT_ID", "abc")
    monkeypatch.setenv("OAUTH_REDIRECT_URL", "http://localhost:8000/auth/callback")
    # Reload settings since it's a module-level singleton.
    from app import settings as settings_mod
    from app.auth import oauth as oauth_mod

    reload(settings_mod)
    # Re-import oauth so it sees the reloaded settings
    reload(oauth_mod)

    async with await _client() as ac:
        r = await ac.get("/auth/login")
    assert r.status_code == 302
    loc = r.headers["location"]
    assert loc.startswith("https://github.com/login/oauth/authorize?")
    qs = parse_qs(urlparse(loc).query)
    assert "state" in qs
    # State cookie set
    assert "si_oauth_state" in r.headers.get("set-cookie", "")
