import json
from pathlib import Path

import pytest
import respx
from httpx import Response

from app.github.client import GitHubClient

FIXTURES = Path(__file__).parent.parent / "fixtures" / "github_responses"


@pytest.mark.asyncio
@respx.mock
async def test_get_user_returns_typed_payload() -> None:
    payload = json.loads((FIXTURES / "user_octocat.json").read_text())
    respx.get("https://api.github.com/users/octocat").mock(
        return_value=Response(200, json=payload, headers={"X-RateLimit-Remaining": "4999"})
    )

    async with GitHubClient(token="ghs_test") as gh:
        user = await gh.get_user("octocat")

    assert user["login"] == "octocat"
    assert user["public_repos"] >= 0


@pytest.mark.asyncio
@respx.mock
async def test_get_repo_root_contents_returns_entry_names() -> None:
    respx.get("https://api.github.com/repos/octocat/Hello-World/contents").mock(
        return_value=Response(
            200,
            json=[
                {"name": "README.md", "type": "file"},
                {"name": "tests", "type": "dir"},
                {"name": "Dockerfile", "type": "file"},
            ],
        )
    )

    async with GitHubClient(token="ghs_test") as gh:
        names = await gh.get_repo_root_contents("octocat", "Hello-World")

    assert names == ["README.md", "tests", "Dockerfile"]


@pytest.mark.asyncio
@respx.mock
async def test_get_repo_root_contents_returns_empty_for_empty_repo_404() -> None:
    """Historic GitHub 404 path — kept for defence in depth across API shifts."""
    respx.get("https://api.github.com/repos/octocat/empty/contents").mock(
        return_value=Response(404, json={"message": "This repository is empty."})
    )

    async with GitHubClient(token="ghs_test") as gh:
        names = await gh.get_repo_root_contents("octocat", "empty")

    assert names == []


@pytest.mark.asyncio
@respx.mock
async def test_get_repo_root_contents_returns_empty_for_empty_repo_409() -> None:
    """GitHub's actual response for empty repos on /contents — 409 'Git
    Repository is empty.'. Caught from a real-world report: analyzing
    `mohit-sharma2` failed because two of three repos had size=0.
    """
    respx.get("https://api.github.com/repos/owner/empty/contents").mock(
        return_value=Response(409, json={"message": "Git Repository is empty."})
    )

    async with GitHubClient(token="ghs_test") as gh:
        names = await gh.get_repo_root_contents("owner", "empty")

    assert names == []


@pytest.mark.asyncio
@respx.mock
async def test_list_recent_commits_sample_returns_empty_on_409_empty_repo() -> None:
    respx.get("https://api.github.com/repos/owner/empty/commits").mock(
        return_value=Response(409, json={"message": "Git Repository is empty."})
    )

    async with GitHubClient(token="ghs_test") as gh:
        msgs = await gh.list_recent_commits_sample("owner", "empty", limit=10)

    assert msgs == []


@pytest.mark.asyncio
@respx.mock
async def test_list_commits_returns_empty_on_409_empty_repo() -> None:
    """The author+since variant — exactly the call that blew up for
    mohit-sharma2's `my-project` empty repo, surfaced via a v0.8.2 prod
    Sentry capture before this fix landed.
    """
    respx.get("https://api.github.com/repos/owner/empty/commits").mock(
        return_value=Response(409, json={"message": "Git Repository is empty."})
    )

    async with GitHubClient(token="ghs_test") as gh:
        commits = await gh.list_commits("owner", "empty", author="someone", since="2024-01-01")

    assert commits == []


@pytest.mark.asyncio
@respx.mock
async def test_client_retries_on_secondary_rate_limit() -> None:
    respx.get("https://api.github.com/users/octocat").mock(
        side_effect=[
            Response(403, json={"message": "secondary rate limit"}, headers={"Retry-After": "0"}),
            Response(200, json={"login": "octocat", "public_repos": 0}),
        ]
    )

    async with GitHubClient(token="ghs_test") as gh:
        user = await gh.get_user("octocat")

    assert user["login"] == "octocat"


@pytest.mark.asyncio
@respx.mock
async def test_get_license_returns_spdx_id() -> None:
    respx.get("https://api.github.com/repos/o/r/license").mock(
        return_value=Response(200, json={"license": {"spdx_id": "MIT"}})
    )
    async with GitHubClient(token="ghs_test") as gh:
        assert await gh.get_license("o", "r") == "MIT"


@pytest.mark.asyncio
@respx.mock
async def test_get_license_returns_none_on_404() -> None:
    respx.get("https://api.github.com/repos/o/r/license").mock(
        return_value=Response(404, json={"message": "Not Found"})
    )
    async with GitHubClient(token="ghs_test") as gh:
        assert await gh.get_license("o", "r") is None


@pytest.mark.asyncio
@respx.mock
async def test_get_license_treats_noassertion_as_none() -> None:
    respx.get("https://api.github.com/repos/o/r/license").mock(
        return_value=Response(200, json={"license": {"spdx_id": "NOASSERTION"}})
    )
    async with GitHubClient(token="ghs_test") as gh:
        assert await gh.get_license("o", "r") is None


@pytest.mark.asyncio
@respx.mock
async def test_list_workflow_files_counts_entries() -> None:
    respx.get("https://api.github.com/repos/o/r/contents/.github/workflows").mock(
        return_value=Response(
            200,
            json=[
                {"name": "ci.yml", "type": "file"},
                {"name": "release.yml", "type": "file"},
                {"name": "examples", "type": "dir"},
            ],
        )
    )
    async with GitHubClient(token="ghs_test") as gh:
        files = await gh.list_workflow_files("o", "r")
    assert files == ["ci.yml", "release.yml"]


@pytest.mark.asyncio
@respx.mock
async def test_list_workflow_files_returns_empty_on_404() -> None:
    respx.get("https://api.github.com/repos/o/r/contents/.github/workflows").mock(
        return_value=Response(404, json={"message": "Not Found"})
    )
    async with GitHubClient(token="ghs_test") as gh:
        assert await gh.list_workflow_files("o", "r") == []


@pytest.mark.asyncio
@respx.mock
async def test_get_repo_readme_text_returns_decoded() -> None:
    import base64

    content = "# Hello\nSecond line."
    respx.get("https://api.github.com/repos/o/r/readme").mock(
        return_value=Response(
            200,
            json={"content": base64.b64encode(content.encode()).decode(), "encoding": "base64"},
        )
    )
    async with GitHubClient(token="ghs_test") as gh:
        assert await gh.get_repo_readme_text("o", "r") == content


@pytest.mark.asyncio
@respx.mock
async def test_get_repo_readme_text_returns_empty_on_404() -> None:
    respx.get("https://api.github.com/repos/o/r/readme").mock(
        return_value=Response(404, json={"message": "Not Found"})
    )
    async with GitHubClient(token="ghs_test") as gh:
        assert await gh.get_repo_readme_text("o", "r") == ""


@pytest.mark.asyncio
@respx.mock
async def test_list_recent_commits_sample_returns_message_list() -> None:
    respx.get(url__startswith="https://api.github.com/repos/o/r/commits").mock(
        return_value=Response(
            200,
            json=[
                {"commit": {"message": "feat: add thing\n\nlong body"}},
                {"commit": {"message": "wip"}},
            ],
        )
    )
    async with GitHubClient(token="ghs_test") as gh:
        msgs = await gh.list_recent_commits_sample("o", "r", limit=10)
    assert msgs == ["feat: add thing\n\nlong body", "wip"]


@pytest.mark.asyncio
@respx.mock
async def test_get_review_depth_averages_body_length() -> None:
    respx.post("https://api.github.com/graphql").mock(
        return_value=Response(
            200,
            json={
                "data": {
                    "user": {
                        "contributionsCollection": {
                            "pullRequestReviewContributions": {
                                "nodes": [
                                    {"pullRequestReview": {"bodyText": "a" * 100}},
                                    {"pullRequestReview": {"bodyText": "b" * 200}},
                                ]
                            }
                        }
                    }
                }
            },
        )
    )
    async with GitHubClient(token="ghs_test") as gh:
        avg = await gh.get_review_depth("alice")
    assert avg == 150


@pytest.mark.asyncio
@respx.mock
async def test_get_review_depth_returns_none_for_no_reviews() -> None:
    respx.post("https://api.github.com/graphql").mock(
        return_value=Response(
            200,
            json={
                "data": {
                    "user": {
                        "contributionsCollection": {"pullRequestReviewContributions": {"nodes": []}}
                    }
                }
            },
        )
    )
    async with GitHubClient(token="ghs_test") as gh:
        assert await gh.get_review_depth("alice") is None


@pytest.mark.asyncio
@respx.mock
async def test_get_contribution_repos_filters_low_volume() -> None:
    respx.post("https://api.github.com/graphql").mock(
        return_value=Response(
            200,
            json={
                "data": {
                    "user": {
                        "contributionsCollection": {
                            "commitContributionsByRepository": [
                                {
                                    "repository": {"nameWithOwner": "alice/big"},
                                    "contributions": {"totalCount": 50},
                                },
                                {
                                    "repository": {"nameWithOwner": "alice/medium"},
                                    "contributions": {"totalCount": 15},
                                },
                                {
                                    "repository": {"nameWithOwner": "alice/small"},
                                    "contributions": {"totalCount": 3},
                                },
                            ]
                        }
                    }
                }
            },
        )
    )
    async with GitHubClient(token="ghs_test") as gh:
        count = await gh.get_contribution_repo_count("alice", min_commits=10)
    assert count == 2


@pytest.mark.asyncio
@respx.mock
async def test_graphql_returns_partial_data_when_errors_present() -> None:
    """GitHub returns partial `data` alongside `errors` when one expensive field
    trips RESOURCE_LIMITS_EXCEEDED (e.g. hyper-active accounts). We must surface
    the partial data rather than raising, so downstream defensive reads survive."""
    respx.post("https://api.github.com/graphql").mock(
        return_value=Response(
            200,
            json={
                "data": {
                    "user": {"pullRequests": {"totalCount": 42}, "contributionsCollection": None}
                },
                "errors": [
                    {
                        "type": "RESOURCE_LIMITS_EXCEEDED",
                        "path": [
                            "user",
                            "contributionsCollection",
                            "pullRequestReviewContributions",
                        ],
                        "message": "Resource limits for this query exceeded.",
                    }
                ],
            },
        )
    )
    async with GitHubClient(token="ghs_test") as gh:
        data = await gh.graphql("query {}", {"login": "antfu"})
    assert data["user"]["pullRequests"]["totalCount"] == 42
    assert data["user"]["contributionsCollection"] is None


@pytest.mark.asyncio
@respx.mock
async def test_graphql_raises_only_when_no_data_returned() -> None:
    """When GitHub returns errors with no usable `data`, the call is genuinely
    fatal and must raise so the caller can decide how to degrade."""
    respx.post("https://api.github.com/graphql").mock(
        return_value=Response(
            200,
            json={"data": None, "errors": [{"message": "Something is broken."}]},
        )
    )
    async with GitHubClient(token="ghs_test") as gh:
        with pytest.raises(RuntimeError, match="GraphQL error"):
            await gh.graphql("query {}", {"login": "ghost"})


# Regression for SKILL-ISSUE-BACKEND-4 (scoring-engine leg): the review-depth and
# contribution-count queries hit the same `contributionsCollection` field that GitHub
# rejects for hyper-active accounts. They must degrade, not 500 the whole analysis.

_REVIEW_RESOURCE_LIMIT = {
    "data": {
        "user": {"contributionsCollection": {"pullRequestReviewContributions": {"nodes": None}}}
    },
    "errors": [
        {
            "type": "RESOURCE_LIMITS_EXCEEDED",
            "path": ["user", "contributionsCollection", "pullRequestReviewContributions", "nodes"],
            "message": "Resource limits for this query exceeded.",
        }
    ],
}


@pytest.mark.asyncio
@respx.mock
async def test_get_review_depth_returns_none_on_partial_null_nodes() -> None:
    """Partial data with null `nodes` (the exact prod shape) must return None, not
    crash iterating None."""
    respx.post("https://api.github.com/graphql").mock(
        return_value=Response(200, json=_REVIEW_RESOURCE_LIMIT)
    )
    async with GitHubClient(token="ghs_test") as gh:
        assert await gh.get_review_depth("antfu") is None


@pytest.mark.asyncio
@respx.mock
async def test_get_review_depth_returns_none_on_fatal_error() -> None:
    """A fully fatal GraphQL rejection (no data) degrades to None."""
    respx.post("https://api.github.com/graphql").mock(
        return_value=Response(200, json={"data": None, "errors": [{"message": "nope"}]})
    )
    async with GitHubClient(token="ghs_test") as gh:
        assert await gh.get_review_depth("antfu") is None


@pytest.mark.asyncio
@respx.mock
async def test_get_contribution_repo_count_returns_zero_on_partial_null() -> None:
    """Partial data with a null contributions collection must return 0."""
    respx.post("https://api.github.com/graphql").mock(
        return_value=Response(
            200,
            json={
                "data": {"user": {"contributionsCollection": None}},
                "errors": [{"type": "RESOURCE_LIMITS_EXCEEDED", "message": "exceeded"}],
            },
        )
    )
    async with GitHubClient(token="ghs_test") as gh:
        assert await gh.get_contribution_repo_count("antfu", min_commits=10) == 0


@pytest.mark.asyncio
@respx.mock
async def test_get_contribution_repo_count_returns_zero_on_fatal_error() -> None:
    """A fully fatal GraphQL rejection (no data) degrades to 0."""
    respx.post("https://api.github.com/graphql").mock(
        return_value=Response(200, json={"data": None, "errors": [{"message": "nope"}]})
    )
    async with GitHubClient(token="ghs_test") as gh:
        assert await gh.get_contribution_repo_count("antfu", min_commits=10) == 0


@pytest.mark.asyncio
@respx.mock
async def test_call_cap_raises_after_max_live_calls() -> None:
    from app.github.client import GitHubCallCapExceeded

    respx.get(url__regex=r"https://api\.github\.com/users/.+").mock(
        return_value=Response(200, json={"login": "x"})
    )
    async with GitHubClient(token="t", max_calls=2) as gh:
        await gh.get_user("a")  # 1
        await gh.get_user("b")  # 2
        with pytest.raises(GitHubCallCapExceeded):
            await gh.get_user("c")  # 3 > cap


def test_retry_after_seconds_caps_and_parses() -> None:
    from httpx import Request, Response

    from app.github.client import _retry_after_seconds

    def _resp(v: str) -> Response:
        return Response(429, headers={"Retry-After": v}, request=Request("GET", "http://x"))

    assert _retry_after_seconds(_resp("3"), ceiling=10.0) == 3.0
    assert _retry_after_seconds(_resp("999"), ceiling=10.0) == 10.0  # capped
    # HTTP-date / garbage must not crash and stays bounded by the ceiling.
    assert _retry_after_seconds(_resp("Wed, 21 Oct 2099 07:28:00 GMT"), ceiling=10.0) == 10.0
    assert _retry_after_seconds(_resp("not-a-number"), ceiling=10.0) <= 10.0
