from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import httpx

from app.github.queries import EXTERNAL_PRS, PINNED_REPOS
from app.models import Profile, Repo

if TYPE_CHECKING:
    from app.github.client import GitHubClient

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

    Silently tolerates per-repo HTTP failures: a single broken request must not
    take down the entire ingestion. Untouched repos keep their default `False`
    flags, which is the correct conservative reading.
    """
    owner, name = repo.full_name.split("/", 1)
    try:
        entries = await gh.get_repo_root_contents(owner, name)
    except httpx.HTTPError:
        return

    has_readme, has_tests, has_ci, hints = _classify_root_entries(entries)
    repo.has_readme = has_readme
    repo.has_tests = has_tests
    repo.has_ci = has_ci
    for hint in hints:
        if hint not in repo.deployment_hints:
            repo.deployment_hints.append(hint)


async def ingest_profile(username: str, gh: GitHubClient) -> Profile:
    user = await gh.get_user(username)
    repos_raw = await gh.list_repos(username)
    pinned = await gh.graphql(PINNED_REPOS, {"login": username})
    external = await gh.graphql(EXTERNAL_PRS, {"login": username})
    profile_readme = await gh.get_profile_readme(username)

    repos = [_repo_from_rest(r) for r in repos_raw if not r.get("fork", False)]
    pinned_names = {
        n["name"] for n in (pinned.get("user", {}).get("pinnedItems", {}).get("nodes") or [])
    }

    for r in repos:
        if r.name in pinned_names:
            r.deployment_hints.append("pinned")

    # Enrich README / tests / CI / deployment signals from each repo's root tree.
    # Capped at ROOT_CONTENT_LIMIT to stay polite to GitHub on heavy profiles.
    await asyncio.gather(*(_enrich_repo_signals(r, gh) for r in repos[:ROOT_CONTENT_LIMIT]))

    languages: dict[str, int] = {}
    for repo in repos[:ROOT_CONTENT_LIMIT]:
        owner, name = repo.full_name.split("/", 1)
        for language, bytes_count in (await gh.list_languages(owner, name)).items():
            languages[language] = languages.get(language, 0) + bytes_count

    external_user = external.get("user") or {}
    has_sponsors_listing = external_user.get("hasSponsorsListing", False)
    is_github_star = external_user.get("isGitHubStar", False)
    is_developer_program_member = external_user.get("isDeveloperProgramMember", False)

    external_prs = external_user.get("pullRequests", {})
    external_prs_merged = external_prs.get("totalCount", 0)
    external_reviews = (
        external_user.get("contributionsCollection", {})
        .get("pullRequestReviewContributions", {})
        .get("totalCount", 0)
    )

    external_orgs = set()
    for node in external_prs.get("nodes", []):
        owner_login = node.get("repository", {}).get("owner", {}).get("login")
        if owner_login and owner_login.lower() != username.lower():
            external_orgs.add(owner_login)

    # Task 10/12: Consistency and Learning Trajectory (commits over last 2 years)
    two_years_ago = (datetime.now(UTC) - timedelta(days=730)).isoformat()
    # Top 10 non-fork repos by update date
    top_repos = [r for r in repos_raw if not r.get("fork")][:10]

    commit_dates_set: set[datetime] = set()
    commit_tasks = [
        gh.list_commits(r["owner"]["login"], r["name"], username, two_years_ago) for r in top_repos
    ]
    all_repo_commits = await asyncio.gather(*commit_tasks)

    for repo_commits in all_repo_commits:
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
        external_prs_merged=external_prs_merged,
        external_reviews=external_reviews,
        external_orgs=external_orgs,
        commit_dates=sorted(commit_dates_set),
        account_created_at=_parse_dt(user["created_at"]) or datetime.now(UTC),
        company=user.get("company"),
        blog=user.get("blog"),
        hireable=bool(user.get("hireable")),
        has_sponsors_listing=has_sponsors_listing,
        is_github_star=is_github_star,
        is_developer_program_member=is_developer_program_member,
    )
