from __future__ import annotations

import asyncio
import base64
from typing import Any, Self

import httpx

API_BASE = "https://api.github.com"
GRAPHQL_URL = "https://api.github.com/graphql"


class GitHubClient:
    def __init__(self, token: str | None = None, *, max_retries: int = 3) -> None:
        headers: dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "skill-issue/0.1.0",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.AsyncClient(headers=headers, timeout=20.0, http2=True)
        self._max_retries = max_retries

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self._client.aclose()

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        for _attempt in range(self._max_retries):
            resp = await self._client.request(method, url, **kwargs)
            if resp.status_code == 403 and "rate limit" in resp.text.lower():
                retry_after = float(resp.headers.get("Retry-After", "1"))
                await asyncio.sleep(retry_after)
                continue
            return resp
        resp.raise_for_status()
        return resp

    async def get_user(self, username: str) -> dict[str, Any]:
        resp = await self._request("GET", f"{API_BASE}/users/{username}")
        resp.raise_for_status()
        return resp.json()

    async def list_repos(self, username: str, *, per_page: int = 100) -> list[dict[str, Any]]:
        resp = await self._request(
            "GET",
            f"{API_BASE}/users/{username}/repos",
            params={"per_page": per_page, "sort": "updated"},
        )
        resp.raise_for_status()
        return resp.json()

    async def list_languages(self, owner: str, repo: str) -> dict[str, int]:
        resp = await self._request("GET", f"{API_BASE}/repos/{owner}/{repo}/languages")
        resp.raise_for_status()
        return resp.json()

    async def list_commits(
        self, owner: str, repo: str, author: str, since: str, per_page: int = 100
    ) -> list[dict[str, Any]]:
        resp = await self._request(
            "GET",
            f"{API_BASE}/repos/{owner}/{repo}/commits",
            params={"author": author, "since": since, "per_page": per_page},
        )
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        return resp.json()

    async def get_repo_root_contents(self, owner: str, repo: str) -> list[str]:
        """Return root-level file and directory names for a repo.

        Empty repos return 404 ("This repository is empty.") — surface those as [].
        If GitHub returns a single file object instead of a list (which happens when
        the path resolves to a file), treat it as no usable directory listing.
        """
        resp = await self._request("GET", f"{API_BASE}/repos/{owner}/{repo}/contents")
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            return []
        return [str(entry.get("name", "")) for entry in data]

    async def get_license(self, owner: str, repo: str) -> str | None:
        """Return the repo's SPDX licence id, or None if absent / NOASSERTION."""
        resp = await self._request("GET", f"{API_BASE}/repos/{owner}/{repo}/license")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        spdx = (resp.json().get("license") or {}).get("spdx_id")
        if not spdx or spdx == "NOASSERTION":
            return None
        return str(spdx)

    async def list_workflow_files(self, owner: str, repo: str) -> list[str]:
        """Return the names of files (not directories) under .github/workflows.

        Returns [] when the directory doesn't exist."""
        resp = await self._request(
            "GET", f"{API_BASE}/repos/{owner}/{repo}/contents/.github/workflows"
        )
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            return []
        return [str(e["name"]) for e in data if e.get("type") == "file"]

    async def get_repo_readme_text(self, owner: str, repo: str) -> str:
        """Return decoded README text for any repo, or "" when missing."""
        resp = await self._request("GET", f"{API_BASE}/repos/{owner}/{repo}/readme")
        if resp.status_code == 404:
            return ""
        resp.raise_for_status()
        content = resp.json().get("content", "")
        return base64.b64decode(content).decode("utf-8", errors="ignore")

    async def list_recent_commits_sample(
        self, owner: str, repo: str, *, limit: int = 100
    ) -> list[str]:
        """Return the most-recent commit messages on the default branch (up to limit)."""
        resp = await self._request(
            "GET",
            f"{API_BASE}/repos/{owner}/{repo}/commits",
            params={"per_page": limit},
        )
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        return [str(c.get("commit", {}).get("message", "")) for c in resp.json()]

    async def get_profile_readme(self, username: str) -> str | None:
        resp = await self._request("GET", f"{API_BASE}/repos/{username}/{username}/readme")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()

        content = resp.json().get("content", "")
        return base64.b64decode(content).decode("utf-8", errors="ignore")

    async def graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        resp = await self._request(
            "POST", GRAPHQL_URL, json={"query": query, "variables": variables}
        )
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            raise RuntimeError(f"GraphQL error: {data['errors']}")
        return data["data"]
