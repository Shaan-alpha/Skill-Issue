import json
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app import dependencies as dep_module
from app import main as app_module
from app.models import Report, ScoreBreakdown, ScoreResult, TierInfo
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
    app_module.app.dependency_overrides[dep_module.get_report_for_user] = _mock_get_report
    app_module.app.dependency_overrides[dep_module.get_narrative_service] = _mock_get_service
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


async def test_signed_in_narrative_persists(db, monkeypatch):
    """When a session is present, the assembled narrative is saved to `narratives`."""
    import base64
    import secrets

    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import select

    monkeypatch.setenv(
        "SESSION_TOKEN_ENC_KEY", base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    )
    monkeypatch.setenv("GITHUB_TOKEN", "p")

    from app.auth.sessions import create_session
    from app.db.models import Narrative, User
    from app.main import app

    u = User(github_id=1, github_login="me")
    db.add(u)
    await db.flush()
    sid = await create_session(db, user_id=u.id, github_access_token="t", ttl_days=30)
    await db.commit()

    from app import dependencies as deps
    from app.narrative import service as nsvc

    def fake_score(profile):
        from datetime import UTC, datetime

        from app.models import Report, ScoreBreakdown, ScoreResult, TierInfo

        return Report(
            username=profile.login,
            tier=TierInfo(
                name="Senior Engineer",
                sub_rank=50,
                band=[65, 80],
                next_tier="Staff Engineer",
                chip_label="50% into tier",
            ),
            badges=[],
            breakdown=ScoreBreakdown(
                repo_quality=ScoreResult(points=25, max_points=30),
                engineering_maturity=ScoreResult(points=15, max_points=20),
                oss_collab=ScoreResult(points=10, max_points=15),
                consistency=ScoreResult(points=8, max_points=10),
                recruiter_signal=ScoreResult(points=12, max_points=15),
                learning_trajectory=ScoreResult(points=8, max_points=10),
            ),
            total=78,
            generated_at=datetime.now(UTC),
        )

    async def fake_ingest(uname, gh):
        return type("P", (), {"login": uname})()

    async def fake_run_engine(profile, gh):
        return fake_score(profile)

    async def fake_stream(self, mode, report):
        for tok in ("Hello ", "world."):
            yield tok

    monkeypatch.setattr(deps, "ingest_profile", fake_ingest)
    monkeypatch.setattr(deps, "run_scoring_engine", fake_run_engine)
    monkeypatch.setattr(nsvc.NarrativeService, "stream_narrative", fake_stream)

    from app.db.session import get_db

    async def _o():
        yield db

    app.dependency_overrides[get_db] = _o

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        ac.cookies.set("si_session", sid)
        r = await ac.get("/narrative/octocat?mode=roast")
        assert r.status_code == 200
        async for _ in r.aiter_text():
            pass
    app.dependency_overrides.clear()

    n = await db.scalar(select(Narrative).where(Narrative.mode == "roast"))
    assert n is not None
    assert "Hello" in n.text
    # Provider derives from settings.narrative_base_url. Test env has it unset,
    # so the OpenAI default applies; v0.8.4 fix prevents prod (Groq) from
    # being silently mislabeled as openai.
    assert n.provider == "openai"
    assert n.is_fallback is False
