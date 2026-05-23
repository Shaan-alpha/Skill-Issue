from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import _ResolvedSession, require_session
from app.db.session import get_db
from app.persistence.analyses import get_user_analysis_by_target

router = APIRouter(prefix="/me", tags=["me"])


@router.post("/refresh/{username}")
async def force_refresh(
    username: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    session: Annotated[_ResolvedSession, Depends(require_session)],
) -> dict[str, object]:
    analysis = await get_user_analysis_by_target(db, user_id=session.user.id, target_login=username)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no_saved_analysis")

    # Task 5 wires the rate-limit gate here.
    # Task 6 wires the cache-invalidate + re-ingest + record-run here.
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="not_yet")
