import json
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app import dependencies as dep_module
from app import main as app_module
from app.models import Badge, Report, ScoreBreakdown, ScoreResult, TierInfo
from app.narrative.budget import DailyBudget
from app.narrative.cache import NarrativeCache
from app.narrative.llm import FakeNarrativeLLM
from app.narrative.service import NarrativeService


def _fake_report() -> Report:
    z = ScoreResult(points=0, max_points=1)
    b = ScoreBreakdown(
        repo_quality=z,
        engineering_maturity=z,
        oss_collab=z,
        consistency=z,
        recruiter_signal=z,
        learning_trajectory=z,
    )
    return Report(
        username="testuser",
        tier=TierInfo(
            name="Professional Developer",
            sub_rank=50,
            band=(50, 65),
            next_tier="Senior Engineer",
            pts_to_next=5,
            prev_tier="Entry-Level Engineer",
            pts_above_prev=10,
        ),
        badges=[],
        breakdown=b,
        total=50,
        generated_at=datetime.now(UTC),
    )


async def _mock_get_report(username: str) -> Report:
    if username == "ghost":
        raise HTTPException(status_code=404, detail="GitHub user 'ghost' not found")
    if username.startswith("-"):
        raise HTTPException(status_code=400, detail="Invalid GitHub username")
    return _fake_report()


def _mock_get_service() -> NarrativeService:
    cache = NarrativeCache()
    budget = DailyBudget(limit=10)
    llm = FakeNarrativeLLM(tokens=["Hello", " ", "SSE", "!"])
    return NarrativeService(cache=cache, budget=budget, llm=llm)


@pytest.fixture
def _override_deps() -> None:
    app_module.app.dependency_overrides[
        dep_module.get_report_for_user
    ] = _mock_get_report
    app_module.app.dependency_overrides[
        dep_module.get_narrative_service
    ] = _mock_get_service
    yield
    app_module.app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_narrative_invalid_mode_returns_400(_override_deps: None) -> None:
    transport = ASGITransport(app=app_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/narrative/testuser?mode=invalid")
    assert resp.status_code == 400
    assert "invalid narrative mode" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_narrative_invalid_username_returns_400(
    _override_deps: None,
) -> None:
    transport = ASGITransport(app=app_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/narrative/-badname?mode=roast")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_narrative_unknown_user_returns_404(_override_deps: None) -> None:
    transport = ASGITransport(app=app_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/narrative/ghost?mode=roast")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_narrative_sse_streaming_format(_override_deps: None) -> None:
    transport = ASGITransport(app=app_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/narrative/testuser?mode=roast")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/event-stream; charset=utf-8"
    assert resp.headers["cache-control"] == "no-cache"

    lines = [line for line in resp.text.splitlines() if line]
    assert len(lines) == 4
    for i, tok in enumerate(["Hello", " ", "SSE", "!"]):
        assert lines[i].startswith("data: ")
        data = json.loads(lines[i][6:])
        assert data["chunk"] == tok
