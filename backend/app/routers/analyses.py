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
    """Construct the public-facing share URL on the frontend origin.

    Uses CORS_ALLOW_ORIGINS as the source of truth — that env var holds the
    frontend origin(s) by definition. The previous implementation derived
    the base from OAUTH_REDIRECT_URL, which on multi-service Vercel deploys
    includes the `/_/backend` service prefix and ended up pointing the share
    URL at the backend's raw JSON endpoint instead of the frontend page.
    """
    origins = [o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()]
    base = origins[0] if origins else ""
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
