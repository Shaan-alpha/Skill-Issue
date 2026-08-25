from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Literal
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

from app.auth.dependencies import is_cross_site_write, optional_session
from app.db.models import AnalysisRun
from app.db.session import get_db
from app.dependencies import get_narrative_service, get_report_for_user
from app.models import Report
from app.narrative.service import NarrativeService, NarrativeStreamMeta
from app.persistence.analyses import record_run, upsert_analysis
from app.persistence.narratives import save_narrative
from app.ratelimit import narrative_rate_limiter, resolve_budget_subject
from app.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["narrative"])


def _scores_hash(report: Report) -> str:
    return hashlib.sha256(
        json.dumps(report.model_dump(mode="json"), sort_keys=True).encode("utf-8")
    ).hexdigest()


def _resolve_provider(base_url: str | None) -> str:
    """Map `NARRATIVE_BASE_URL` to a stable provider tag for analytics.

    Default (None / OpenAI's own host) → "openai". Recognised OpenAI-compatible
    hosts get their own tag. Everything else is "openai-compatible" so we never
    silently mislabel an unknown provider.
    """
    if not base_url:
        return "openai"
    try:
        host = (urlparse(base_url).hostname or "").lower()
    except ValueError:
        return "openai-compatible"
    if host.endswith("openai.com"):
        return "openai"
    if host.endswith("groq.com"):
        return "groq"
    if host.endswith("openrouter.ai"):
        return "openrouter"
    if host.endswith("cerebras.ai"):
        return "cerebras"
    return "openai-compatible"


@router.get("/narrative/{username}")
async def get_narrative(
    request: Request,
    username: str,
    _rl: Annotated[None, Depends(narrative_rate_limiter)],
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

    typed_mode: Literal["roast", "mentor"] = "roast" if mode == "roast" else "mentor"

    subject, subject_limit = resolve_budget_subject(request, session)

    async def event_generator() -> AsyncIterator[str]:
        acc: list[str] = []
        meta = NarrativeStreamMeta()
        started_at = datetime.now(UTC)
        try:
            async for chunk in service.stream_narrative(
                typed_mode, report, meta=meta, subject=subject, subject_limit=subject_limit
            ):
                acc.append(chunk)
                payload = json.dumps({"chunk": chunk})
                yield f"data: {payload}\n\n"
        except GeneratorExit:
            # Client aborted mid-stream (v1.0.5 SI-07): refund the LLM slot IFF
            # one was truly consumed — not on a cache hit, not on the budget
            # fallback (nothing consumed there).
            if not meta.cache_hit and meta.fallback_reason != "budget":
                logger.warning("narrative.budget.refunded_on_abort")
                await service.refund(subject=subject, consumed_day=meta.consumed_day)
            raise

        # Skip the persist branch for cross-site navigations (CSRF): this is a
        # GET with a SameSite=Lax cookie, so a top-level navigation from another
        # site could otherwise write into the victim's account. Streaming the
        # narrative back is unaffected.
        if session is not None and not is_cross_site_write(request):
            completed_at = datetime.now(UTC)
            analysis = await upsert_analysis(
                db, user_id=session.user.id, target_login=report.username
            )
            shash = _scores_hash(report)
            latest_run = None
            if analysis.latest_run_id is not None:
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
                    latency_ms=int((completed_at - started_at).total_seconds() * 1000),
                )
            await save_narrative(
                db,
                analysis_run_id=latest_run.id,
                mode=typed_mode,
                text="".join(acc),
                provider=_resolve_provider(settings.narrative_base_url),
                model_name=None if meta.is_fallback else settings.narrative_model,
                is_fallback=meta.is_fallback,
            )
            await db.commit()

        # v1.0.7 SI-33: explicit end-of-stream sentinel so the client can tell a
        # normal completion (this) from a dropped connection (EventSource error).
        # `truncated` rides along so the client can close off a narrative the
        # model stopped mid-sentence instead of rendering the ragged edge.
        yield f"data: {json.dumps({'done': True, 'truncated': meta.truncated})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
