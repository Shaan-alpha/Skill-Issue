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
async def test_get_repo_root_contents_returns_empty_for_empty_repo() -> None:
    respx.get("https://api.github.com/repos/octocat/empty/contents").mock(
        return_value=Response(404, json={"message": "This repository is empty."})
    )

    async with GitHubClient(token="ghs_test") as gh:
        names = await gh.get_repo_root_contents("octocat", "empty")

    assert names == []


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
