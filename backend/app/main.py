import hashlib
import json
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.auth.dependencies import optional_session
from app.db.engine import engine
from app.db.session import get_db
from app.dependencies import get_report_for_user
from app.models import Report
from app.persistence.analyses import record_run, upsert_analysis
from app.routers import analyses, auth, me, narrative, share
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


@app.exception_handler(StarletteHTTPException)
async def _http_exc_handler(_request: Request, exc: StarletteHTTPException):
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(exc.detail, status_code=exc.status_code)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


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
app.include_router(me.router)
app.include_router(analyses.router)
app.include_router(share.router)


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


def _scores_hash(report: Report) -> str:
    return hashlib.sha256(
        json.dumps(report.model_dump(mode="json"), sort_keys=True).encode("utf-8")
    ).hexdigest()


@app.get("/analyze/{username}", response_model=Report)
async def analyze_user(
    username: str,  # path param forwarded to get_report_for_user via request scope
    report: Annotated[Report, Depends(get_report_for_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    session: Annotated[object | None, Depends(optional_session)],
) -> Report:
    """Ingest + score. Persists when a session is present; anonymous calls write nothing."""
    started_at = datetime.now(UTC)
    if session is not None:
        completed_at = datetime.now(UTC)
        analysis = await upsert_analysis(
            db,
            user_id=session.user.id,
            target_login=report.username,
        )
        await record_run(
            db,
            analysis_id=analysis.id,
            report_json=report.model_dump(mode="json"),
            total_score=report.total,
            tier_name=report.tier.name,
            scores_hash=_scores_hash(report),
            started_at=started_at,
            completed_at=completed_at,
            latency_ms=int((completed_at - started_at).total_seconds() * 1000),
        )
    return report
