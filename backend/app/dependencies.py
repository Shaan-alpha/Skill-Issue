import logging
import re
from functools import lru_cache
from typing import TYPE_CHECKING, Annotated

import httpx
from fastapi import Depends, HTTPException

from app.auth.dependencies import optional_session
from app.github.client import GitHubClient
from app.ingestion.profile import ingest_profile
from app.models import Report
from app.narrative.budget import DailyBudget
from app.narrative.cache import NarrativeCache
from app.narrative.llm import NarrativeLLM
from app.narrative.service import NarrativeService
from app.scoring.engine import run_scoring_engine
from app.settings import settings

if TYPE_CHECKING:
    from app.auth.dependencies import _ResolvedSession

logger = logging.getLogger(__name__)

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$")


@lru_cache
def get_narrative_cache() -> NarrativeCache:
    return NarrativeCache()


@lru_cache
def get_daily_budget() -> DailyBudget:
    return DailyBudget(limit=settings.narrative_daily_limit)


@lru_cache
def get_narrative_service() -> NarrativeService:
    cache = get_narrative_cache()
    budget = get_daily_budget()
    llm = NarrativeLLM(
        api_key=settings.openai_api_key or "missing-key",
        model=settings.narrative_model,
        base_url=settings.narrative_base_url,
    )
    return NarrativeService(cache=cache, budget=budget, llm=llm)


async def get_report_for_user(
    username: str,
    session: Annotated["_ResolvedSession | None", Depends(optional_session)] = None,
) -> Report:
    """Validate username, fetch profile from GitHub, and run scoring engine."""
    if not _USERNAME_RE.fullmatch(username):
        raise HTTPException(status_code=400, detail="Invalid GitHub username")

    access_token = (
        getattr(session, "access_token", None) if session is not None else None
    ) or settings.github_token

    if not access_token:
        raise HTTPException(
            status_code=500, detail="GITHUB_TOKEN not configured on backend"
        )

    async with GitHubClient(token=access_token) as gh:
        try:
            profile = await ingest_profile(username, gh)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(
                    status_code=404, detail=f"GitHub user '{username}' not found"
                ) from e
            logger.exception("GitHub HTTP error analyzing %s", username)
            raise HTTPException(
                status_code=502, detail=f"GitHub API error: {e.response.status_code}"
            ) from e
        except Exception:
            logger.exception("Unexpected error analyzing %s", username)
            raise HTTPException(
                status_code=500, detail=f"Failed to analyze user '{username}'"
            ) from None

        return await run_scoring_engine(profile, gh)
