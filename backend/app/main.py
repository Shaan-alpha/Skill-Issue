import logging
import re

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.github.client import GitHubClient
from app.ingestion.profile import ingest_profile
from app.models import Report
from app.scoring.engine import run_scoring_engine
from app.settings import VERSION, settings

logger = logging.getLogger(__name__)

# GitHub usernames: 1-39 chars, alphanumeric or single hyphens, no leading/
# trailing hyphen. Source: https://github.com/shinnn/github-username-regex.
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$")

app = FastAPI(title="Skill Issue API", version=VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()],
    allow_origin_regex=settings.cors_allow_origin_regex,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": VERSION}


@app.get("/analyze/{username}", response_model=Report)
async def analyze_user(username: str) -> Report:
    """Ingest a GitHub user and return the deterministic scoring report."""
    if not _USERNAME_RE.fullmatch(username):
        raise HTTPException(status_code=400, detail="Invalid GitHub username")
    if not settings.github_token:
        raise HTTPException(status_code=500, detail="GITHUB_TOKEN not configured on backend")

    async with GitHubClient(token=settings.github_token) as gh:
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
