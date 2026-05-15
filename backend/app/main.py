from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.github.client import GitHubClient
from app.ingestion.profile import ingest_profile
from app.models import Report
from app.scoring.engine import run_scoring_engine
from app.settings import VERSION, settings

app = FastAPI(title="Skill Issue API", version=VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": VERSION}


@app.get("/analyze/{username}", response_model=Report)
async def analyze_user(username: str) -> Report:
    """
    Ingests data for a GitHub user and returns a full scoring report.
    """
    if not settings.github_token:
        raise HTTPException(status_code=500, detail="GITHUB_TOKEN not configured on backend")

    async with GitHubClient(token=settings.github_token) as gh:
        try:
            profile = await ingest_profile(username, gh)
            report = run_scoring_engine(profile)
            return report
        except Exception as e:
            # Basic error handling for MVP
            raise HTTPException(
                status_code=404, detail=f"Error analyzing user '{username}': {e!s}"
            ) from None
