from __future__ import annotations

import re
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import settings as settings_module
from app.auth.sessions import get_session_with_token, touch_session
from app.db.models import User
from app.db.session import get_db


def _origin_allowed(origin: str) -> bool:
    s = settings_module.settings
    allowed = {o.strip() for o in s.cors_allow_origins.split(",") if o.strip()}
    if origin in allowed:
        return True
    rx = s.cors_allow_origin_regex
    return bool(rx and re.fullmatch(rx, origin))


def require_trusted_origin(request: Request) -> None:
    """v1.0.8 SI-16: reject a state-changing mutation whose ``Origin`` is not one
    of ours. SameSite=Lax treats a sibling subdomain as same-site, so a
    credentialed DELETE/POST from ``evil.skillissue.tech`` (XSS / subdomain
    takeover) would otherwise carry the cookie. Defense-in-depth on top of the
    ownership check + SameSite — an absent Origin (server-to-server / curl) is
    allowed, since browsers always send it on cross-origin fetch/XHR."""
    origin = request.headers.get("origin")
    if origin is None or _origin_allowed(origin):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "bad_origin"})


def is_cross_site_write(request: Request) -> bool:
    """True when the request looks like a cross-site browser navigation — the
    CSRF signal for our GET endpoints that persist state.

    Browsers stamp ``Sec-Fetch-Site: cross-site`` on requests initiated from a
    different site (e.g. a top-level navigation from an attacker page, which
    would carry the SameSite=Lax session cookie). Legitimate first-party
    callers send ``same-origin``/``same-site``/``none``, and the Next.js RSC
    server-to-server proxy omits the header entirely. We treat ONLY the explicit
    ``cross-site`` value as hostile, so anything that legitimately lacks the
    header (old browsers, server fetches) is never penalized — the write simply
    proceeds as before.
    """
    return request.headers.get("sec-fetch-site") == "cross-site"


class _ResolvedSession:
    __slots__ = ("access_token", "session_id", "user")

    def __init__(self, user: User, access_token: str, session_id: str) -> None:
        self.user = user
        self.access_token = access_token
        self.session_id = session_id


async def optional_session(
    db: Annotated[AsyncSession, Depends(get_db)],
    si_session: Annotated[str | None, Cookie()] = None,
) -> _ResolvedSession | None:
    """Resolve the session cookie if present; never raises on absence."""
    if si_session is None:
        return None
    resolved = await get_session_with_token(db, si_session)
    if resolved is None:
        return None
    user, token = resolved
    await touch_session(db, si_session)
    return _ResolvedSession(user=user, access_token=token, session_id=si_session)


async def current_user_or_none(
    session: Annotated[_ResolvedSession | None, Depends(optional_session)],
) -> User | None:
    return session.user if session else None


async def require_user(
    session: Annotated[_ResolvedSession | None, Depends(optional_session)],
) -> User:
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "auth_required"},
        )
    return session.user


async def require_session(
    session: Annotated[_ResolvedSession | None, Depends(optional_session)],
) -> _ResolvedSession:
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "auth_required"},
        )
    return session
