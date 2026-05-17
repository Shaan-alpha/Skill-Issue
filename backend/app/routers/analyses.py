from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_user
from app.db.models import User
from app.db.session import get_db
from app.persistence.analyses import (
    AnalysisNotFound,
    revoke_share_slug,
    set_share_slug,
)
from app.settings import settings

router = APIRouter(prefix="/analyses", tags=["analyses"])


def _public_share_url(slug: str) -> str:
    base = (settings.oauth_redirect_url or "").rsplit("/auth/callback", 1)[0]
    return f"{base}/share/{slug}"


@router.post("/{analysis_id}/share")
async def share_analysis(
    analysis_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_user)],
) -> dict[str, Any]:
    try:
        slug = await set_share_slug(db, analysis_id=analysis_id, owner_id=user.id)
    except AnalysisNotFound as exc:
        raise HTTPException(status_code=403, detail={"error": "not_owner_or_missing"}) from exc
    return {"share_slug": slug, "share_url": _public_share_url(slug)}


@router.delete("/{analysis_id}/share", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_share(
    analysis_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_user)],
) -> Response:
    try:
        await revoke_share_slug(db, analysis_id=analysis_id, owner_id=user.id)
    except AnalysisNotFound as exc:
        raise HTTPException(status_code=403, detail={"error": "not_owner_or_missing"}) from exc
    return Response(status_code=204)
