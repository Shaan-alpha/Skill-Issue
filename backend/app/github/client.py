from __future__ import annotations

import asyncio
import base64
import logging
from typing import TYPE_CHECKING, Any, Self

import httpx

from app.cache.keys import NAMESPACE_GH, gh_request_key, ttl_for_gh_endpoint
from app.settings import VERSION, settings

if TYPE_CHECKING:
    from app.cache.client import RedisCache

logger = logging.getLogger(__name__)

API_BASE = "https://api.github.com"
GRAPHQL_URL = "https://api.github.com/graphql"

# Status codes whose response bodies are safe to cache. 5xx and 429 are
# transient and should always retry against the live API.
_CACHEABLE_STATUSES = frozenset({200, 404, 409, 422})
# 409 covers the "Git Repository is empty." case GitHub returns on
# /contents and /commits endpoints when a repo has no commits yet.


class _CachedResponse:
    """Mimics the subset of httpx.Response used downstream of `_request`."""

    def __init__(self, status_code: int, json_body: Any) -> None:
        self.status_code = status_code
        self._json = json_body
        self.text = "" if json_body is None else "[cached]"
        self.headers: dict[str, str] = {}

    def json(self) -> Any:
        return self._json

    def raise_for_status(self) -> None:
        if 400 <= self.status_code < 600:
            request = httpx.Request("GET", "cached://")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError(
                f"Cached {self.status_code}", request=request, response=response
            )


class GitHubCallCapExceeded(Exception):
    """Raised when a single analysis exceeds its per-analysis live-call cap
    (v1.0.5 SI-03). One GitHubClient is built per analysis, so its live-call
    counter bounds the fan-out of that analysis."""

    def __init__(self, count: int, cap: int) -> None:
        super().__init__(f"GitHub call cap exceeded: {count} > {cap}")
        self.count = count
        self.cap = cap


class GitHubClient:
    def __init__(
        self,
        token: str | None = None,
        *,
        max_retries: int = 3,
        max_calls: int | None = None,
        cache: RedisCache | None = None,
    ) -> None:
        headers: dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": f"skill-issue/{VERSION}",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.AsyncClient(headers=headers, timeout=20.0, http2=True)
        self._max_retries = max_retries
        self._max_calls = max_calls
        self._live_calls = 0
        self._cache = cache

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self._client.aclose()

    async def _request(
        self, method: str, url: str, **kwargs: Any
    ) -> httpx.Response | _CachedResponse:
        params = kwargs.get("params")
        body = kwargs.get("json")
        cache_key: str | None = None

        # Try the cache before hitting GitHub.
        if self._cache is not None:
            cache_key = gh_request_key(method, url, params, body)
            try:
                cached = await self._cache.get_json(NAMESPACE_GH, cache_key)
            except Exception:
                cached = None
                logger.warning("cache get raised in GitHubClient", exc_info=True)
            if cached is not None:
                return _CachedResponse(status_code=cached["status"], json_body=cached["body"])

        # v1.0.5 SI-03: count only live calls (cache hits returned above are
        # free) and hard-cap per-analysis fan-out. One GitHubClient == one
        # analysis, so this instance counter bounds the analysis.
        if self._max_calls is not None:
            self._live_calls += 1
            if self._live_calls > self._max_calls:
                raise GitHubCallCapExceeded(self._live_calls, self._max_calls)

        # Live request with existing retry/rate-limit logic.
        resp: httpx.Response | None = None
        for _attempt in range(self._max_retries):
            resp = await self._client.request(method, url, **kwargs)
            if resp.status_code == 403 and "rate limit" in resp.text.lower():
                retry_after = float(resp.headers.get("Retry-After", "1"))
                await asyncio.sleep(retry_after)
                continue
            break
        assert resp is not None  # max_retries >= 1, so the loop body ran at least once

        # Cache successful + permanently-failed responses; skip transient errors.
        if (
            self._cache is not None
            and cache_key is not None
            and resp.status_code in _CACHEABLE_STATUSES
        ):
            ttl = ttl_for_gh_endpoint(url) or settings.cache_default_ttl_seconds
            try:
                try:
                    body_json: Any = resp.json()
                except ValueError:
                    body_json = None
                await self._cache.set_json(
                    NAMESPACE_GH,
                    cache_key,
                    {"status": resp.status_code, "body": body_json},
                    ttl_seconds=ttl,
                )
            except Exception:
                logger.warning("cache set raised in GitHubClient", exc_info=True)

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
        """List commits on a repo filtered by author + since-date.

        404 = repo or branch missing. 409 = repo is empty (no commits yet).
        Both surface as []. (The 409 path bit a real user analysis in v0.8.2:
        empty repos in mohit-sharma2's account broke the ingestion fan-out.)
        """
        resp = await self._request(
            "GET",
            f"{API_BASE}/repos/{owner}/{repo}/commits",
            params={"author": author, "since": since, "per_page": per_page},
        )
        if resp.status_code in (404, 409):
            return []
        resp.raise_for_status()
        return resp.json()

    async def get_repo_root_contents(self, owner: str, repo: str) -> list[str]:
        """Return root-level file and directory names for a repo.

        Empty repos return 409 ("Git Repository is empty.") on `/contents`; older
        GitHub responses occasionally returned 404 for the same condition. Surface
        both as []. If GitHub returns a single file object instead of a list
        (which happens when the path resolves to a file), treat it as no usable
        directory listing.
        """
        resp = await self._request("GET", f"{API_BASE}/repos/{owner}/{repo}/contents")
        if resp.status_code in (404, 409):
            return []
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            return []
        return [str(entry.get("name", "")) for entry in data]

    async def get_license(self, owner: str, repo: str) -> str | None:
        """Return the repo's SPDX licence id, or None if absent / NOASSERTION.

        404 = no detected license. 409 = repo is empty (no commits / no detectable
        license). Both map to None.
        """
        resp = await self._request("GET", f"{API_BASE}/repos/{owner}/{repo}/license")
        if resp.status_code in (404, 409):
            return None
        resp.raise_for_status()
        spdx = (resp.json().get("license") or {}).get("spdx_id")
        if not spdx or spdx == "NOASSERTION":
            return None
        return str(spdx)

    async def list_workflow_files(self, owner: str, repo: str) -> list[str]:
        """Return the names of files (not directories) under .github/workflows.

        Returns [] when the directory doesn't exist (404) or when the whole repo
        is empty (409 — "Git Repository is empty.").
        """
        resp = await self._request(
            "GET", f"{API_BASE}/repos/{owner}/{repo}/contents/.github/workflows"
        )
        if resp.status_code in (404, 409):
            return []
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            return []
        return [str(e["name"]) for e in data if e.get("type") == "file"]

    async def get_repo_readme_text(self, owner: str, repo: str) -> str:
        """Return decoded README text for any repo, or "" when missing.

        404 = no README file. 409 = repo is empty (no commits yet) — also treated
        as no README.
        """
        resp = await self._request("GET", f"{API_BASE}/repos/{owner}/{repo}/readme")
        if resp.status_code in (404, 409):
            return ""
        resp.raise_for_status()
        content = resp.json().get("content", "")
        return base64.b64decode(content).decode("utf-8", errors="ignore")

    async def list_recent_commits_sample(
        self, owner: str, repo: str, *, limit: int = 100
    ) -> list[str]:
        """Return the most-recent commit messages on the default branch (up to limit).

        404 = repo or branch missing. 409 = repo is empty (no commits yet).
        Both surface as [].
        """
        resp = await self._request(
            "GET",
            f"{API_BASE}/repos/{owner}/{repo}/commits",
            params={"per_page": limit},
        )
        if resp.status_code in (404, 409):
            return []
        resp.raise_for_status()
        return [str(c.get("commit", {}).get("message", "")) for c in resp.json()]

    async def get_review_depth(self, username: str) -> int | None:
        """Return the avg bodyText length across the 25 most-recent reviews, or None.

        This is a bonus depth signal, so it degrades to None rather than failing the
        analysis. GitHub rejects this `contributionsCollection` query with
        RESOURCE_LIMITS_EXCEEDED for hyper-active accounts (SKILL-ISSUE-BACKEND-4) —
        either fully (graphql() raises) or with partial data whose `nodes` field is
        null — so every access below is null-guarded and the call is wrapped.
        """
        from app.github.queries import REVIEW_DEPTH

        try:
            data = await self.graphql(REVIEW_DEPTH, {"login": username})
        except Exception:
            logger.warning(
                "Review-depth query failed for %s; skipping signal", username, exc_info=True
            )
            return None
        user = data.get("user") or {}
        contributions = user.get("contributionsCollection") or {}
        review_contributions = contributions.get("pullRequestReviewContributions") or {}
        nodes = review_contributions.get("nodes") or []
        bodies = [str((n.get("pullRequestReview") or {}).get("bodyText") or "") for n in nodes]
        bodies = [b for b in bodies if b]
        if not bodies:
            return None
        return sum(len(b) for b in bodies) // len(bodies)

    async def get_contribution_repo_count(self, username: str, *, min_commits: int = 10) -> int:
        """Return the number of repos the user contributed >= min_commits to in the last year.

        Bonus depth signal — degrades to 0 rather than failing the analysis when
        GitHub can't resolve this `contributionsCollection` query (the same
        RESOURCE_LIMITS_EXCEEDED rejection hyper-active accounts trigger).
        """
        from datetime import UTC, datetime, timedelta

        from app.github.queries import CONTRIBUTION_REPOS

        now = datetime.now(UTC)
        try:
            data = await self.graphql(
                CONTRIBUTION_REPOS,
                {
                    "login": username,
                    "from": (now - timedelta(days=365)).isoformat(),
                    "to": now.isoformat(),
                },
            )
        except Exception:
            logger.warning(
                "Contribution-repo-count query failed for %s; defaulting to 0",
                username,
                exc_info=True,
            )
            return 0
        user = data.get("user") or {}
        contributions = user.get("contributionsCollection") or {}
        repos = contributions.get("commitContributionsByRepository") or []
        return sum(
            1 for r in repos if (r.get("contributions") or {}).get("totalCount", 0) >= min_commits
        )

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
        body = resp.json()
        payload = body.get("data")
        errors = body.get("errors")
        # GitHub's GraphQL returns partial `data` alongside `errors` when it can
        # resolve some fields but not others — e.g. RESOURCE_LIMITS_EXCEEDED on an
        # expensive field for a hyper-active account. Downstream ingestion reads
        # every field defensively, so partial data is still useful. Only treat the
        # response as fatal when nothing came back at all.
        if errors:
            if payload is None:
                raise RuntimeError(f"GraphQL error: {errors}")
            logger.warning("Partial GraphQL response; continuing with partial data: %s", errors)
        return payload
