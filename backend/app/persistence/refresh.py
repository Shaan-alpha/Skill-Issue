from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import asc, nulls_first, select
from sqlalchemy.orm import aliased

from app.db.models import Analysis, AnalysisRun

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def iter_stale_analyses(
    db: AsyncSession,
    *,
    limit: int = 25,
    stale_after_hours: int = 24,
) -> list[Analysis]:
    """Return up to `limit` analyses whose latest run completed > N hours ago
    (or whose run set is empty). Ordered oldest-first; rows with no run sort
    before any row with a run.
    """
    latest = aliased(AnalysisRun)
    cutoff = datetime.now(UTC) - timedelta(hours=stale_after_hours)
    stmt = (
        select(Analysis)
        .join(latest, Analysis.latest_run_id == latest.id, isouter=True)
        .where((latest.ingestion_completed_at.is_(None)) | (latest.ingestion_completed_at < cutoff))
        .order_by(nulls_first(asc(latest.ingestion_completed_at)))
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return list(rows)
