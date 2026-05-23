from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import _ResolvedSession, require_session
from app.cache.rate_limit import try_increment_counter
from app.db.session import get_db
from app.dependencies import get_cache
from app.persistence.analyses import get_user_analysis_by_target
from app.settings import settings

router = APIRouter(prefix="/me", tags=["me"])


def _hour_bucket(now: datetime) -> str:
    return now.strftime("%Y-%m-%d-%H")


def _seconds_until_next_hour(now: datetime) -> int:
    next_hour = now.replace(minute=0, second=0, microsecond=0).timestamp() + 3600
    return max(1, int(next_hour - now.timestamp()))


@router.post("/refresh/{username}")
async def force_refresh(
    username: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    session: Annotated[_ResolvedSession, Depends(require_session)],
) -> object:
    analysis = await get_user_analysis_by_target(db, user_id=session.user.id, target_login=username)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no_saved_analysis")

    cache = get_cache()
    if cache is not None:
        now = datetime.now(UTC)
        result = await try_increment_counter(
            cache,
            name="force_refresh",
            user_id=session.user.id,
            limit=settings.force_refresh_per_user_per_hour,
            hour_bucket=_hour_bucket(now),
        )
        if not result.allowed:
            retry_after = _seconds_until_next_hour(now)
            return JSONResponse(
                {"detail": "rate_limited", "retry_after_seconds": retry_after},
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(retry_after)},
            )

    # Task 6 wires the cache-invalidate + re-ingest + record-run here.
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="not_yet")
