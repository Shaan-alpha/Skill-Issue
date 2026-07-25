from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import _ResolvedSession, require_session, require_trusted_origin
from app.cache.keys import NAMESPACE_REPORT, report_key
from app.cache.rate_limit import try_increment_counter
from app.db.session import get_db
from app.dependencies import get_cache, get_report_for_user
from app.models import Report
from app.persistence.analyses import get_user_analysis_by_target, record_run
from app.ratelimit import hour_bucket, seconds_until_next_hour
from app.settings import settings

router = APIRouter(prefix="/me", tags=["me"])


@router.post("/refresh/{username}")
async def force_refresh(
    username: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    session: Annotated[_ResolvedSession, Depends(require_session)],
    _origin: Annotated[None, Depends(require_trusted_origin)],
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
            subject=f"user:{session.user.id}",
            limit=settings.force_refresh_per_user_per_hour,
            hour_bucket=hour_bucket(now),
        )
        if not result.allowed:
            retry_after = seconds_until_next_hour(now)
            return JSONResponse(
                {"detail": "rate_limited", "retry_after_seconds": retry_after},
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(retry_after)},
            )

    # Invalidate Layer A so the live pipeline runs cold for this target.
    if cache is not None:
        await cache.delete(NAMESPACE_REPORT, report_key(username))

    started_at = datetime.now(UTC)
    report: Report = await get_report_for_user(username, session=session)
    completed_at = datetime.now(UTC)

    scores_hash = hashlib.sha256(
        json.dumps(report.model_dump(mode="json"), sort_keys=True).encode("utf-8")
    ).hexdigest()
    await record_run(
        db,
        analysis_id=analysis.id,
        report_json=report.model_dump(mode="json"),
        total_score=report.total,
        tier_name=report.tier.name,
        scores_hash=scores_hash,
        started_at=started_at,
        completed_at=completed_at,
        latency_ms=int((completed_at - started_at).total_seconds() * 1000),
    )
    await db.commit()
    return report
