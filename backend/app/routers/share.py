from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.db.models import AnalysisRun, User
from app.db.session import DbSession
from app.persistence.analyses import get_analysis_by_slug

router = APIRouter(prefix="/share", tags=["share"])


@router.get("/{slug}")
async def get_shared(
    slug: str,
    db: DbSession,
) -> dict[str, Any]:
    a = await get_analysis_by_slug(db, slug)
    if a is None or a.latest_run_id is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})

    run = await db.get(AnalysisRun, a.latest_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail={"error": "not_found"})

    owner = await db.get(User, a.user_id)
    return {
        "report": run.report_json,
        "owner": {
            "login": owner.github_login if owner else None,
            "avatar_url": owner.avatar_url if owner else None,
        },
        "shared_at": a.updated_at.isoformat(),
    }
