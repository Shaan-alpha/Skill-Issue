from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from httpx import HTTPStatusError
from sqlalchemy.ext.asyncio import AsyncSession

import app.auth.oauth as _oauth_mod
from app.auth.oauth import build_authorize_url, generate_state_token
from app.auth.sessions import create_session
from app.db.session import get_db
from app.persistence.users import upsert_user_from_github_payload
from app.settings import Settings, settings

router = APIRouter(prefix="/auth", tags=["auth"])

_OAUTH_STATE_COOKIE = "si_oauth_state"
_OAUTH_STATE_TTL_SECONDS = 600  # 10 min


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
        path="/auth",
    )
    return redirect


@router.get("/callback")
async def callback(
    db: Annotated[AsyncSession, Depends(get_db)],
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    si_oauth_state: Annotated[str | None, Cookie()] = None,
) -> RedirectResponse:
    # User cancelled the OAuth flow.
    if error == "access_denied":
        resp = RedirectResponse("/?auth=cancelled", status_code=302)
        resp.delete_cookie(_OAUTH_STATE_COOKIE, path="/auth")
        return resp

    if not code or not state:
        raise HTTPException(status_code=400, detail={"error": "missing_code_or_state"})

    # Use module-level lookup so that test reloads of app.auth.oauth don't
    # create a class-identity mismatch between the imported symbol and the
    # live module's class.
    try:
        _oauth_mod.verify_state_token(cookie=si_oauth_state, query=state)
    except _oauth_mod.InvalidOAuthState as exc:
        raise HTTPException(status_code=400, detail={"error": "invalid_state"}) from exc

    # Construct a fresh Settings instance so monkeypatched env vars are picked
    # up in tests (the module-level singleton is frozen at import time).
    cfg = Settings()

    try:
        access_token = await _oauth_mod.exchange_code_for_token(code)
        gh_user = await _oauth_mod.fetch_github_user(access_token)
    except HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail={"error": "github_failure"}) from exc

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
    resp.delete_cookie(_OAUTH_STATE_COOKIE, path="/auth")
    return resp
