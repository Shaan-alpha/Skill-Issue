from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from app.db.models import Narrative

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def save_narrative(
    db: AsyncSession,
    *,
    analysis_run_id: int,
    mode: str,
    text: str,
    provider: str,
    model_name: str | None,
    is_fallback: bool,
) -> Narrative:
    """Upsert a narrative row for (analysis_run_id, mode)."""
    existing = await db.scalar(
        select(Narrative).where(
            Narrative.analysis_run_id == analysis_run_id,
            Narrative.mode == mode,
        )
    )
    if existing is None:
        n = Narrative(
            analysis_run_id=analysis_run_id,
            mode=mode,
            text=text,
            provider=provider,
            model_name=model_name,
            is_fallback=is_fallback,
        )
        db.add(n)
        await db.flush()
        return n

    existing.text = text
    existing.provider = provider
    existing.model_name = model_name
    existing.is_fallback = is_fallback
    await db.flush()
    return existing
