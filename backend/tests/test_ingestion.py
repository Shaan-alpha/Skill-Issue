import json
from pathlib import Path

import pytest
import respx
from httpx import Response

from app.github.client import GitHubClient
from app.ingestion.profile import ingest_profile

FIXTURES = Path(__file__).parent / "fixtures" / "github_responses"


@pytest.mark.asyncio
@respx.mock
async def test_ingest_profile_maps_to_domain() -> None:
    respx.get("https://api.github.com/users/octocat").mock(
        return_value=Response(200, json=json.loads((FIXTURES / "user_octocat.json").read_text()))
    )
    respx.get("https://api.github.com/users/octocat/repos").mock(
        return_value=Response(200, json=json.loads((FIXTURES / "repos_octocat.json").read_text()))
    )
    respx.post("https://api.github.com/graphql").mock(
        return_value=Response(
            200,
            json={"data": {"user": {"pinnedItems": {"nodes": []}}}},
        )
    )

    async with GitHubClient(token="ghs_test") as gh:
        profile = await ingest_profile("octocat", gh)

    assert profile.username == "octocat"
    assert profile.public_repos >= 0
    assert isinstance(profile.repos, list)


@pytest.mark.asyncio
@respx.mock
async def test_pinned_repos_get_tagged() -> None:
    respx.get("https://api.github.com/users/octocat").mock(
        return_value=Response(200, json=json.loads((FIXTURES / "user_octocat.json").read_text()))
    )
    respx.get("https://api.github.com/users/octocat/repos").mock(
        return_value=Response(200, json=json.loads((FIXTURES / "repos_octocat.json").read_text()))
    )
    repos_payload = json.loads((FIXTURES / "repos_octocat.json").read_text())
    # Pin the first non-fork repo from the fixture
    first_non_fork_name = next(r["name"] for r in repos_payload if not r.get("fork", False))
    respx.post("https://api.github.com/graphql").mock(
        return_value=Response(
            200,
            json={
                "data": {
                    "user": {
                        "pinnedItems": {
                            "nodes": [{"name": first_non_fork_name}]
                        }
                    }
                }
            },
        )
    )

    async with GitHubClient(token="ghs_test") as gh:
        profile = await ingest_profile("octocat", gh)

    pinned = [r for r in profile.repos if "pinned" in r.deployment_hints]
    assert len(pinned) == 1
    assert pinned[0].name == first_non_fork_name
