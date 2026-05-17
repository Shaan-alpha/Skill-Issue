from __future__ import annotations

import secrets
from typing import Any
from urllib.parse import urlencode

from httpx import AsyncClient

from app.settings import settings


class InvalidOAuthState(Exception):
    """Raised when the OAuth state cookie is missing or does not match the query param."""


def generate_state_token() -> str:
    """43-char URL-safe random token, ~256 bits of entropy."""
    return secrets.token_urlsafe(32)


def verify_state_token(*, cookie: str | None, query: str) -> None:
    """Raise InvalidOAuthState unless cookie == query in constant time."""
    if not cookie:
        raise InvalidOAuthState("missing state cookie")
    if not secrets.compare_digest(cookie, query):
        raise InvalidOAuthState("state cookie/query mismatch")


def build_authorize_url(state: str) -> str:
    """Construct the GitHub authorize URL we 302 to."""
    params = {
        "client_id": settings.github_oauth_client_id or "",
        "scope": "read:user public_repo",
        "state": state,
        "redirect_uri": settings.oauth_redirect_url or "",
    }
    return f"https://github.com/login/oauth/authorize?{urlencode(params)}"


async def exchange_code_for_token(code: str) -> str:
    """Exchange an OAuth code for an access token. Returns the raw token string."""
    async with AsyncClient(timeout=10.0) as client:
        r = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": settings.github_oauth_client_id,
                "client_secret": settings.github_oauth_client_secret,
                "code": code,
                "redirect_uri": settings.oauth_redirect_url,
            },
            headers={"Accept": "application/json"},
        )
    r.raise_for_status()
    payload: dict[str, Any] = r.json()
    token = payload.get("access_token")
    if not token:
        raise RuntimeError(f"GitHub token exchange returned no access_token: {payload}")
    return token


async def fetch_github_user(token: str) -> dict[str, Any]:
    """GET /user using the just-obtained access token."""
    async with AsyncClient(timeout=10.0) as client:
        r = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
        )
    r.raise_for_status()
    return r.json()
