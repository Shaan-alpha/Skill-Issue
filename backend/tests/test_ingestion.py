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


def _mock_graphql(
    *,
    pinned_nodes: list[dict[str, object]] | None = None,
    external_prs: int = 0,
    external_reviews: int = 0,
) -> None:
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
                            "contributionsCollection": {
                                "pullRequestReviewContributions": {"totalCount": external_reviews}
                            },
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
    _mock_graphql(external_prs=12, external_reviews=4)

    async with GitHubClient(token="ghs_test") as gh:
        profile = await ingest_profile("octocat", gh)

    assert profile.languages == {"Python": 1000, "TypeScript": 200, "Rust": 300}
    assert profile.profile_readme_chars == len(readme)
    assert profile.external_prs_merged == 12
    assert profile.external_reviews == 4
    assert profile.has_sponsors_listing is True
    assert profile.is_developer_program_member is True
