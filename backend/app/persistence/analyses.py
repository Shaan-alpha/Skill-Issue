from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

from sqlalchemy import desc, func, select
from sqlalchemy.orm import aliased

from app.db.models import Analysis, AnalysisRun

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

Sort = Literal["recent", "score_desc", "score_asc"]


class AnalysisNotFound(Exception):
    """Raised when an analysis id does not exist or the caller is not the owner."""


def _new_slug() -> str:
    """12-char URL-safe slug (~72 bits of entropy)."""
    return secrets.token_urlsafe(9)[:12]


async def upsert_analysis(
    db: AsyncSession,
    *,
    user_id: int,
    target_login: str,
    target_github_id: int | None = None,
) -> Analysis:
    a = await db.scalar(
        select(Analysis).where(Analysis.user_id == user_id, Analysis.target_login == target_login)
    )
    if a is None:
        a = Analysis(
            user_id=user_id,
            target_login=target_login,
            target_github_id=target_github_id,
        )
        db.add(a)
        await db.flush()
        return a
    if target_github_id is not None and a.target_github_id is None:
        a.target_github_id = target_github_id
    a.updated_at = datetime.now(UTC)
    await db.flush()
    return a


async def record_run(
    db: AsyncSession,
    *,
    analysis_id: int,
    report_json: dict[str, Any],
    total_score: int,
    tier_name: str,
    scores_hash: str,
    started_at: datetime,
    completed_at: datetime,
    latency_ms: int,
) -> AnalysisRun:
    run = AnalysisRun(
        analysis_id=analysis_id,
        report_json=report_json,
        total_score=total_score,
        tier_name=tier_name,
        scores_hash=scores_hash,
        ingestion_started_at=started_at,
        ingestion_completed_at=completed_at,
        ingestion_latency_ms=latency_ms,
    )
    db.add(run)
    await db.flush()

    a = await db.get(Analysis, analysis_id)
    if a is not None:
        a.latest_run_id = run.id
        a.updated_at = datetime.now(UTC)
        await db.flush()
    return run


async def get_user_analysis_by_target(
    db: AsyncSession,
    *,
    user_id: int,
    target_login: str,
) -> Analysis | None:
    """Return the user's saved Analysis for this target, or None.

    Matches case-insensitively on target_login. v0.5.0 stored canonical
    GitHub case ('Shaan-alpha'); URL slugs usually arrive lowercased.
    """
    stmt = select(Analysis).where(
        Analysis.user_id == user_id,
        func.lower(Analysis.target_login) == target_login.lower(),
    )
    return await db.scalar(stmt)


async def _owned_analysis(db: AsyncSession, analysis_id: int, owner_id: int) -> Analysis:
    a = await db.scalar(
        select(Analysis).where(Analysis.id == analysis_id, Analysis.user_id == owner_id)
    )
    if a is None:
        raise AnalysisNotFound()
    return a


async def set_share_slug(db: AsyncSession, *, analysis_id: int, owner_id: int) -> str:
    a = await _owned_analysis(db, analysis_id, owner_id)
    slug = _new_slug()
    a.is_public = True
    a.share_slug = slug
    a.updated_at = datetime.now(UTC)
    await db.flush()
    return slug


async def revoke_share_slug(db: AsyncSession, *, analysis_id: int, owner_id: int) -> None:
    a = await _owned_analysis(db, analysis_id, owner_id)
    a.is_public = False
    a.share_slug = None
    a.updated_at = datetime.now(UTC)
    await db.flush()


async def get_analysis_by_slug(db: AsyncSession, slug: str) -> Analysis | None:
    return await db.scalar(
        select(Analysis).where(Analysis.share_slug == slug, Analysis.is_public.is_(True))
    )


async def list_user_analyses(
    db: AsyncSession,
    *,
    user_id: int,
    sort: Sort = "recent",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Analysis], int]:
    """Return (rows, total). 1-indexed pages."""
    latest = aliased(AnalysisRun)
    base = (
        select(Analysis, latest)
        .where(Analysis.user_id == user_id)
        .join(latest, Analysis.latest_run_id == latest.id, isouter=True)
    )
    if sort == "recent":
        base = base.order_by(desc(latest.ingestion_completed_at))
    elif sort == "score_desc":
        base = base.order_by(desc(latest.total_score))
    elif sort == "score_asc":
        base = base.order_by(latest.total_score)

    total = await db.scalar(
        select(func.count()).select_from(Analysis).where(Analysis.user_id == user_id)
    )

    offset = max(0, (page - 1) * page_size)
    rows = (await db.execute(base.offset(offset).limit(page_size))).all()
    return [r.Analysis for r in rows], int(total or 0)
