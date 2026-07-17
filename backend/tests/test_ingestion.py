import asyncio
import base64
import copy
import json
from pathlib import Path

import pytest
import respx
from httpx import Response

from app.github.client import GitHubClient
from app.ingestion.profile import ingest_profile

FIXTURES = Path(__file__).parent / "fixtures" / "github_responses"


def _load_fixture(name: str) -> object:
    return json.loads((FIXTURES / name).read_text())


def _mock_user(payload: dict[str, object] | None = None) -> None:
    user_payload = payload or _load_fixture("user_octocat.json")
    respx.get("https://api.github.com/users/octocat").mock(
        return_value=Response(200, json=user_payload)
    )


def _mock_repos(payload: list[dict[str, object]] | None = None) -> list[dict[str, object]]:
    repos_payload = payload or _load_fixture("repos_octocat.json")
    respx.get("https://api.github.com/users/octocat/repos").mock(
        return_value=Response(200, json=repos_payload)
    )
    return repos_payload


def _mock_profile_readme(readme: str | None = "") -> None:
    if readme is None:
        respx.get("https://api.github.com/repos/octocat/octocat/readme").mock(
            return_value=Response(404, json={"message": "Not Found"})
        )
        return

    encoded = base64.b64encode(readme.encode("utf-8")).decode("ascii")
    respx.get("https://api.github.com/repos/octocat/octocat/readme").mock(
        return_value=Response(200, json={"content": encoded, "encoding": "base64"})
    )


def _mock_languages(
    repos_payload: list[dict[str, object]], languages: dict[str, dict[str, int]] | None = None
) -> None:
    languages = languages or {}
    for raw in repos_payload:
        if raw.get("fork"):
            continue
        owner, repo = str(raw["full_name"]).split("/", 1)
        respx.get(f"https://api.github.com/repos/{owner}/{repo}/languages").mock(
            return_value=Response(200, json=languages.get(str(raw["name"]), {}))
        )


def _mock_commits(repos_payload: list[dict[str, object]]) -> None:
    for raw in repos_payload:
        if raw.get("fork"):
            continue
        owner, repo = str(raw["full_name"]).split("/", 1)
        # Use a regex match or generic match for the commits URL because it has params
        respx.get(url__startswith=f"https://api.github.com/repos/{owner}/{repo}/commits").mock(
            return_value=Response(200, json=[])
        )


def _mock_contents(
    repos_payload: list[dict[str, object]],
    contents_by_repo: dict[str, list[dict[str, object]]] | None = None,
) -> None:
    """Mock `/repos/{owner}/{repo}/contents`. Default: empty repo (404)."""
    contents_by_repo = contents_by_repo or {}
    for raw in repos_payload:
        if raw.get("fork"):
            continue
        owner, repo = str(raw["full_name"]).split("/", 1)
        entries = contents_by_repo.get(str(raw["name"]))
        if entries is None:
            respx.get(f"https://api.github.com/repos/{owner}/{repo}/contents").mock(
                return_value=Response(404, json={"message": "This repository is empty."})
            )
        else:
            respx.get(f"https://api.github.com/repos/{owner}/{repo}/contents").mock(
                return_value=Response(200, json=entries)
            )


def _mock_graphql(
    *,
    pinned_nodes: list[dict[str, object]] | None = None,
    external_prs: int = 0,
    external_reviews: int = 0,
) -> None:
    # ingest_profile issues three GraphQL POSTs in order: PINNED_REPOS, EXTERNAL_PRS,
    # then EXTERNAL_REVIEW_COUNT (the review count is a separate isolated query).
    respx.post("https://api.github.com/graphql").mock(
        side_effect=[
            Response(
                200,
                json={
                    "data": {
                        "user": {
                            "pinnedItems": {
                                "nodes": pinned_nodes or [],
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
                            "hasSponsorsListing": True,
                            "isGitHubStar": False,
                            "isDeveloperProgramMember": True,
                            "pullRequests": {"totalCount": external_prs, "nodes": []},
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
                                "pullRequestReviewContributions": {"totalCount": external_reviews}
                            }
                        }
                    }
                },
            ),
        ]
    )


def _fake_repo(name: str, *, language: str | None = None) -> dict[str, object]:
    raw = copy.deepcopy(_load_fixture("repos_octocat.json")[1])
    raw["name"] = name
    raw["full_name"] = f"octocat/{name}"
    raw["language"] = language
    raw["fork"] = False
    return raw


@pytest.mark.asyncio
@respx.mock
async def test_ingest_profile_maps_to_domain() -> None:
    _mock_user()
    repos_payload = _mock_repos()
    _mock_languages(repos_payload)
    _mock_commits(repos_payload)
    _mock_contents(repos_payload)
    _mock_profile_readme()
    _mock_graphql()

    async with GitHubClient(token="ghs_test") as gh:
        profile = await ingest_profile("octocat", gh)

    assert profile.username == "octocat"
    assert profile.public_repos >= 0
    assert isinstance(profile.repos, list)


@pytest.mark.asyncio
@respx.mock
async def test_pinned_repos_get_tagged() -> None:
    _mock_user()
    repos_payload = _mock_repos()
    _mock_languages(repos_payload)
    _mock_commits(repos_payload)
    _mock_contents(repos_payload)
    _mock_profile_readme()
    # Pin the first non-fork repo from the fixture
    first_non_fork_name = next(r["name"] for r in repos_payload if not r.get("fork", False))
    _mock_graphql(pinned_nodes=[{"name": first_non_fork_name}])

    async with GitHubClient(token="ghs_test") as gh:
        profile = await ingest_profile("octocat", gh)

    pinned = [r for r in profile.repos if "pinned" in r.deployment_hints]
    assert len(pinned) == 1
    assert pinned[0].name == first_non_fork_name


@pytest.mark.asyncio
@respx.mock
async def test_ingest_profile_populates_languages_readme_and_external_counts() -> None:
    repos_payload = [
        _fake_repo("alpha-api", language="Python"),
        _fake_repo("beta-web", language="TypeScript"),
    ]
    readme = "# Octocat\n\nBuilder of sturdy example repositories.\n"

    _mock_user()
    _mock_repos(repos_payload)
    _mock_languages(
        repos_payload,
        {
            "alpha-api": {"Python": 800, "TypeScript": 200},
            "beta-web": {"Python": 200, "Rust": 300},
        },
    )
    _mock_profile_readme(readme)
    _mock_commits(repos_payload)
    _mock_contents(repos_payload)
    _mock_graphql(external_prs=12, external_reviews=4)

    async with GitHubClient(token="ghs_test") as gh:
        profile = await ingest_profile("octocat", gh)

    assert profile.languages == {"Python": 1000, "TypeScript": 200, "Rust": 300}
    assert profile.profile_readme_chars == len(readme)
    assert profile.external_prs_merged == 12
    assert profile.external_reviews == 4
    assert profile.has_sponsors_listing is True
    assert profile.is_developer_program_member is True


_RESOURCE_LIMIT_ERROR = {
    "data": None,
    "errors": [
        {
            "type": "RESOURCE_LIMITS_EXCEEDED",
            "path": ["user", "contributionsCollection", "pullRequestReviewContributions"],
            "message": "Resource limits for this query exceeded.",
        }
    ],
}


@pytest.mark.asyncio
@respx.mock
async def test_ingest_profile_keeps_pr_count_when_review_query_hits_resource_limit() -> None:
    """Regression for SKILL-ISSUE-BACKEND-4: GitHub rejects the isolated review-count
    query with RESOURCE_LIMITS_EXCEEDED for hyper-active accounts (e.g. antfu). Because
    the review count lives in its own query (Fix C), the merged-PR count and account
    badges survive — only the review count degrades to 0, and no 500 reaches the user."""
    repos_payload = [_fake_repo("alpha-api", language="Python")]
    _mock_user()
    _mock_repos(repos_payload)
    _mock_languages(repos_payload)
    _mock_commits(repos_payload)
    _mock_contents(repos_payload)
    _mock_profile_readme()
    # POSTs in order: PINNED_REPOS (ok), EXTERNAL_PRS (ok, 137 merged PRs),
    # EXTERNAL_REVIEW_COUNT (rejected with RESOURCE_LIMITS_EXCEEDED).
    respx.post("https://api.github.com/graphql").mock(
        side_effect=[
            Response(200, json={"data": {"user": {"pinnedItems": {"nodes": []}}}}),
            Response(
                200,
                json={
                    "data": {
                        "user": {
                            "hasSponsorsListing": True,
                            "isGitHubStar": True,
                            "isDeveloperProgramMember": False,
                            "pullRequests": {"totalCount": 137, "nodes": []},
                        }
                    }
                },
            ),
            Response(200, json=_RESOURCE_LIMIT_ERROR),
        ]
    )

    async with GitHubClient(token="ghs_test") as gh:
        profile = await ingest_profile("octocat", gh)

    assert profile.username == "octocat"
    # Merged-PR count and badges survived the review-count rejection…
    assert profile.external_prs_merged == 137
    assert profile.has_sponsors_listing is True
    assert profile.is_github_star is True
    # …and only the review count degraded to 0 rather than 500-ing the request.
    assert profile.external_reviews == 0


@pytest.mark.asyncio
@respx.mock
async def test_ingest_profile_keeps_review_count_when_pr_query_fails() -> None:
    """The split degrades both directions independently: if the EXTERNAL_PRS half
    fails entirely, the review count (its own query) still comes through."""
    repos_payload = [_fake_repo("alpha-api", language="Python")]
    _mock_user()
    _mock_repos(repos_payload)
    _mock_languages(repos_payload)
    _mock_commits(repos_payload)
    _mock_contents(repos_payload)
    _mock_profile_readme()
    respx.post("https://api.github.com/graphql").mock(
        side_effect=[
            Response(200, json={"data": {"user": {"pinnedItems": {"nodes": []}}}}),
            Response(200, json=_RESOURCE_LIMIT_ERROR),
            Response(
                200,
                json={
                    "data": {
                        "user": {
                            "contributionsCollection": {
                                "pullRequestReviewContributions": {"totalCount": 9}
                            }
                        }
                    }
                },
            ),
        ]
    )

    async with GitHubClient(token="ghs_test") as gh:
        profile = await ingest_profile("octocat", gh)

    assert profile.username == "octocat"
    # EXTERNAL_PRS half degraded to defaults…
    assert profile.external_prs_merged == 0
    assert profile.external_orgs == set()
    assert profile.has_sponsors_listing is False
    # …but the independent review-count query still delivered.
    assert profile.external_reviews == 9


@pytest.mark.asyncio
@respx.mock
async def test_ingest_profile_detects_readme_tests_ci_and_deployment_hints() -> None:
    """The previously-dormant signals must be populated from per-repo root contents.

    Regression guard for the bug where `_repo_from_rest` hardcoded these flags to
    `False`, silently making ~28 of 100 scoring points unreachable in production.
    """
    repos_payload = [
        _fake_repo("polished", language="TypeScript"),
        _fake_repo("bare", language="Go"),
    ]
    _mock_user()
    _mock_repos(repos_payload)
    _mock_languages(repos_payload)
    _mock_commits(repos_payload)
    _mock_profile_readme()
    _mock_graphql()
    _mock_contents(
        repos_payload,
        {
            "polished": [
                {"name": "README.md", "type": "file"},
                {"name": "tests", "type": "dir"},
                {"name": ".github", "type": "dir"},
                {"name": "Dockerfile", "type": "file"},
                {"name": "vercel.json", "type": "file"},
            ],
            # "bare" gets the default 404 -> empty contents, so it stays all-False.
        },
    )

    async with GitHubClient(token="ghs_test") as gh:
        profile = await ingest_profile("octocat", gh)

    by_name = {r.name: r for r in profile.repos}
    polished = by_name["polished"]
    assert polished.has_readme is True
    assert polished.has_tests is True
    assert polished.has_ci is True
    assert "dockerfile" in polished.deployment_hints
    assert "vercel" in polished.deployment_hints

    bare = by_name["bare"]
    assert bare.has_readme is False
    assert bare.has_tests is False
    assert bare.has_ci is False
    # Deployment hints stay empty (or only "pinned" if pinned, which it isn't here)
    assert bare.deployment_hints == []


@pytest.mark.asyncio
@respx.mock
async def test_ingest_profile_rejects_organizations() -> None:
    """
    GitHub orgs respond to /users/{login} with the same shape as users but
    `type: "Organization"`. The scoring engine assumes individual-developer
    semantics (pinned repos, contribution graph, PRs opened by user) and the
    GraphQL `user(login:)` query returns null for orgs, which previously
    null-deref'd in profile.py and surfaced as a generic 500 to the user.
    Now we detect early and raise NotAnIndividualError so the API layer
    can map it to a clean 422 with a helpful message.
    """
    from app.ingestion.profile import NotAnIndividualError

    respx.get("https://api.github.com/users/apache").mock(
        return_value=Response(
            200,
            json={
                "login": "apache",
                "id": 47359,
                "node_id": "MDEyOk9yZ2FuaXphdGlvbjQ3MzU5",
                "type": "Organization",
                "avatar_url": "https://avatars.githubusercontent.com/u/47359",
                "html_url": "https://github.com/apache",
            },
        )
    )

    async with GitHubClient(token="ghs_test") as gh:
        with pytest.raises(NotAnIndividualError) as excinfo:
            await ingest_profile("apache", gh)

    msg = str(excinfo.value)
    assert "apache" in msg
    assert "organization" in msg.lower()
    assert "username instead" in msg.lower() or "individual" in msg.lower()


# ─── v0.9.0: bounded GH fan-out ──────────────────────────────────────


class FakeGitHubClient:
    """Minimal GitHubClient stand-in for the bounded-fanout tests.

    Instruments every GH-touching method with a current/max in-flight
    counter. A tiny `asyncio.sleep` forces real concurrency — without
    it, fast coros could resolve sequentially and the cap assertion
    would pass vacuously.
    """

    def __init__(self, *, repo_count: int) -> None:
        self.repo_count = repo_count
        self.current_in_flight = 0
        self.max_in_flight = 0
        self.total_calls = 0

    async def _enter(self) -> None:
        self.total_calls += 1
        self.current_in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.current_in_flight)
        # Force genuine concurrency by yielding to the event loop.
        await asyncio.sleep(0.005)

    def _exit(self) -> None:
        self.current_in_flight -= 1

    async def get_user(self, login: str) -> dict[str, object]:
        await self._enter()
        try:
            return {
                "login": login,
                "type": "User",
                "bio": None,
                "followers": 0,
                "public_repos": self.repo_count,
                "created_at": "2020-01-01T00:00:00Z",
                "company": None,
                "blog": None,
                "hireable": False,
            }
        finally:
            self._exit()

    async def list_repos(self, login: str) -> list[dict[str, object]]:
        await self._enter()
        try:
            return [
                {
                    "name": f"repo-{i}",
                    "full_name": f"{login}/repo-{i}",
                    "language": "Python",
                    "stargazers_count": 0,
                    "forks_count": 0,
                    "fork": False,
                    "size": 100,
                    "pushed_at": "2026-01-01T00:00:00Z",
                    "created_at": "2024-01-01T00:00:00Z",
                    "owner": {"login": login},
                }
                for i in range(self.repo_count)
            ]
        finally:
            self._exit()

    async def graphql(self, query: str, variables: dict[str, object]) -> dict[str, object]:
        await self._enter()
        try:
            return {
                "user": {
                    "pinnedItems": {"nodes": []},
                    "hasSponsorsListing": False,
                    "isGitHubStar": False,
                    "isDeveloperProgramMember": False,
                    "pullRequests": {"totalCount": 0, "nodes": []},
                    "contributionsCollection": {
                        "pullRequestReviewContributions": {"totalCount": 0}
                    },
                }
            }
        finally:
            self._exit()

    async def get_profile_readme(self, login: str) -> str | None:
        await self._enter()
        try:
            return None
        finally:
            self._exit()

    async def get_repo_root_contents(self, owner: str, name: str) -> list[str]:
        await self._enter()
        try:
            return []
        finally:
            self._exit()

    async def list_languages(self, owner: str, name: str) -> dict[str, int]:
        await self._enter()
        try:
            return {}
        finally:
            self._exit()

    async def list_commits(
        self, owner: str, name: str, author: str, since: str
    ) -> list[dict[str, object]]:
        await self._enter()
        try:
            return []
        finally:
            self._exit()


@pytest.mark.asyncio
async def test_bounded_fanout_default_cap() -> None:
    """At default cap 8, a 50-repo profile must never burst >8 in-flight."""
    fake = FakeGitHubClient(repo_count=50)
    await ingest_profile("octocat", fake)
    assert fake.max_in_flight <= 8, f"expected ≤8 in-flight, observed {fake.max_in_flight}"
    # Sanity: the test actually drove enough load to be meaningful.
    assert fake.total_calls >= 50


@pytest.mark.asyncio
async def test_bounded_fanout_overridable_via_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Overriding settings.gh_ingest_concurrency=2 must cap in-flight at 2."""
    from app import settings as settings_module
    from app.settings import Settings

    monkeypatch.setattr(settings_module, "settings", Settings(gh_ingest_concurrency=2))
    fake = FakeGitHubClient(repo_count=50)
    await ingest_profile("octocat", fake)
    assert fake.max_in_flight <= 2, (
        f"expected ≤2 in-flight at override, observed {fake.max_in_flight}"
    )
