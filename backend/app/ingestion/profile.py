from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from app.github.queries import EXTERNAL_PRS, PINNED_REPOS
from app.models import Profile, Repo

if TYPE_CHECKING:
    from app.github.client import GitHubClient


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

    languages: dict[str, int] = {}
    for repo in repos[:20]:
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

    # Task 10: Consistency (commits over last year)
    one_year_ago = (datetime.now(UTC) - timedelta(days=365)).isoformat()
    # Top 10 non-fork repos by update date
    top_repos = [r for r in repos_raw if not r.get("fork")][:10]

    commit_dates_set: set[str] = set()
    commit_tasks = [
        gh.list_commits(r["owner"]["login"], r["name"], username, one_year_ago) for r in top_repos
    ]
    all_repo_commits = await asyncio.gather(*commit_tasks)

    for repo_commits in all_repo_commits:
        for c in repo_commits:
            date_str = c.get("commit", {}).get("author", {}).get("date")
            if date_str:
                commit_dates_set.add(date_str[:10])  # YYYY-MM-DD

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
        commit_dates=sorted(list(commit_dates_set)),
        account_created_at=_parse_dt(user["created_at"]) or datetime.now(UTC),
        company=user.get("company"),
        blog=user.get("blog"),
        hireable=bool(user.get("hireable")),
        has_sponsors_listing=has_sponsors_listing,
        is_github_star=is_github_star,
        is_developer_program_member=is_developer_program_member,
    )
