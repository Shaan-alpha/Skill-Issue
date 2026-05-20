"""End-to-end fault-injection: every Redis call fails, /analyze still
returns 200. The cache must never be a correctness boundary."""

from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response

from app import dependencies as dep_module
from app import main as app_module
from app.settings import Settings

if TYPE_CHECKING:
    from app.cache.client import RedisCache


@pytest.fixture
def _settings_with_token(monkeypatch: pytest.MonkeyPatch) -> None:
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
        "company": None,
        "blog": None,
        "hireable": True,
    }


def _repo_payload(name: str, *, language: str = "Python") -> dict[str, Any]:
    pushed = (datetime.now(UTC) - timedelta(days=5)).isoformat()
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


def _mock_github_for_testuser() -> None:
    """Minimum mocks for /analyze/testuser to complete end-to-end."""
    respx.get("https://api.github.com/users/testuser").mock(
        return_value=Response(200, json=_user_payload())
    )
    repos = [_repo_payload("alpha")]
    respx.get("https://api.github.com/users/testuser/repos").mock(
        return_value=Response(200, json=repos)
    )
    encoded = base64.b64encode(b"# Hello world").decode("ascii")
    respx.get("https://api.github.com/repos/testuser/testuser/readme").mock(
        return_value=Response(200, json={"content": encoded, "encoding": "base64"})
    )
    for repo in repos:
        owner, name = str(repo["full_name"]).split("/", 1)
        respx.get(
            f"https://api.github.com/repos/{owner}/{name}/languages"
        ).mock(return_value=Response(200, json={repo["language"]: 1000}))
        commits = [_commit_payload(days_ago=i) for i in range(5)]
        respx.get(
            url__startswith=f"https://api.github.com/repos/{owner}/{name}/commits"
        ).mock(return_value=Response(200, json=commits))
        respx.get(f"https://api.github.com/repos/{owner}/{name}/contents").mock(
            return_value=Response(
                200,
                json=[
                    {"name": "README.md", "type": "file"},
                    {"name": "tests", "type": "dir"},
                ],
            )
        )
        respx.get(f"https://api.github.com/repos/{owner}/{name}/license").mock(
            return_value=Response(200, json={"license": {"spdx_id": "MIT"}})
        )
        respx.get(
            f"https://api.github.com/repos/{owner}/{name}/contents/.github/workflows"
        ).mock(return_value=Response(200, json=[]))
        respx.get(f"https://api.github.com/repos/{owner}/{name}/readme").mock(
            return_value=Response(
                200,
                json={
                    "content": base64.b64encode(b"# README\n").decode(),
                    "encoding": "base64",
                },
            )
        )

    respx.post("https://api.github.com/graphql").mock(
        side_effect=[
            Response(200, json={"data": {"user": {"pinnedItems": {"nodes": []}}}}),
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
            Response(
                200,
                json={
                    "data": {
                        "user": {
                            "contributionsCollection": {
                                "commitContributionsByRepository": []
                            }
                        }
                    }
                },
            ),
        ]
    )


@pytest.mark.asyncio
@respx.mock
async def test_analyze_succeeds_when_every_redis_call_fails(
    _settings_with_token: None, fake_cache: RedisCache, fake_redis, monkeypatch
) -> None:
    """Fail-open contract end-to-end: every Redis call raises, /analyze
    still returns 200 with a valid Report. The cache is never a
    correctness boundary."""
    # Inject the broken cache.
    monkeypatch.setattr(dep_module, "get_cache", lambda: fake_cache)
    fake_redis.fail_next = 10_000  # every call for the duration of this test
    _mock_github_for_testuser()

    transport = ASGITransport(app=app_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/analyze/testuser")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["username"] == "testuser"
    assert "tier" in body
    assert "total" in body


@pytest.mark.asyncio
@respx.mock
async def test_analyze_works_without_cache_configured(
    _settings_with_token: None, monkeypatch
) -> None:
    """When get_cache() returns None (no Upstash configured), /analyze runs
    the original anonymous path — proves backwards compat."""
    monkeypatch.setattr(dep_module, "get_cache", lambda: None)
    _mock_github_for_testuser()

    transport = ASGITransport(app=app_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/analyze/testuser")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["username"] == "testuser"
