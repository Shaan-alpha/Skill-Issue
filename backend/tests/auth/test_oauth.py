import secrets
from urllib.parse import parse_qs, urlparse

import pytest

from app.auth.oauth import (
    InvalidOAuthState,
    build_authorize_url,
    generate_state_token,
    verify_state_token,
)


def test_authorize_url_requests_read_only_scope():
    """v0.9.5: scope must be `read:user` only — no write scope (`public_repo`),
    never `repo`/`admin:*`. The app only reads public data."""
    qs = parse_qs(urlparse(build_authorize_url("state123")).query)
    assert qs["scope"] == ["read:user"]
    assert "public_repo" not in qs["scope"][0]
    assert "repo" not in qs["scope"][0].split()
    assert qs["state"] == ["state123"]


def test_state_token_is_url_safe_high_entropy():
    s = generate_state_token()
    assert len(s) >= 32
    assert all(c.isalnum() or c in "-_" for c in s)


def test_verify_state_matches():
    s = generate_state_token()
    verify_state_token(cookie=s, query=s)  # does not raise


def test_verify_state_mismatch_raises():
    with pytest.raises(InvalidOAuthState):
        verify_state_token(cookie="abc", query="def")


def test_verify_state_missing_cookie_raises():
    with pytest.raises(InvalidOAuthState):
        verify_state_token(cookie=None, query="abc")


def test_verify_state_uses_constant_time_compare():
    a = secrets.token_urlsafe(32)
    b = "x" * len(a)
    with pytest.raises(InvalidOAuthState):
        verify_state_token(cookie=a, query=b)
