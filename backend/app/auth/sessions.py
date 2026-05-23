from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import delete, select, update

from app.auth.crypto import decrypt_access_token, encrypt_access_token, load_enc_key
from app.db.models import Session, User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def _new_session_id() -> str:
    """43-char URL-safe random token (32 raw bytes b64-encoded)."""
    return secrets.token_urlsafe(32)


async def create_session(
    db: AsyncSession,
    *,
    user_id: int,
    github_access_token: str,
    ttl_days: int = 30,
) -> str:
    """Insert a session row, return the opaque session id (cookie value)."""
    key = load_enc_key()
    ct, nonce = encrypt_access_token(key, github_access_token)
    sid = _new_session_id()
    expires_at = datetime.now(UTC) + timedelta(days=ttl_days)
    db.add(
        Session(
            id=sid,
            user_id=user_id,
            access_token_ct=ct,
            access_token_nonce=nonce,
            expires_at=expires_at,
        )
    )
    await db.flush()
    return sid


async def get_session_with_token(db: AsyncSession, session_id: str) -> tuple[User, str] | None:
    """Resolve a session_id to (User, decrypted_token) or None when expired/missing."""
    row = await db.scalar(select(Session).where(Session.id == session_id))
    if row is None:
        return None
    if row.expires_at <= datetime.now(UTC):
        return None
    user = await db.get(User, row.user_id)
    if user is None:
        return None
    key = load_enc_key()
    token = decrypt_access_token(key, row.access_token_ct, row.access_token_nonce)
    return user, token


async def touch_session(db: AsyncSession, session_id: str) -> None:
    await db.execute(
        update(Session).where(Session.id == session_id).values(last_used_at=datetime.now(UTC))
    )


async def delete_session(db: AsyncSession, session_id: str) -> None:
    await db.execute(delete(Session).where(Session.id == session_id))
