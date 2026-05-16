import logging
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.dependencies import get_report_for_user
from app.models import Report
from app.routers import narrative
from app.settings import VERSION, settings

logger = logging.getLogger(__name__)

app = FastAPI(title="Skill Issue API", version=VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()
    ],
    allow_origin_regex=settings.cors_allow_origin_regex,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(narrative.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": VERSION}


@app.get("/analyze/{username}", response_model=Report)
async def analyze_user(
    report: Annotated[Report, Depends(get_report_for_user)],
) -> Report:
    """Ingest a GitHub user and return the deterministic scoring report."""
    return report
