"""End-to-end test for GET /analyze/{username}.

Exercises the real ingestion → scoring → response serialization path with
GitHub HTTP responses mocked at the network layer. Locks the contract the
unit tests can't see: that the data shapes ingestion produces are exactly
what the scorers expect.
"""

from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response

from app import dependencies as dep_module
from app import main as app_module
from app.settings import Settings


@pytest.fixture
def _settings_with_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the app to see a github_token without touching the real .env."""
    monkeypatch.setattr(app_module, "settings", Settings(github_token="ghs_test"))
    monkeypatch.setattr(dep_module, "settings", Settings(github_token="ghs_test"))


def _user_payload(login: str = "testuser") -> dict[str, Any]:
    return {
        "login": login,
        "id": 1,
        "bio": "Builds things.",
        "followers": 42,
        "public_repos": 3,
        "created_at": "2020-01-15T00:00:00Z",
        "company": "@example-co",
        "blog": "https://example.dev",
        "hireable": True,
    }


def _repo_payload(name: str, *, language: str, days_since_push: int = 5) -> dict[str, Any]:
    pushed = (datetime.now(UTC) - timedelta(days=days_since_push)).isoformat()
    return {
        "name": name,
        "full_name": f"testuser/{name}",
        "owner": {"login": "testuser"},
        "language": language,
        "stargazers_count": 75,
        "forks_count": 3,
        "fork": False,
        "size": 512,
        "pushed_at": pushed,
        "created_at": "2021-06-01T00:00:00Z",
    }


def _commit_payload(days_ago: int) -> dict[str, Any]:
    when = (datetime.now(UTC) - timedelta(days=days_ago)).isoformat()
    return {"commit": {"author": {"date": when}}}


def _mock_github_for_testuser(
    repos: list[dict[str, Any]], commits_by_repo: dict[str, list[dict[str, Any]]]
) -> None:
    respx.get("https://api.github.com/users/testuser").mock(
        return_value=Response(200, json=_user_payload())
    )
    respx.get("https://api.github.com/users/testuser/repos").mock(
        return_value=Response(200, json=repos)
    )
    encoded = base64.b64encode(b"# Hello world").decode("ascii")
    respx.get("https://api.github.com/repos/testuser/testuser/readme").mock(
        return_value=Response(200, json={"content": encoded, "encoding": "base64"})
    )
    for repo in repos:
        owner, name = str(repo["full_name"]).split("/", 1)
        respx.get(f"https://api.github.com/repos/{owner}/{name}/languages").mock(
            return_value=Response(200, json={repo["language"]: 1000})
        )
        respx.get(url__startswith=f"https://api.github.com/repos/{owner}/{name}/commits").mock(
            return_value=Response(200, json=commits_by_repo.get(name, []))
        )
        # Root-contents enrichment: give every test repo a healthy set of signals
        # so the e2e contract test exercises the README/tests/CI/deployment paths.
        respx.get(f"https://api.github.com/repos/{owner}/{name}/contents").mock(
            return_value=Response(
                200,
                json=[
                    {"name": "README.md", "type": "file"},
                    {"name": "tests", "type": "dir"},
                    {"name": ".github", "type": "dir"},
                    {"name": "Dockerfile", "type": "file"},
                ],
            )
        )
        # Pro+ depth endpoints (Professional Developer tier and above)
        respx.get(f"https://api.github.com/repos/{owner}/{name}/license").mock(
            return_value=Response(200, json={"license": {"spdx_id": "MIT"}})
        )
        respx.get(f"https://api.github.com/repos/{owner}/{name}/contents/.github/workflows").mock(
            return_value=Response(
                200,
                json=[{"name": "ci.yml", "type": "file"}],
            )
        )
        respx.get(f"https://api.github.com/repos/{owner}/{name}/readme").mock(
            return_value=Response(
                200,
                json={
                    "content": base64.b64encode(b"# README\n## Setup").decode(),
                    "encoding": "base64",
                },
            )
        )

    respx.post("https://api.github.com/graphql").mock(
        side_effect=[
            Response(
                200,
                json={"data": {"user": {"pinnedItems": {"nodes": []}}}},
            ),
            Response(
                200,
                json={
                    "data": {
                        "user": {
                            "hasSponsorsListing": False,
                            "isGitHubStar": False,
                            "isDeveloperProgramMember": False,
                            "pullRequests": {"totalCount": 0, "nodes": []},
                            "contributionsCollection": {
                                "pullRequestReviewContributions": {"totalCount": 0}
                            },
                        }
                    }
                },
            ),
            # REVIEW_DEPTH (Senior Engineer tier and above)
            Response(
                200,
                json={
                    "data": {
                        "user": {
                            "contributionsCollection": {
                                "pullRequestReviewContributions": {"nodes": []}
                            }
                        }
                    }
                },
            ),
            # CONTRIBUTION_REPOS (Staff Engineer tier and above)
            Response(
                200,
                json={
                    "data": {
                        "user": {"contributionsCollection": {"commitContributionsByRepository": []}}
                    }
                },
            ),
        ]
    )


@pytest.mark.asyncio
@respx.mock
async def test_analyze_returns_complete_report(
    _settings_with_token: None,
) -> None:
    """Happy path: every scorer runs, breakdown is complete, total = sum of
    parts."""
    repos = [
        _repo_payload("alpha", language="TypeScript"),
        _repo_payload("beta", language="Python"),
    ]
    # 35 commit days spread across the last 90 days — exercises consistency
    # cadence + dry-spell + volume signals against tz-aware UTC datetimes.
    commits = [_commit_payload(days_ago=i * 2) for i in range(35)]
    _mock_github_for_testuser(repos, {"alpha": commits, "beta": commits[:5]})

    transport = ASGITransport(app=app_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/analyze/testuser")

    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Shape: every bucket the frontend reads must be present.
    assert body["username"] == "testuser"
    assert "tier" in body
    tier = body["tier"]
    assert tier["name"] in {
        "Hobbyist",
        "Student Builder",
        "Entry-Level Engineer",
        "Professional Developer",
        "Senior Engineer",
        "Staff Engineer",
        "Principal Engineer",
    }
    assert 0 <= tier["sub_rank"] <= 100
    assert isinstance(body["badges"], list)
    breakdown = body["breakdown"]
    expected_keys = {
        "repo_quality",
        "engineering_maturity",
        "oss_collab",
        "consistency",
        "recruiter_signal",
        "learning_trajectory",
    }
    assert set(breakdown) == expected_keys

    for key, bucket in breakdown.items():
        assert isinstance(bucket["points"], int), key
        assert isinstance(bucket["max_points"], int), key
        assert 0 <= bucket["points"] <= bucket["max_points"], key
        assert isinstance(bucket["evidence"], list), key

    # The headline number must be the literal sum of the buckets. No fudge.
    assert body["total"] == sum(b["points"] for b in breakdown.values())
    assert 0 <= body["total"] <= 100

    # Regression guard for the two bugs we shipped in v0.1.0:
    # - consistency.score crashed on strptime(datetime, ...)
    # - learning_trajectory.score crashed comparing naive vs aware datetimes
    # Reaching this assertion at all proves both paths ran without raising.
    assert breakdown["consistency"]["max_points"] == 10
    assert breakdown["learning_trajectory"]["max_points"] == 10


@pytest.mark.asyncio
@respx.mock
async def test_analyze_unknown_user_returns_404(
    _settings_with_token: None,
) -> None:
    respx.get("https://api.github.com/users/ghost").mock(
        return_value=Response(404, json={"message": "Not Found"})
    )

    transport = ASGITransport(app=app_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/analyze/ghost")

    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_username",
    [
        "-leading-hyphen",
        "trailing-hyphen-",
        "double--hyphen",
        "has space",
        "has/slash",
        "name@with@at",
        "a" * 40,
        "",
    ],
)
async def test_analyze_rejects_invalid_username(
    _settings_with_token: None, bad_username: str
) -> None:
    transport = ASGITransport(app=app_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/analyze/{bad_username}")

    # FastAPI returns 404 when the path itself is empty; the validator handles
    # the rest with 400.
    assert resp.status_code in {400, 404}


@pytest.mark.asyncio
async def test_analyze_without_token_returns_500(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_module, "settings", Settings(github_token=None))
    monkeypatch.setattr(dep_module, "settings", Settings(github_token=None))
    transport = ASGITransport(app=app_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/analyze/anybody")

    assert resp.status_code == 500
    assert "GITHUB_TOKEN" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_signed_in_analyze_persists_run(db, monkeypatch):
    """When a session cookie is sent, /analyze writes an analyses + analysis_runs row."""
    import base64
    import secrets

    from httpx import ASGITransport, AsyncClient

    monkeypatch.setenv(
        "SESSION_TOKEN_ENC_KEY", base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    )
    monkeypatch.setenv("GITHUB_TOKEN", "project-token")

    from sqlalchemy import select

    from app.auth.sessions import create_session
    from app.db.models import Analysis, AnalysisRun, User
    from app.main import app

    u = User(github_id=1, github_login="me")
    db.add(u)
    await db.flush()
    sid = await create_session(db, user_id=u.id, github_access_token="user-token", ttl_days=30)
    await db.commit()

    from app import dependencies as deps

    async def fake_ingest(username, gh):
        return type("P", (), {"login": username})()

    async def fake_run_engine(profile, gh):
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
                repo_quality=ScoreResult(points=20, max_points=30),
                engineering_maturity=ScoreResult(points=10, max_points=20),
                oss_collab=ScoreResult(points=10, max_points=15),
                consistency=ScoreResult(points=5, max_points=10),
                recruiter_signal=ScoreResult(points=10, max_points=15),
                learning_trajectory=ScoreResult(points=5, max_points=10),
            ),
            total=60,
            generated_at=datetime.now(UTC),
        )

    monkeypatch.setattr(deps, "ingest_profile", fake_ingest)
    monkeypatch.setattr(deps, "run_scoring_engine", fake_run_engine)

    from app.db.session import get_db

    async def _o():
        yield db

    app.dependency_overrides[get_db] = _o

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        ac.cookies.set("si_session", sid)
        r = await ac.get("/analyze/octocat")
    app.dependency_overrides.clear()
    assert r.status_code == 200

    analysis = await db.scalar(
        select(Analysis).where(Analysis.user_id == u.id, Analysis.target_login == "octocat")
    )
    assert analysis is not None
    run = await db.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis.id))
    assert run is not None
    assert run.total_score == 60
    assert run.tier_name == "Senior Engineer"
    assert analysis.latest_run_id == run.id


@pytest.mark.asyncio
async def test_anonymous_analyze_does_not_persist(db, monkeypatch):
    """Anonymous /analyze writes nothing — landing-page demo flow unchanged."""
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import func, select

    from app import dependencies as deps
    from app.db.models import Analysis
    from app.main import app

    monkeypatch.setenv("GITHUB_TOKEN", "project-token")
    # setenv alone does nothing here: app/dependencies.py binds the settings
    # object at import via `from app.settings import settings`, so it keeps
    # whatever GITHUB_TOKEN was on disk. This is the anonymous path, which has
    # no session token to fall back on, so with an unset token the request 500s
    # at the "GITHUB_TOKEN not configured" guard. It passed only on machines
    # with a real token in .env, and failed the moment it ran in CI.
    monkeypatch.setattr(deps.settings, "github_token", "project-token")

    async def fake_ingest(username, gh):
        return type("P", (), {"login": username})()

    async def fake_run_engine(profile, gh):
        from datetime import UTC, datetime

        from app.models import Report, ScoreBreakdown, ScoreResult, TierInfo

        return Report(
            username=profile.login,
            tier=TierInfo(
                name="Hobbyist",
                sub_rank=10,
                band=[0, 30],
                next_tier="Student Builder",
                chip_label="10% into tier",
            ),
            badges=[],
            breakdown=ScoreBreakdown(
                repo_quality=ScoreResult(points=0, max_points=30),
                engineering_maturity=ScoreResult(points=0, max_points=20),
                oss_collab=ScoreResult(points=0, max_points=15),
                consistency=ScoreResult(points=0, max_points=10),
                recruiter_signal=ScoreResult(points=0, max_points=15),
                learning_trajectory=ScoreResult(points=0, max_points=10),
            ),
            total=0,
            generated_at=datetime.now(UTC),
        )

    monkeypatch.setattr(deps, "ingest_profile", fake_ingest)
    monkeypatch.setattr(deps, "run_scoring_engine", fake_run_engine)

    from app.db.session import get_db

    async def _o():
        yield db

    app.dependency_overrides[get_db] = _o

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.get("/analyze/octocat")
    app.dependency_overrides.clear()
    assert r.status_code == 200
    count = await db.scalar(select(func.count()).select_from(Analysis))
    assert count == 0
