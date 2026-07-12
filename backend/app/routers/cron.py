from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import settings as settings_module
from app.auth.sessions import purge_expired_sessions
from app.cron import run_refresh_chunk
from app.db.session import get_db

router = APIRouter(prefix="/cron", tags=["cron"])


def require_cron_auth(
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """Verify Authorization: Bearer <CRON_SECRET>.

    503 when the secret is unset on the backend (prod misconfig surfaces at
    first fire). 401 for any missing/mismatched bearer. Constant-time compare
    so a timing oracle cannot probe the secret byte by byte.

    Reads through `settings_module.settings` (not a `from .. import settings`
    binding) so tests that reassign the singleton are seen at call time.
    """
    expected = settings_module.settings.cron_secret
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="cron_disabled",
        )
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    presented = authorization.removeprefix("Bearer ").strip()
    if not hmac.compare_digest(presented, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


# Vercel Cron Jobs invoke the scheduled path with an HTTP GET (there is no way
# to make a Vercel cron POST), so GET is the method that actually fires in
# production. POST is kept for manual triggers (`vercel crons run`, curl). Both
# go through `require_cron_auth` — Vercel injects the Bearer CRON_SECRET header
# on the scheduled GET. Before this, the route was POST-only and every daily
# fire 405'd before any handler code ran.
@router.api_route("/refresh-saved-analyses", methods=["GET", "POST"])
async def refresh_saved_analyses(
    db: Annotated[AsyncSession, Depends(get_db)],
    _auth: Annotated[None, Depends(require_cron_auth)],
) -> dict[str, object]:
    summary = await run_refresh_chunk(db)
    # Data minimization: drop expired session rows (encrypted GitHub tokens)
    # on the same daily tick. Independent of the refresh commit above.
    purged_sessions = await purge_expired_sessions(db)
    await db.commit()
    return {
        "processed": summary.processed,
        "succeeded": summary.succeeded,
        "skipped": summary.skipped,
        "rate_limited": summary.rate_limited,
        "deadline_reached": summary.deadline_reached,
        "purged_sessions": purged_sessions,
        "outcomes": [
            {
                "analysis_id": o.analysis_id,
                "target_login": o.target_login,
                "owner_user_id": o.owner_user_id,
                "token_source": str(o.token_source),
                "status": o.status,
                "duration_ms": o.duration_ms,
                "error": o.error,
            }
            for o in summary.outcomes
        ],
    }
