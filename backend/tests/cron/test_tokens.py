from __future__ import annotations

import base64
import secrets
from datetime import UTC, datetime, timedelta

from app.auth.crypto import encrypt_access_token, load_enc_key
from app.cron.tokens import TokenSource, resolve_token_for_analysis
from app.db.models import Analysis, Session, User


def _enc_key(monkeypatch) -> bytes:
    monkeypatch.setenv(
        "SESSION_TOKEN_ENC_KEY", base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    )
    from app import settings as settings_module

    settings_module.settings = settings_module.Settings()
    return load_enc_key()


def _app_fallback_token(monkeypatch, value: str = "app-fallback-token") -> str:
    """Force the app-fallback token that `resolve_token_for_analysis` will read.

    `app/cron/tokens.py` does `from app.settings import settings`, which binds
    the settings *object* at import time. Rebuilding `app.settings.settings`
    (as `_enc_key` does) rebinds only that module's name — the cron module keeps
    the original object, still carrying whatever `GITHUB_TOKEN` was in the
    developer's `.env`. Setting the env var alone therefore did nothing, and the
    assertion compared against a real `ghp_` token from disk. Patch the
    attribute on the object the module actually holds.
    """
    from app.cron import tokens as tokens_module

    monkeypatch.setattr(tokens_module.settings, "github_token", value)
    return value


async def _make_user_and_analysis(db, login: str = "alice") -> tuple[User, Analysis]:
    u = User(github_id=hash(login) & 0xFFFF, github_login=login, name=login, avatar_url=None)
    db.add(u)
    await db.flush()
    a = Analysis(user_id=u.id, target_login="octocat")
    db.add(a)
    await db.flush()
    return u, a


async def test_resolves_active_session_token(db, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "app-fallback-token")
    _app_fallback_token(monkeypatch)
    key = _enc_key(monkeypatch)
    user, analysis = await _make_user_and_analysis(db)

    ct, nonce = encrypt_access_token(key, "user-token-123")
    db.add(
        Session(
            id="sid-active",
            user_id=user.id,
            access_token_ct=ct,
            access_token_nonce=nonce,
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )
    )
    await db.commit()

    token, source = await resolve_token_for_analysis(db, analysis)
    assert token == "user-token-123"
    assert source == TokenSource.USER_SESSION


async def test_falls_back_when_session_expired(db, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "app-fallback-token")
    _app_fallback_token(monkeypatch)
    key = _enc_key(monkeypatch)
    user, analysis = await _make_user_and_analysis(db)

    ct, nonce = encrypt_access_token(key, "stale-token")
    db.add(
        Session(
            id="sid-expired",
            user_id=user.id,
            access_token_ct=ct,
            access_token_nonce=nonce,
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
    )
    await db.commit()

    token, source = await resolve_token_for_analysis(db, analysis)
    assert token == "app-fallback-token"
    assert source == TokenSource.APP_FALLBACK


async def test_falls_back_when_no_session_at_all(db, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "app-fallback-token")
    _app_fallback_token(monkeypatch)
    _enc_key(monkeypatch)
    _, analysis = await _make_user_and_analysis(db)
    await db.commit()

    token, source = await resolve_token_for_analysis(db, analysis)
    assert token == "app-fallback-token"
    assert source == TokenSource.APP_FALLBACK


async def test_picks_most_recently_used_session_when_multiple(db, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "app-fallback-token")
    _app_fallback_token(monkeypatch)
    key = _enc_key(monkeypatch)
    user, analysis = await _make_user_and_analysis(db)
    now = datetime.now(UTC)

    ct1, nonce1 = encrypt_access_token(key, "older-token")
    db.add(
        Session(
            id="sid-older",
            user_id=user.id,
            access_token_ct=ct1,
            access_token_nonce=nonce1,
            expires_at=now + timedelta(days=30),
            last_used_at=now - timedelta(hours=3),
        )
    )
    ct2, nonce2 = encrypt_access_token(key, "newer-token")
    db.add(
        Session(
            id="sid-newer",
            user_id=user.id,
            access_token_ct=ct2,
            access_token_nonce=nonce2,
            expires_at=now + timedelta(days=30),
            last_used_at=now - timedelta(minutes=5),
        )
    )
    await db.commit()

    token, source = await resolve_token_for_analysis(db, analysis)
    assert token == "newer-token"
    assert source == TokenSource.USER_SESSION
