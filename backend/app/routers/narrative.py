from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

from app.auth.dependencies import optional_session
from app.db.session import get_db
from app.dependencies import get_narrative_service, get_report_for_user
from app.models import Report
from app.narrative.service import NarrativeService
from app.persistence.analyses import record_run, upsert_analysis
from app.persistence.narratives import save_narrative
from app.settings import settings

router = APIRouter(tags=["narrative"])


def _scores_hash(report: Report) -> str:
    return hashlib.sha256(
        json.dumps(report.model_dump(mode="json"), sort_keys=True).encode("utf-8")
    ).hexdigest()


@router.get("/narrative/{username}")
async def get_narrative(
    username: str,
    report: Annotated[Report, Depends(get_report_for_user)],
    service: Annotated[NarrativeService, Depends(get_narrative_service)],
    db: Annotated[AsyncSession, Depends(get_db)],
    session: Annotated[object | None, Depends(optional_session)],
    mode: str = Query("roast", description="Narrative mode: roast or mentor"),
) -> StreamingResponse:
    """Stream AI narrative critique or mentorship over Server-Sent Events
    (SSE)."""
    if mode not in ("roast", "mentor"):
        raise HTTPException(
            status_code=400,
            detail="Invalid narrative mode; must be 'roast' or 'mentor'",
        )

    typed_mode: Literal["roast", "mentor"] = (
        "roast" if mode == "roast" else "mentor"
    )

    async def event_generator() -> AsyncIterator[str]:
        acc: list[str] = []
        is_fallback = False
        started_at = datetime.now(UTC)
        async for chunk in service.stream_narrative(typed_mode, report):
            acc.append(chunk)
            payload = json.dumps({"chunk": chunk})
            yield f"data: {payload}\n\n"

        if session is not None:
            completed_at = datetime.now(UTC)
            analysis = await upsert_analysis(
                db, user_id=session.user.id, target_login=report.username
            )
            shash = _scores_hash(report)
            latest_run = None
            if analysis.latest_run_id is not None:
                from app.db.models import AnalysisRun

                cand = await db.get(AnalysisRun, analysis.latest_run_id)
                if cand is not None and cand.scores_hash == shash:
                    latest_run = cand
            if latest_run is None:
                latest_run = await record_run(
                    db,
                    analysis_id=analysis.id,
                    report_json=report.model_dump(mode="json"),
                    total_score=report.total,
                    tier_name=report.tier.name,
                    scores_hash=shash,
                    started_at=started_at,
                    completed_at=completed_at,
                    latency_ms=int(
                        (completed_at - started_at).total_seconds() * 1000
                    ),
                )
            await save_narrative(
                db,
                analysis_run_id=latest_run.id,
                mode=typed_mode,
                text="".join(acc),
                provider="openai",
                model_name=settings.narrative_model if not is_fallback else None,
                is_fallback=is_fallback,
            )
            await db.commit()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
