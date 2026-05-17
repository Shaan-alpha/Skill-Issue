import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.db.engine import engine
from app.dependencies import get_report_for_user
from app.models import Report
from app.routers import auth, narrative
from app.settings import VERSION, settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        logger.exception("DB ping at startup failed")
    yield
    await engine.dispose()


app = FastAPI(title="Skill Issue API", version=VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()
    ],
    allow_origin_regex=settings.cors_allow_origin_regex,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(narrative.router)
app.include_router(auth.router)


@app.get("/health")
async def health() -> dict[str, str]:
    db_status = "up"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "down"
    return {
        "status": "ok" if db_status == "up" else "degraded",
        "version": VERSION,
        "db": db_status,
    }


@app.get("/analyze/{username}", response_model=Report)
async def analyze_user(
    report: Annotated[Report, Depends(get_report_for_user)],
) -> Report:
    """Ingest a GitHub user and return the deterministic scoring report."""
    return report
