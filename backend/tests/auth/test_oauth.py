import secrets

import pytest

from app.auth.oauth import (
    InvalidOAuthState,
    generate_state_token,
    verify_state_token,
)


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
