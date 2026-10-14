import asyncio
import json
from pathlib import Path

import httpx
import pytest
import respx
from httpx import Response

from app.github.client import GitHubClient, GitHubRateLimited, RootEntry

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
async def test_get_repo_root_contents_returns_names_types_and_sizes() -> None:
    """Sizes come free with the listing: they measure README depth without
    downloading each README."""
    respx.get("https://api.github.com/repos/octocat/Hello-World/contents").mock(
        return_value=Response(
            200,
            json=[
                {"name": "README.md", "type": "file", "size": 4096},
                {"name": "tests", "type": "dir", "size": 0},
                {"name": "Dockerfile", "type": "file", "size": 120},
            ],
        )
    )

    async with GitHubClient(token="ghs_test") as gh:
        entries = await gh.get_repo_root_contents("octocat", "Hello-World")

    assert entries == [
        RootEntry("README.md", "file", 4096),
        RootEntry("tests", "dir", 0),
        RootEntry("Dockerfile", "file", 120),
    ]


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
async def test_transient_server_error_is_retried_once() -> None:
    route = respx.get("https://api.github.com/users/octocat").mock(
        side_effect=[Response(502), Response(200, json={"login": "octocat"})]
    )

    async with GitHubClient(token="ghs_test") as gh:
        user = await gh.get_user("octocat")

    assert user["login"] == "octocat"
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_persistent_server_error_fails_after_one_retry() -> None:
    route = respx.get("https://api.github.com/users/octocat").mock(return_value=Response(503))

    async with GitHubClient(token="ghs_test") as gh:
        with pytest.raises(httpx.HTTPStatusError):
            await gh.get_user("octocat")

    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_dropped_connection_is_retried_once() -> None:
    route = respx.get("https://api.github.com/users/octocat").mock(
        side_effect=[httpx.RemoteProtocolError("stream reset"), Response(200, json={"login": "x"})]
    )

    async with GitHubClient(token="ghs_test") as gh:
        await gh.get_user("octocat")

    assert route.call_count == 2


_UNAVAILABLE = [
    pytest.param(
        451, {"message": "Repository access blocked", "block": {"reason": "dmca"}}, id="dmca-451"
    ),
    pytest.param(
        403, {"message": "Repository access blocked", "block": {"reason": "tos"}}, id="tos-403"
    ),
    pytest.param(410, {"message": "Gone"}, id="gone-410"),
]


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(("status", "body"), _UNAVAILABLE)
async def test_unavailable_repository_reads_as_absent(status: int, body: dict[str, object]) -> None:
    """A repository GitHub won't serve (DMCA'd, blocked, gone) is one repo's
    problem, not the analysis's: every per-repo read treats it as absent."""
    respx.route(url__startswith="https://api.github.com/repos/owner/blocked").mock(
        return_value=Response(status, json=body)
    )

    async with GitHubClient(token="ghs_test") as gh:
        assert await gh.list_languages("owner", "blocked") == {}
        assert await gh.get_repo_root_contents("owner", "blocked") == []
        assert await gh.list_commits("owner", "blocked", "owner", "2024-01-01") == []


@pytest.mark.asyncio
@respx.mock
async def test_rate_limited_repository_read_is_not_mistaken_for_absent() -> None:
    respx.get("https://api.github.com/repos/owner/repo/languages").mock(
        return_value=Response(
            403,
            json={"message": "API rate limit exceeded for user ID 1."},
            headers={"Retry-After": "0", "X-RateLimit-Remaining": "0"},
        )
    )

    async with GitHubClient(token="ghs_test", max_retries=1) as gh:
        with pytest.raises(httpx.HTTPStatusError):
            await gh.list_languages("owner", "repo")


class _InFlight:
    """Async respx side effect that records the peak number of requests in flight."""

    def __init__(self, response: Response) -> None:
        self._response = response
        self.current = 0
        self.peak = 0

    async def __call__(self, request: httpx.Request) -> Response:
        self.current += 1
        self.peak = max(self.peak, self.current)
        try:
            await asyncio.sleep(0.01)
            return self._response
        finally:
            self.current -= 1


@pytest.mark.asyncio
@respx.mock
async def test_client_caps_live_requests_in_flight() -> None:
    tracker = _InFlight(Response(200, json={"Python": 1}))
    respx.get(url__regex=r"https://api\.github\.com/repos/o/r\d+/languages").mock(
        side_effect=tracker
    )

    async with GitHubClient(token="ghs_test", max_concurrency=3) as gh:
        await asyncio.gather(*(gh.list_languages("o", f"r{i}") for i in range(12)))

    assert tracker.peak == 3


@pytest.mark.asyncio
async def test_client_concurrency_defaults_to_the_ingest_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import settings as settings_module
    from app.settings import Settings

    monkeypatch.setattr(settings_module, "settings", Settings(gh_ingest_concurrency=2))
    tracker = _InFlight(Response(200, json={"Python": 1}))
    with respx.mock:
        respx.get(url__regex=r"https://api\.github\.com/repos/o/r\d+/languages").mock(
            side_effect=tracker
        )
        async with GitHubClient(token="ghs_test") as gh:
            await asyncio.gather(*(gh.list_languages("o", f"r{i}") for i in range(6)))

    assert tracker.peak == 2


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


# GitHub documents GraphQL rate limits as HTTP 200 with an error message (primary,
# x-ratelimit-remaining 0) or 200/403 naming a secondary rate limit. The status
# alone can't tell a caller it was refused, so the client raises one exception
# for every shape and fail-soft callers can still let it fail the analysis.
_PRIMARY_LIMIT_200 = Response(
    200,
    json={
        "data": None,
        "errors": [{"type": "RATE_LIMITED", "message": "API rate limit exceeded for user ID 1."}],
    },
    headers={"X-RateLimit-Remaining": "0"},
)
_SECONDARY_LIMIT_200 = Response(
    200,
    json={
        "errors": [
            {"message": "You have exceeded a secondary rate limit. Please wait a few minutes."}
        ]
    },
)
# A REST-style body on a 200, with no `data` or `errors` at all.
_SECONDARY_LIMIT_200_MESSAGE = Response(
    200, json={"message": "You have exceeded a secondary rate limit. Please wait a few minutes."}
)
_SECONDARY_LIMIT_403 = Response(
    403,
    json={"message": "You have exceeded a secondary rate limit. Please wait a few minutes."},
    headers={"Retry-After": "0"},
)


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(
    "response",
    [_PRIMARY_LIMIT_200, _SECONDARY_LIMIT_200, _SECONDARY_LIMIT_200_MESSAGE, _SECONDARY_LIMIT_403],
    ids=["primary-200", "secondary-200", "secondary-200-message", "secondary-403"],
)
async def test_a_graphql_rate_limit_raises_rate_limited(response: Response) -> None:
    respx.post("https://api.github.com/graphql").mock(return_value=response)

    async with GitHubClient(token="ghs_test", max_retries=1) as gh:
        with pytest.raises(GitHubRateLimited):
            await gh.graphql("query Probe { viewer { login } }", {})


@pytest.mark.asyncio
@respx.mock
async def test_a_graphql_body_without_data_is_an_error_not_an_empty_answer() -> None:
    """Returned as None, it crashed callers outside their fail-soft blocks
    and quietly emptied the workflow probe."""
    respx.post("https://api.github.com/graphql").mock(return_value=Response(200, json={}))

    async with GitHubClient(token="ghs_test") as gh:
        with pytest.raises(RuntimeError, match="GraphQL"):
            await gh.graphql("query Probe { viewer { login } }", {})


@pytest.mark.asyncio
@respx.mock
async def test_review_depth_lets_a_rate_limit_fail_the_analysis() -> None:
    """Review depth degrades when GitHub can't resolve the query, but a rate
    limit read as "no reviews" is a low score the report cache keeps for 6 h."""
    respx.post("https://api.github.com/graphql").mock(return_value=_PRIMARY_LIMIT_200)

    async with GitHubClient(token="ghs_test") as gh:
        with pytest.raises(GitHubRateLimited):
            await gh.get_review_depth("antfu")


@pytest.mark.asyncio
@respx.mock
async def test_review_depth_lets_the_call_cap_stop_the_analysis() -> None:
    """Review depth degrades when GitHub can't resolve it, but an analysis past
    its call cap must stop with a 503, not finish scored without it and keep
    that report cached for six hours."""
    from app.github.client import GitHubCallCapExceeded

    respx.post("https://api.github.com/graphql").mock(
        return_value=Response(200, json={"data": {"user": None}})
    )

    async with GitHubClient(token="ghs_test", max_calls=0) as gh:
        with pytest.raises(GitHubCallCapExceeded):
            await gh.get_review_depth("antfu")


@pytest.mark.asyncio
@respx.mock
async def test_a_403_with_retry_after_is_a_rate_limit_not_a_blocked_repo() -> None:
    """GitHub's older secondary-limit wording never says "rate limit"; the
    Retry-After header is what marks it."""
    respx.get("https://api.github.com/repos/owner/repo/languages").mock(
        return_value=Response(
            403,
            json={"message": "You have triggered an abuse detection mechanism."},
            headers={"Retry-After": "0"},
        )
    )

    async with GitHubClient(token="ghs_test", max_retries=1) as gh:
        with pytest.raises(httpx.HTTPStatusError):
            await gh.list_languages("owner", "repo")


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


@pytest.mark.asyncio
@respx.mock
async def test_shared_token_records_low_quota(fake_cache) -> None:
    from app.cache.keys import GH_SHARED_QUOTA_KEY, NAMESPACE_GH

    respx.get(url__regex=r".*/users/.+").mock(
        return_value=Response(200, json={"login": "x"}, headers={"X-RateLimit-Remaining": "300"})
    )
    async with GitHubClient(token="t", cache=fake_cache, is_shared_token=True) as gh:
        await gh.get_user("a")
    assert await fake_cache.get_json(NAMESPACE_GH, GH_SHARED_QUOTA_KEY) == {"remaining": 300}


@pytest.mark.asyncio
@respx.mock
async def test_high_quota_is_not_recorded(fake_cache) -> None:
    from app.cache.keys import GH_SHARED_QUOTA_KEY, NAMESPACE_GH

    respx.get(url__regex=r".*/users/.+").mock(
        return_value=Response(200, json={"login": "x"}, headers={"X-RateLimit-Remaining": "4999"})
    )
    async with GitHubClient(token="t", cache=fake_cache, is_shared_token=True) as gh:
        await gh.get_user("a")
    assert await fake_cache.get_json(NAMESPACE_GH, GH_SHARED_QUOTA_KEY) is None


@pytest.mark.asyncio
@respx.mock
async def test_non_shared_token_never_records(fake_cache) -> None:
    from app.cache.keys import GH_SHARED_QUOTA_KEY, NAMESPACE_GH

    respx.get(url__regex=r".*/users/.+").mock(
        return_value=Response(200, json={"login": "x"}, headers={"X-RateLimit-Remaining": "10"})
    )
    async with GitHubClient(token="t", cache=fake_cache, is_shared_token=False) as gh:
        await gh.get_user("a")
    assert await fake_cache.get_json(NAMESPACE_GH, GH_SHARED_QUOTA_KEY) is None


def test_decode_readme_caps_oversized_content() -> None:
    import base64

    from app.github.client import _README_B64_MAX, _decode_readme_content

    # Normal READMEs decode unchanged.
    normal = base64.b64encode(b"# Hello\nWorld").decode()
    assert _decode_readme_content(normal) == "# Hello\nWorld"

    # An oversized (but valid) base64 blob is bounded and never raises.
    big = base64.b64encode(b"x" * 3_000_000).decode()  # ~4MB of base64
    out = _decode_readme_content(big)
    assert isinstance(out, str)
    assert len(out) <= _README_B64_MAX
