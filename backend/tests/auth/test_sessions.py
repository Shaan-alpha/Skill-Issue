import base64
import secrets
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.sessions import (
    create_session,
    delete_session,
    get_session_with_token,
    touch_session,
)
from app.db.models import Session, User


@pytest.fixture(autouse=True)
def _enc_key(monkeypatch):
    monkeypatch.setenv(
        "SESSION_TOKEN_ENC_KEY",
        base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
    )


async def _user(db: AsyncSession) -> User:
    u = User(github_id=42, github_login="alice")
    db.add(u)
    await db.flush()
    return u


async def test_create_session_persists_encrypted_token(db: AsyncSession):
    u = await _user(db)
    sid = await create_session(db, user_id=u.id, github_access_token="ghp_x", ttl_days=30)
    row = await db.scalar(select(Session).where(Session.id == sid))
    assert row is not None
    assert row.access_token_ct != b"ghp_x"  # encrypted
    assert len(row.access_token_nonce) == 12
    assert row.expires_at > datetime.now(UTC) + timedelta(days=29)


async def test_get_session_returns_user_and_decrypted_token(db: AsyncSession):
    u = await _user(db)
    sid = await create_session(db, user_id=u.id, github_access_token="ghp_x", ttl_days=30)
    resolved = await get_session_with_token(db, sid)
    assert resolved is not None
    user, token = resolved
    assert user.id == u.id
    assert token == "ghp_x"


async def test_get_expired_session_returns_none(db: AsyncSession):
    u = await _user(db)
    sid = await create_session(db, user_id=u.id, github_access_token="x", ttl_days=30)
    # Manually expire it
    row = await db.scalar(select(Session).where(Session.id == sid))
    row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db.flush()
    assert await get_session_with_token(db, sid) is None


async def test_get_unknown_session_returns_none(db: AsyncSession):
    assert await get_session_with_token(db, "no-such-session") is None


async def test_touch_session_updates_last_used_at(db: AsyncSession):
    u = await _user(db)
    sid = await create_session(db, user_id=u.id, github_access_token="x", ttl_days=30)
    row = await db.scalar(select(Session).where(Session.id == sid))
    original = row.last_used_at
    await touch_session(db, sid)
    await db.refresh(row)
    assert row.last_used_at >= original


async def test_delete_session_removes_row(db: AsyncSession):
    u = await _user(db)
    sid = await create_session(db, user_id=u.id, github_access_token="x", ttl_days=30)
    await delete_session(db, sid)
    assert await db.scalar(select(Session).where(Session.id == sid)) is None


async def test_session_id_stored_hashed(db: AsyncSession):
    import hashlib

    u = await _user(db)
    sid = await create_session(db, user_id=u.id, github_access_token="ghp_x", ttl_days=30)
    # v1.0.8 SI-21: the raw cookie value is NOT stored — the PK is its hash.
    assert await db.scalar(select(Session).where(Session.id == sid)) is None
    expected = hashlib.sha256(sid.encode("utf-8")).hexdigest()
    assert await db.scalar(select(Session).where(Session.id == expected)) is not None
    # Resolving by the raw cookie value still works.
    resolved = await get_session_with_token(db, sid)
    assert resolved is not None
    assert resolved[0].id == u.id


async def test_get_session_with_corrupt_ciphertext_returns_none(db: AsyncSession):
    u = await _user(db)
    sid = await create_session(db, user_id=u.id, github_access_token="ghp_x", ttl_days=30)
    row = await db.scalar(select(Session).where(Session.id == sid))
    # Flip the last ciphertext byte so the AES-GCM tag check fails on decrypt.
    row.access_token_ct = row.access_token_ct[:-1] + bytes([row.access_token_ct[-1] ^ 0xFF])
    await db.flush()
    # Must degrade to "invalid session" (None), not raise InvalidEncKey.
    assert await get_session_with_token(db, sid) is None
