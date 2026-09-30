"""A client that leaves mid-stream gets its LLM budget slot back (v1.0.5 SI-07).

Starlette usually delivers a disconnect as task cancellation while the stream
is waiting on the model, not as GeneratorExit at a yield, so both must refund.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request

from app.models import Report, ScoreBreakdown, ScoreResult, TierInfo
from app.narrative.budget import DailyBudget
from app.narrative.cache import NarrativeCache
from app.narrative.service import NarrativeService
from app.routers.narrative import get_narrative


def _report() -> Report:
    z = ScoreResult(points=10, max_points=30)
    return Report(
        username="octocat",
        tier=TierInfo(
            name="Hobbyist",
            sub_rank=42,
            band=(0, 50),
            next_tier="Student Builder",
            pts_to_next=8,
            prev_tier=None,
            pts_above_prev=42,
        ),
        badges=[],
        breakdown=ScoreBreakdown(
            repo_quality=z,
            engineering_maturity=z,
            oss_collab=z,
            consistency=z,
            recruiter_signal=z,
            learning_trajectory=z,
        ),
        total=42,
        generated_at=datetime.now(UTC),
    )


class _StallingLLM:
    """Streams one chunk, then stalls the way a reasoning model does mid-answer."""

    async def stream_chat(self, messages, **_kwargs):
        yield "Your commit history "
        await asyncio.sleep(30)
        yield "never arrives"


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/narrative/octocat",
            "headers": [],
            "query_string": b"",
            "client": ("203.0.113.7", 50000),
        }
    )


async def _open_stream(budget: DailyBudget):
    service = NarrativeService(cache=NarrativeCache(), budget=budget, llm=_StallingLLM())
    response = await get_narrative(
        request=_request(),
        username="octocat",
        _rl=None,
        report=_report(),
        service=service,
        db=AsyncMock(),
        session=None,
        mode="roast",
    )
    return response.body_iterator


async def test_disconnect_while_the_model_is_thinking_refunds_the_slot():
    budget = DailyBudget(limit=5)
    body = await _open_stream(budget)

    async def drain():
        async for _ in body:
            pass

    consumer = asyncio.create_task(drain())
    await asyncio.sleep(0.05)  # first chunk sent; now waiting on the model
    consumer.cancel()
    with pytest.raises(asyncio.CancelledError):
        await consumer
    await asyncio.sleep(0)  # let the shielded refund finish
    assert budget._remaining == 5


async def test_close_after_a_chunk_refunds_the_slot():
    budget = DailyBudget(limit=5)
    body = await _open_stream(budget)
    await body.__anext__()
    await body.aclose()
    assert budget._remaining == 5


async def test_no_refund_when_no_slot_was_consumed():
    budget = DailyBudget(limit=1)
    budget.try_consume()  # the day's only slot is gone: the stream serves the fallback
    body = await _open_stream(budget)
    await body.__anext__()
    await body.aclose()
    assert budget._remaining == 0
