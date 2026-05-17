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
