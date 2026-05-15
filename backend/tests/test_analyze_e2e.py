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

from app import main as app_module
from app.settings import Settings


@pytest.fixture
def _settings_with_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the app to see a github_token without touching the real .env."""
    monkeypatch.setattr(app_module, "settings", Settings(github_token="ghs_test"))


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
        respx.get(
            url__startswith=f"https://api.github.com/repos/{owner}/{name}/commits"
        ).mock(return_value=Response(200, json=commits_by_repo.get(name, [])))

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
        ]
    )


@pytest.mark.asyncio
@respx.mock
async def test_analyze_returns_complete_report(_settings_with_token: None) -> None:
    """Happy path: every scorer runs, breakdown is complete, total = sum of parts."""
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
    assert body["category"] in {
        "Student Builder",
        "Entry-Level Engineer",
        "Professional Developer",
        "Senior Engineer",
        "OSS Contributor",
        "Indie Hacker",
    }
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
async def test_analyze_unknown_user_returns_404(_settings_with_token: None) -> None:
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
async def test_analyze_without_token_returns_500(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_module, "settings", Settings(github_token=None))
    transport = ASGITransport(app=app_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/analyze/anybody")

    assert resp.status_code == 500
    assert "GITHUB_TOKEN" in resp.json()["detail"]
