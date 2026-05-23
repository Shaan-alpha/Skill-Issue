from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_user
from app.db.models import Analysis, AnalysisRun, User
from app.db.session import get_db
from app.persistence.analyses import list_user_analyses

router = APIRouter(tags=["me"])


@router.get("/me")
async def me(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_user)],
) -> dict[str, Any]:
    count = await db.scalar(
        select(func.count()).select_from(Analysis).where(Analysis.user_id == user.id)
    )
    return {
        "user": {
            "id": user.id,
            "login": user.github_login,
            "name": user.name,
            "avatar_url": user.avatar_url,
        },
        "counts": {"analyses": int(count or 0)},
    }


@router.get("/me/analyses")
async def my_analyses(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_user)],
    sort: Literal["recent", "score_desc", "score_asc"] = Query("recent"),
    page: int = Query(1, ge=1),
) -> dict[str, Any]:
    rows, total = await list_user_analyses(db, user_id=user.id, sort=sort, page=page, page_size=20)
    serialised: list[dict[str, Any]] = []
    for a in rows:
        run: AnalysisRun | None = (
            await db.scalar(select(AnalysisRun).where(AnalysisRun.id == a.latest_run_id))
            if a.latest_run_id
            else None
        )
        serialised.append(
            {
                "id": a.id,
                "target_login": a.target_login,
                "is_public": a.is_public,
                "share_slug": a.share_slug,
                "latest_run": None
                if run is None
                else {
                    "total_score": run.total_score,
                    "tier_name": run.tier_name,
                    "completed_at": run.ingestion_completed_at.isoformat(),
                },
            }
        )
    return {"analyses": serialised, "page": page, "total": total}
