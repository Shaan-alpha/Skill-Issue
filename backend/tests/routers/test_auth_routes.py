from importlib import reload
from urllib.parse import parse_qs, urlparse

import respx
from httpx import ASGITransport, AsyncClient
from httpx import Response as HTTPXResponse

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


async def _seed_db_override(db):
    """Wire app.db.session.get_db to yield the test `db` AsyncSession."""
    from app.db.session import get_db

    async def _override():
        yield db

    app.dependency_overrides[get_db] = _override


@respx.mock
async def test_callback_happy_path_creates_user_and_session(db, monkeypatch):
    monkeypatch.setenv("GITHUB_OAUTH_CLIENT_ID", "test-id")
    monkeypatch.setenv("GITHUB_OAUTH_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("OAUTH_REDIRECT_URL", "http://localhost:8000/auth/callback")
    import base64
    import secrets

    monkeypatch.setenv(
        "SESSION_TOKEN_ENC_KEY",
        base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
    )

    state = "test-state-token"
    code = "abc123"

    respx.post("https://github.com/login/oauth/access_token").mock(
        return_value=HTTPXResponse(
            200, json={"access_token": "ghp_test", "token_type": "bearer"}
        )
    )
    respx.get("https://api.github.com/user").mock(
        return_value=HTTPXResponse(
            200,
            json={
                "id": 583231,
                "login": "octocat",
                "name": "The Octocat",
                "avatar_url": "https://avatars.example/oc.png",
            },
        )
    )

    await _seed_db_override(db)

    async with await _client() as ac:
        # Omit domain: HTTPX won't send domain-specified cookies to single-label
        # hosts (RFC 6265). The cookie jar still forwards it as a session cookie.
        ac.cookies.set("si_oauth_state", state)
        r = await ac.get(f"/auth/callback?code={code}&state={state}")

    app.dependency_overrides.clear()

    assert r.status_code == 302
    assert r.headers["location"] == "/"
    cookies = r.headers.get_list("set-cookie")
    assert any("si_session=" in c for c in cookies)

    from sqlalchemy import select

    from app.db.models import Session, User

    user = await db.scalar(select(User).where(User.github_id == 583231))
    assert user is not None and user.github_login == "octocat"
    session = await db.scalar(select(Session).where(Session.user_id == user.id))
    assert session is not None


async def test_callback_state_mismatch_returns_400(db):
    await _seed_db_override(db)

    async with await _client() as ac:
        ac.cookies.set("si_oauth_state", "real")
        r = await ac.get("/auth/callback?code=x&state=fake")
    app.dependency_overrides.clear()
    assert r.status_code == 400
    assert r.json() == {"error": "invalid_state"}


async def test_callback_user_cancelled_redirects_to_root(db):
    await _seed_db_override(db)
    async with await _client() as ac:
        r = await ac.get("/auth/callback?error=access_denied&state=anything")
    app.dependency_overrides.clear()
    assert r.status_code == 302
    assert r.headers["location"] == "/?auth=cancelled"


async def test_logout_deletes_session_and_clears_cookie(db, monkeypatch):
    import base64
    import secrets

    from sqlalchemy import select

    from app.auth.sessions import create_session
    from app.db.models import Session, User

    monkeypatch.setenv(
        "SESSION_TOKEN_ENC_KEY",
        base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
    )

    u = User(github_id=1, github_login="x")
    db.add(u)
    await db.flush()
    sid = await create_session(db, user_id=u.id, github_access_token="t", ttl_days=30)
    await db.commit()

    await _seed_db_override(db)

    async with await _client() as ac:
        ac.cookies.set("si_session", sid)
        r = await ac.post("/auth/logout")
    app.dependency_overrides.clear()

    assert r.status_code == 204
    assert (await db.scalar(select(Session).where(Session.id == sid))) is None


async def test_logout_idempotent_without_cookie():
    async with await _client() as ac:
        r = await ac.post("/auth/logout")
    assert r.status_code == 204
