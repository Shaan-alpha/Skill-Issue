import json
from collections.abc import AsyncIterator
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.dependencies import get_narrative_service, get_report_for_user
from app.models import Report
from app.narrative.service import NarrativeService

router = APIRouter(tags=["narrative"])


@router.get("/narrative/{username}")
async def get_narrative(
    username: str,
    report: Annotated[Report, Depends(get_report_for_user)],
    service: Annotated[NarrativeService, Depends(get_narrative_service)],
    mode: str = Query("roast", description="Narrative mode: roast or mentor"),
) -> StreamingResponse:
    """Stream AI narrative critique or mentorship over Server-Sent Events
    (SSE)."""
    if mode not in ("roast", "mentor"):
        raise HTTPException(
            status_code=400,
            detail="Invalid narrative mode; must be 'roast' or 'mentor'",
        )

    typed_mode: Literal["roast", "mentor"] = (
        "roast" if mode == "roast" else "mentor"
    )

    async def event_generator() -> AsyncIterator[str]:
        async for chunk in service.stream_narrative(typed_mode, report):
            payload = json.dumps({"chunk": chunk})
            yield f"data: {payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
