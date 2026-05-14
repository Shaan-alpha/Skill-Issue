from __future__ import annotations

import asyncio
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

    async def graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        resp = await self._request(
            "POST", GRAPHQL_URL, json={"query": query, "variables": variables}
        )
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            raise RuntimeError(f"GraphQL error: {data['errors']}")
        return data["data"]
