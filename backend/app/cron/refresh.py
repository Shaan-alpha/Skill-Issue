from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

import httpx

from app.cron.tokens import TokenSource, resolve_token_for_analysis
from app.persistence.refresh import iter_stale_analyses

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db.models import Analysis
    from app.models import Report

logger = logging.getLogger(__name__)

Status = Literal[
    "succeeded",
    "not_found",
    "org_detected",
    "rate_limited",
    "unexpected_error",
]


@dataclass
class RefreshOutcome:
    analysis_id: int
    target_login: str
    owner_user_id: int
    token_source: TokenSource
    status: Status
    duration_ms: int
    error: str | None = None


@dataclass
class RefreshChunkSummary:
    processed: int = 0
    succeeded: int = 0
    skipped: int = 0
    rate_limited: int = 0
    deadline_reached: bool = False
    outcomes: list[RefreshOutcome] = field(default_factory=list)


# ---- Indirection layer so tests can monkey-patch the underlying primitives.


async def _fetch_stale_analyses(db: AsyncSession, *, limit: int) -> list[Analysis]:
    return await iter_stale_analyses(db, limit=limit)


async def _resolve_token(db: AsyncSession, analysis: Analysis) -> tuple[str, TokenSource]:
    return await resolve_token_for_analysis(db, analysis)


async def _fetch_report(username: str, *, token: str) -> Report:
    """Run the existing ingestion+scoring pipeline write-through to Layer A."""
    import json

    from app.cache.keys import NAMESPACE_REPORT, report_key
    from app.dependencies import _live_ingest, get_cache
    from app.settings import settings

    cache = get_cache()
    cache_key = report_key(username)

    class _Sess:
        access_token = token

    report = await _live_ingest(username, _Sess(), cache=cache)  # type: ignore[arg-type]

    if cache is not None:
        try:
            await cache.set_json(
                NAMESPACE_REPORT,
                cache_key,
                json.loads(report.model_dump_json()),
                ttl_seconds=settings.cache_report_ttl_seconds,
            )
        except Exception:
            logger.warning("cron: cache set failed for %s", cache_key, exc_info=True)
    return report


async def _record_run(db: AsyncSession, analysis: Analysis, report: Report, *, duration_ms: int):
    """Write a fresh AnalysisRun + update analyses.latest_run_id."""
    import hashlib
    import json
    from datetime import UTC, datetime, timedelta

    from app.persistence.analyses import record_run

    completed_at = datetime.now(UTC)
    started_at = completed_at - timedelta(milliseconds=duration_ms)
    scores_hash = hashlib.sha256(
        json.dumps(report.model_dump(mode="json"), sort_keys=True).encode("utf-8")
    ).hexdigest()
    return await record_run(
        db,
        analysis_id=analysis.id,
        report_json=report.model_dump(mode="json"),
        total_score=report.total,
        tier_name=report.tier.name,
        scores_hash=scores_hash,
        started_at=started_at,
        completed_at=completed_at,
        latency_ms=duration_ms,
    )


# ---- Public API.


def _classify(exc: BaseException) -> Status:
    if isinstance(exc, httpx.HTTPStatusError):
        if exc.response.status_code == 404:
            return "not_found"
        if exc.response.status_code == 422:
            return "org_detected"
        if (
            exc.response.status_code == 403
            and exc.response.headers.get("X-RateLimit-Remaining") == "0"
        ):
            return "rate_limited"
    return "unexpected_error"


async def run_refresh_chunk(
    db: AsyncSession,
    *,
    limit: int = 25,
    deadline_seconds: float = 240,
    now: Callable[[], float] | None = None,
) -> RefreshChunkSummary:
    """Process up to `limit` stale analyses; commit DB session at the end.

    `now` is injectable for tests — defaults to time.monotonic.
    """
    clock = now or time.monotonic
    started = clock()
    summary = RefreshChunkSummary()

    rows = await _fetch_stale_analyses(db, limit=limit)
    for analysis in rows:
        # Check budget BEFORE attempting the row.
        if clock() - started >= deadline_seconds:
            summary.deadline_reached = True
            break

        summary.processed += 1
        token, source = await _resolve_token(db, analysis)
        iter_start = clock()
        # Isolate EVERY per-row failure; rate-limit is the only one that breaks the chunk.
        try:
            report = await _fetch_report(analysis.target_login, token=token)
        except BaseException as exc:
            outcome_status = _classify(exc)
            duration_ms = int((clock() - iter_start) * 1000)
            summary.outcomes.append(
                RefreshOutcome(
                    analysis_id=analysis.id,
                    target_login=analysis.target_login,
                    owner_user_id=analysis.user_id,
                    token_source=source,
                    status=outcome_status,
                    duration_ms=duration_ms,
                    error=str(exc)[:200],
                )
            )
            if outcome_status == "rate_limited":
                summary.rate_limited += 1
                logger.error("cron rate_limit_cliff after %d analyses", summary.succeeded)
                break
            summary.skipped += 1
            logger.warning(
                "cron refresh skipped target=%s analysis_id=%d status=%s",
                analysis.target_login,
                analysis.id,
                outcome_status,
            )
            continue

        duration_ms = int((clock() - iter_start) * 1000)
        try:
            await _record_run(db, analysis, report, duration_ms=duration_ms)
        except Exception:
            logger.exception(
                "cron record_run failed for analysis_id=%d — committing what's done",
                analysis.id,
            )
            summary.outcomes.append(
                RefreshOutcome(
                    analysis_id=analysis.id,
                    target_login=analysis.target_login,
                    owner_user_id=analysis.user_id,
                    token_source=source,
                    status="unexpected_error",
                    duration_ms=duration_ms,
                    error="record_run failed",
                )
            )
            summary.skipped += 1
            continue

        summary.succeeded += 1
        summary.outcomes.append(
            RefreshOutcome(
                analysis_id=analysis.id,
                target_login=analysis.target_login,
                owner_user_id=analysis.user_id,
                token_source=source,
                status="succeeded",
                duration_ms=duration_ms,
            )
        )

    await db.commit()
    return summary
