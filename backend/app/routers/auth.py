from __future__ import annotations

from fastapi import APIRouter, Response
from fastapi.responses import RedirectResponse

from app.auth.oauth import build_authorize_url, generate_state_token
from app.settings import settings

router = APIRouter(prefix="/auth", tags=["auth"])

_OAUTH_STATE_COOKIE = "si_oauth_state"
_OAUTH_STATE_TTL_SECONDS = 600  # 10 min


@router.get("/login")
async def login(response: Response) -> RedirectResponse:
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
