from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Cookie, Query, status
from fastapi.responses import RedirectResponse, Response
from httpx import HTTPError

import app.auth.oauth as _oauth_mod
from app.auth.oauth import build_authorize_url, generate_state_token
from app.auth.sessions import create_session, delete_session
from app.db.session import DbSession
from app.persistence.users import upsert_user_from_github_payload
from app.settings import Settings, settings

router = APIRouter(prefix="/auth", tags=["auth"])

_OAUTH_STATE_COOKIE = "si_oauth_state"
_OAUTH_STATE_TTL_SECONDS = 600  # 10 min

logger = logging.getLogger(__name__)


def _back_to_site(outcome: str) -> RedirectResponse:
    resp = RedirectResponse(f"/?auth={outcome}", status_code=302)
    resp.delete_cookie(_OAUTH_STATE_COOKIE, path="/")
    return resp


@router.get("/login")
async def login() -> RedirectResponse:
    state = generate_state_token()
    redirect = RedirectResponse(build_authorize_url(state), status_code=302)
    redirect.set_cookie(
        key=_OAUTH_STATE_COOKIE,
        value=state,
        max_age=_OAUTH_STATE_TTL_SECONDS,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        domain=settings.cookie_domain,
        # Cookie must be sent back on the callback. On Vercel multi-service the
        # callback URL is `/_/backend/auth/callback`, which would not match a
        # `/auth` cookie path. `/` is the safe default — the cookie is 10-minute
        # TTL anyway, so the narrower scope buys very little.
        path="/",
    )
    return redirect


@router.get("/callback")
async def callback(
    db: DbSession,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    si_oauth_state: Annotated[str | None, Cookie()] = None,
) -> RedirectResponse:
    # User cancelled the OAuth flow.
    if error == "access_denied":
        return _back_to_site("cancelled")

    # Every other failure lands back on the site too, never on a raw error
    # page: GitHub's other `error=` values, a missing code, a state that
    # doesn't match (CSRF, or a callback older than the 10-minute cookie), a
    # code GitHub rejects as expired or reused, or GitHub being down.
    if error or not code or not state:
        logger.warning("auth.callback_failed reason=%s", error or "missing_code_or_state")
        return _back_to_site("failed")

    # Use module-level lookup so that test reloads of app.auth.oauth don't
    # create a class-identity mismatch between the imported symbol and the
    # live module's class.
    try:
        _oauth_mod.verify_state_token(cookie=si_oauth_state, query=state)
    except _oauth_mod.InvalidOAuthState:
        logger.warning("auth.callback_failed reason=invalid_state")
        return _back_to_site("failed")

    # Construct a fresh Settings instance so monkeypatched env vars are picked
    # up in tests (the module-level singleton is frozen at import time).
    cfg = Settings()

    try:
        access_token = await _oauth_mod.exchange_code_for_token(code)
        gh_user = await _oauth_mod.fetch_github_user(access_token)
    except (HTTPError, RuntimeError) as exc:
        # RuntimeError: GitHub answered 200 without a token (bad_verification_code).
        logger.warning("auth.callback_failed reason=github error=%s", type(exc).__name__)
        return _back_to_site("failed")

    user = await upsert_user_from_github_payload(db, gh_user)
    sid = await create_session(
        db,
        user_id=user.id,
        github_access_token=access_token,
        ttl_days=cfg.session_ttl_days,
    )

    resp = RedirectResponse("/", status_code=302)
    resp.set_cookie(
        key=cfg.session_cookie_name,
        value=sid,
        max_age=cfg.session_ttl_days * 86400,
        httponly=True,
        secure=cfg.cookie_secure,
        samesite="lax",
        domain=cfg.cookie_domain,
        path="/",
    )
    resp.delete_cookie(_OAUTH_STATE_COOKIE, path="/")
    return resp


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    db: DbSession,
    si_session: Annotated[str | None, Cookie()] = None,
) -> Response:
    if si_session:
        await delete_session(db, si_session)
    resp = Response(status_code=204)
    resp.delete_cookie(
        settings.session_cookie_name,
        domain=settings.cookie_domain,
        path="/",
    )
    return resp
