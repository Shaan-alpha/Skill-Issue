from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import desc, select

from app.auth.crypto import decrypt_access_token, load_enc_key
from app.db.models import Session
from app.settings import settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db.models import Analysis


class TokenSource(StrEnum):
    USER_SESSION = "user_session"
    APP_FALLBACK = "app_fallback"


async def resolve_token_for_analysis(
    db: AsyncSession,
    analysis: Analysis,
) -> tuple[str, TokenSource]:
    """Pick a GitHub token for refreshing this analysis.

    Tries the owner's most-recently-used unexpired session. If decryption
    works, returns that token + USER_SESSION. Otherwise falls back to the
    app's GITHUB_TOKEN + APP_FALLBACK. Returning the app token when no user
    token is available is intentional — it keeps cron alive even for users
    who signed out or rotated their auth.
    """
    fallback = settings.github_token or ""
    stmt = (
        select(Session)
        .where(
            Session.user_id == analysis.user_id,
            Session.expires_at > datetime.now(UTC),
        )
        .order_by(desc(Session.last_used_at))
        .limit(1)
    )
    sess = await db.scalar(stmt)
    if sess is None:
        return fallback, TokenSource.APP_FALLBACK
    try:
        key = load_enc_key()
        token = decrypt_access_token(key, sess.access_token_ct, sess.access_token_nonce)
    except Exception:
        return fallback, TokenSource.APP_FALLBACK
    return token, TokenSource.USER_SESSION
