from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from app.db.models import User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def upsert_user_from_github_payload(
    db: AsyncSession, payload: dict[str, Any]
) -> User:
    """Insert or update a User row keyed by github_id. Returns the persisted row."""
    github_id = int(payload["id"])
    login = str(payload["login"])
    name = payload.get("name")
    avatar_url = payload.get("avatar_url")

    user = await db.scalar(select(User).where(User.github_id == github_id))
    if user is None:
        user = User(
            github_id=github_id,
            github_login=login,
            name=name,
            avatar_url=avatar_url,
        )
        db.add(user)
        await db.flush()
        return user

    user.github_login = login
    user.name = name
    user.avatar_url = avatar_url
    user.updated_at = datetime.now(UTC)
    await db.flush()
    return user
