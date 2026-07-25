import base64
import secrets
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import current_user_or_none, require_user
from app.auth.sessions import create_session
from app.db.models import User


@pytest.fixture
def mini_app(db):
    from app.db.session import get_db

    app = FastAPI()

    @app.get("/whoami")
    async def whoami(u: Annotated[User | None, Depends(current_user_or_none)]):
        return {"login": u.github_login if u else None}

    @app.get("/private")
    async def private(u: Annotated[User, Depends(require_user)]):
        return {"login": u.github_login}

    async def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    return app


async def test_whoami_returns_null_when_no_cookie(mini_app):
    async with AsyncClient(transport=ASGITransport(app=mini_app), base_url="http://t") as ac:
        r = await ac.get("/whoami")
    assert r.json() == {"login": None}


async def test_whoami_returns_user_with_valid_cookie(mini_app, db, monkeypatch):
    monkeypatch.setenv(
        "SESSION_TOKEN_ENC_KEY",
        base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
    )
    u = User(github_id=99, github_login="z")
    db.add(u)
    await db.flush()
    sid = await create_session(db, user_id=u.id, github_access_token="t", ttl_days=30)
    await db.commit()
    async with AsyncClient(transport=ASGITransport(app=mini_app), base_url="http://t") as ac:
        ac.cookies.set("si_session", sid)
        r = await ac.get("/whoami")
    assert r.json() == {"login": "z"}


async def test_private_returns_401_without_session(mini_app):
    async with AsyncClient(transport=ASGITransport(app=mini_app), base_url="http://t") as ac:
        r = await ac.get("/private")
    assert r.status_code == 401


def _req_with_headers(headers: dict[str, str]):
    from starlette.requests import Request

    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
    }
    return Request(scope)


def test_is_cross_site_write_flags_only_cross_site():
    from app.auth.dependencies import is_cross_site_write

    # The CSRF signal: a cross-site browser navigation.
    assert is_cross_site_write(_req_with_headers({"sec-fetch-site": "cross-site"})) is True
    # Legit first-party callers.
    for site in ("same-origin", "same-site", "none"):
        assert is_cross_site_write(_req_with_headers({"sec-fetch-site": site})) is False
    # Absent header (Next.js RSC server fetch, old browsers) — never penalized.
    assert is_cross_site_write(_req_with_headers({})) is False


def _req_with_origin(origin: str | None = None):
    from starlette.requests import Request

    headers = [(b"origin", origin.encode())] if origin else []
    return Request({"type": "http", "headers": headers})


def test_require_trusted_origin(monkeypatch):
    import pytest
    from fastapi import HTTPException

    from app import settings as settings_module
    from app.auth.dependencies import require_trusted_origin

    monkeypatch.setattr(
        settings_module.settings,
        "cors_allow_origins",
        "https://skillissue.tech,http://localhost:3000",
    )
    monkeypatch.setattr(
        settings_module.settings,
        "cors_allow_origin_regex",
        r"https://preview-[a-z0-9]+\.vercel\.app",
    )
    # Absent Origin (server-to-server / curl) -> allowed.
    require_trusted_origin(_req_with_origin(None))
    # Configured origin -> allowed.
    require_trusted_origin(_req_with_origin("https://skillissue.tech"))
    # Regex-matched preview deploy -> allowed.
    require_trusted_origin(_req_with_origin("https://preview-abc123.vercel.app"))
    # Foreign origin -> 403.
    with pytest.raises(HTTPException) as exc:
        require_trusted_origin(_req_with_origin("https://evil.example.com"))
    assert exc.value.status_code == 403
    assert exc.value.detail["error"] == "bad_origin"
