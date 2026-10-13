from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from app.github.queries import (
    EXTERNAL_PRS,
    EXTERNAL_REVIEW_COUNT,
    PINNED_REPOS,
    external_merged_prs_query,
)
from app.models import Profile, Repo

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from app.github.client import GitHubClient

logger = logging.getLogger(__name__)


async def gather_all[T](*aws: Awaitable[T]) -> list[T]:
    """`asyncio.gather` that cancels the rest as soon as one awaitable fails.

    Plain gather leaves the siblings running after a failure: they keep calling
    GitHub for an analysis that has already failed, then hit the closed client
    and log "Task exception was never retrieved".
    """
    tasks = [asyncio.ensure_future(aw) for aw in aws]
    try:
        return await asyncio.gather(*tasks)
    except BaseException:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise


class NotAnIndividualError(Exception):
    """Raised when /users/{login} resolves to an Organization (or other
    non-User account type). The dependency layer maps this to a 422
    so the frontend can render a specific message."""


# How many repos to inspect for README / tests / CI / deployment signals.
# Matches the cap used for language aggregation. Beyond this, signals are
# diminishing and the API cost is real.
ROOT_CONTENT_LIMIT = 20

_TEST_DIRS = {"tests", "test", "__tests__", "spec", "specs"}
_CI_MARKERS = {
    ".github",
    ".circleci",
    ".gitlab-ci.yml",
    ".travis.yml",
    "azure-pipelines.yml",
    "bitbucket-pipelines.yml",
    "jenkinsfile",
}
_DEPLOYMENT_MARKERS: dict[str, str] = {
    "dockerfile": "dockerfile",
    "docker-compose.yml": "docker-compose",
    "docker-compose.yaml": "docker-compose",
    "vercel.json": "vercel",
    "netlify.toml": "netlify",
    "fly.toml": "fly",
    "render.yaml": "render",
    "app.yaml": "app-engine",
    "serverless.yml": "serverless",
    "serverless.yaml": "serverless",
    "procfile": "heroku",
    "wrangler.toml": "cloudflare",
}


def _classify_root_entries(entries: list[str]) -> tuple[bool, bool, bool, list[str]]:
    """Derive (has_readme, has_tests, has_ci, deployment_hints) from root entry names."""
    lowered = {entry.lower() for entry in entries}
    has_readme = any(entry.startswith("readme") for entry in lowered)
    has_tests = bool(lowered & _TEST_DIRS)
    has_ci = bool(lowered & _CI_MARKERS)
    hints = [hint for marker, hint in _DEPLOYMENT_MARKERS.items() if marker in lowered]
    # Preserve insertion order, dedupe (e.g. docker-compose.yml + .yaml both map to docker-compose).
    seen: set[str] = set()
    unique_hints = [h for h in hints if not (h in seen or seen.add(h))]
    return has_readme, has_tests, has_ci, unique_hints


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _repo_from_rest(raw: dict[str, Any]) -> Repo:
    return Repo(
        name=raw["name"],
        full_name=raw["full_name"],
        primary_language=raw.get("language"),
        stars=raw.get("stargazers_count", 0),
        forks=raw.get("forks_count", 0),
        is_fork=raw.get("fork", False),
        has_readme=False,
        has_tests=False,
        has_ci=False,
        deployment_hints=[],
        size_kb=raw.get("size", 0),
        last_commit_at=_parse_dt(raw.get("pushed_at")),
        created_at=_parse_dt(raw.get("created_at")) or datetime.now(UTC),
    )


async def _enrich_repo_signals(repo: Repo, gh: GitHubClient) -> None:
    """Inspect a repo's root contents and populate README/tests/CI/deployment flags.

    A repository GitHub won't serve (empty, DMCA'd, blocked) reads as an empty
    listing and keeps its conservative `False` flags. A rate limit or a server
    error propagates: scoring the repo as bare would cache a wrong, low report.
    """
    owner, name = repo.full_name.split("/", 1)
    entries = await gh.get_repo_root_contents(owner, name)

    has_readme, has_tests, has_ci, hints = _classify_root_entries(entries)
    repo.has_readme = has_readme
    repo.has_tests = has_tests
    repo.has_ci = has_ci
    for hint in hints:
        if hint not in repo.deployment_hints:
            repo.deployment_hints.append(hint)


async def _external_pr_signals(username: str, gh: GitHubClient) -> dict[str, Any]:
    """Merged PRs into other people's repositories, account badges and external
    orgs — the cheaper half; GitHub can usually compute this even for very
    active accounts."""
    try:
        external = await gh.graphql(
            EXTERNAL_PRS,
            {"login": username, "externalMerged": external_merged_prs_query(username)},
        )
    except Exception:
        logger.warning(
            "External PR/badge signals unavailable for %s; degrading to defaults",
            username,
            exc_info=True,
        )
        return {}
    external_user = external.get("user") or {}
    external_prs = external.get("search") or {}

    external_orgs: set[str] = set()
    for node in external_prs.get("nodes") or []:
        owner_login = ((node or {}).get("repository") or {}).get("owner", {}).get("login")
        if owner_login and owner_login.lower() != username.lower():
            external_orgs.add(owner_login)

    return {
        "has_sponsors_listing": external_user.get("hasSponsorsListing", False),
        "is_github_star": external_user.get("isGitHubStar", False),
        "is_developer_program_member": external_user.get("isDeveloperProgramMember", False),
        "external_prs_merged": external_prs.get("issueCount", 0),
        "external_orgs": external_orgs,
    }


async def _external_review_count(username: str, gh: GitHubClient) -> int:
    """PR review count — isolated because it's the field GitHub most often rejects."""
    try:
        reviews = await gh.graphql(EXTERNAL_REVIEW_COUNT, {"login": username})
    except Exception:
        logger.warning(
            "External review-count signal unavailable for %s; degrading to 0",
            username,
            exc_info=True,
        )
        return 0
    review_user = reviews.get("user") or {}
    review_contributions = (review_user.get("contributionsCollection") or {}).get(
        "pullRequestReviewContributions"
    ) or {}
    return review_contributions.get("totalCount", 0)


async def _ingest_external_signals(username: str, gh: GitHubClient) -> dict[str, Any]:
    """Fetch external-contribution signals: merged PRs, review count, badges, orgs.

    Split into two independent GraphQL calls so a failure of one can't sink the
    other. GitHub rejects the review-count field with RESOURCE_LIMITS_EXCEEDED for
    hyper-active accounts (SKILL-ISSUE-BACKEND-4); isolating it keeps the cheaper
    merged-PR / badge signals intact when only that field blows the budget. Every
    field here is a bonus signal, so any failure degrades to a conservative default
    rather than failing the whole analysis.
    """
    pr_signals, external_reviews = await gather_all(
        _external_pr_signals(username, gh), _external_review_count(username, gh)
    )
    return {
        "has_sponsors_listing": False,
        "is_github_star": False,
        "is_developer_program_member": False,
        "external_prs_merged": 0,
        "external_orgs": set(),
        **pr_signals,
        "external_reviews": external_reviews,
    }


async def ingest_profile(username: str, gh: GitHubClient) -> Profile:
    user = await gh.get_user(username)
    # GitHub reuses the /users/{login} endpoint for organisations — same shape,
    # different `type`. Our scoring engine assumes an individual developer
    # (pinned repos, contribution graph, PRs opened, commit cadence). Orgs
    # also break the GraphQL queries since `user(login:)` returns null for
    # an org and downstream `.get(...).get(...)` chains null-deref. Detect
    # early and surface a clean 422 so the caller can render a helpful
    # message instead of a generic 500.
    if user.get("type") == "Organization":
        raise NotAnIndividualError(
            f"'{username}' is a GitHub organization, not a user. "
            "Skill Issue scores individual developers — try a username instead."
        )

    # Everything below needs only the login, so it is issued at once; the
    # client bounds how many requests are actually in flight.
    repos_raw, pinned, external_signals, profile_readme = await gather_all(
        gh.list_repos(username),
        gh.graphql(PINNED_REPOS, {"login": username}),
        _ingest_external_signals(username, gh),
        gh.get_profile_readme(username),
    )

    repos = [_repo_from_rest(r) for r in repos_raw if not r.get("fork", False)]
    pinned_nodes = ((pinned.get("user") or {}).get("pinnedItems") or {}).get("nodes") or []
    pinned_names = {n["name"] for n in pinned_nodes if n}

    for r in repos:
        r.is_pinned = r.name in pinned_names

    # Root contents (README / tests / CI / deployment) and languages for the
    # first ROOT_CONTENT_LIMIT repos, plus two years of commit days from the
    # ten most recently updated (Consistency reads the last year, Learning
    # Trajectory compares it with the one before). All three run together.
    inspected = repos[:ROOT_CONTENT_LIMIT]
    top_repos = [r for r in repos_raw if not r.get("fork")][:10]
    two_years_ago = (datetime.now(UTC) - timedelta(days=730)).isoformat()
    _, language_maps, commit_lists = await gather_all(
        gather_all(*(_enrich_repo_signals(r, gh) for r in inspected)),
        gather_all(*(gh.list_languages(*r.full_name.split("/", 1)) for r in inspected)),
        gather_all(
            *(
                gh.list_commits(r["owner"]["login"], r["name"], username, two_years_ago)
                for r in top_repos
            )
        ),
    )

    languages: dict[str, int] = {}
    for repo_languages in language_maps:
        for language, bytes_count in repo_languages.items():
            languages[language] = languages.get(language, 0) + bytes_count

    commit_dates_set: set[datetime] = set()
    for repo_commits in commit_lists:
        for c in repo_commits:
            date_str = c.get("commit", {}).get("author", {}).get("date")
            if date_str:
                # Normalize to a UTC-aware day so downstream date math is safe.
                day = datetime.strptime(date_str[:10], "%Y-%m-%d").replace(tzinfo=UTC)
                commit_dates_set.add(day)

    return Profile(
        username=user["login"],
        bio=user.get("bio"),
        profile_readme_chars=len(profile_readme or ""),
        followers=user.get("followers", 0),
        public_repos=user.get("public_repos", 0),
        languages=languages,
        repos=repos,
        external_prs_merged=external_signals["external_prs_merged"],
        external_reviews=external_signals["external_reviews"],
        external_orgs=external_signals["external_orgs"],
        commit_dates=sorted(commit_dates_set),
        account_created_at=_parse_dt(user["created_at"]) or datetime.now(UTC),
        company=user.get("company"),
        blog=user.get("blog"),
        hireable=bool(user.get("hireable")),
        has_sponsors_listing=external_signals["has_sponsors_listing"],
        is_github_star=external_signals["is_github_star"],
        is_developer_program_member=external_signals["is_developer_program_member"],
    )
