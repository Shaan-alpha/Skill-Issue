import json
import logging
import re
from functools import lru_cache
from typing import TYPE_CHECKING, Annotated

import httpx
from fastapi import Depends, HTTPException

from app.auth.dependencies import optional_session
from app.cache.client import RedisCache
from app.cache.keys import NAMESPACE_REPORT, report_key
from app.cache.locks import singleflight
from app.github.client import GitHubClient
from app.ingestion.profile import NotAnIndividualError, ingest_profile
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
def get_cache() -> RedisCache | None:
    """Process-wide singleton wrapping the configured Upstash Redis client.

    Returns None when `UPSTASH_REDIS_REST_URL` is unset — every cache
    integration then short-circuits to today's behaviour.
    """
    url = settings.upstash_redis_rest_url
    token = settings.upstash_redis_rest_token
    if not url or not token:
        return None
    try:
        from upstash_redis.asyncio import Redis  # type: ignore[import-not-found]
    except ImportError:
        return None
    return RedisCache(redis=Redis(url=url, token=token))


@lru_cache
def get_narrative_cache() -> NarrativeCache:
    return NarrativeCache(redis=get_cache())


@lru_cache
def get_daily_budget() -> DailyBudget:
    return DailyBudget(limit=settings.narrative_daily_limit, redis=get_cache())


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
    """Validate username, then return a Report — from cache when possible,
    otherwise via live ingest + scoring with singleflight coalescing."""
    if not _USERNAME_RE.fullmatch(username):
        raise HTTPException(status_code=400, detail="Invalid GitHub username")

    cache = get_cache()
    cache_key = report_key(username)

    # Layer A: try the Report cache first.
    if cache is not None:
        cached = await cache.get_json(NAMESPACE_REPORT, cache_key)
        if cached is not None:
            try:
                return Report.model_validate(cached)
            except Exception:
                logger.warning(
                    "cached Report for %s failed validation; ignoring",
                    cache_key,
                    exc_info=True,
                )

    # Layer B: singleflight around the cold ingest.
    if cache is not None:
        async with singleflight(cache, NAMESPACE_REPORT, cache_key) as got:
            if not got:
                # Another holder finished; check the cache one more time.
                cached = await cache.get_json(NAMESPACE_REPORT, cache_key)
                if cached is not None:
                    try:
                        return Report.model_validate(cached)
                    except Exception:
                        pass
                # Lock holder timed out or returned bad data — fall through
                # to a live ingest, no lock held.

            report = await _live_ingest(username, session, cache)

            # Populate the cache for next time.
            try:
                await cache.set_json(
                    NAMESPACE_REPORT,
                    cache_key,
                    json.loads(report.model_dump_json()),
                    ttl_seconds=settings.cache_report_ttl_seconds,
                )
            except Exception:
                logger.warning(
                    "report cache set failed for %s", cache_key, exc_info=True
                )

            return report

    # No cache configured — original behaviour.
    return await _live_ingest(username, session, cache=None)


async def _live_ingest(
    username: str,
    session: "_ResolvedSession | None",
    cache: RedisCache | None,
) -> Report:
    access_token = (
        getattr(session, "access_token", None) if session is not None else None
    ) or settings.github_token

    if not access_token:
        raise HTTPException(
            status_code=500, detail="GITHUB_TOKEN not configured on backend"
        )

    async with GitHubClient(token=access_token, cache=cache) as gh:
        try:
            profile = await ingest_profile(username, gh)
        except NotAnIndividualError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
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
