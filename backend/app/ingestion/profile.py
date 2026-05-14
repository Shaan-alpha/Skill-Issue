from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.github.queries import PINNED_REPOS
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
        last_commit_at=_parse_dt(raw.get("pushed_at")),
        created_at=_parse_dt(raw.get("created_at")) or datetime.now(UTC),
    )


async def ingest_profile(username: str, gh: GitHubClient) -> Profile:
    user = await gh.get_user(username)
    repos_raw = await gh.list_repos(username)
    pinned = await gh.graphql(PINNED_REPOS, {"login": username})

    repos = [_repo_from_rest(r) for r in repos_raw if not r.get("fork", False)]
    pinned_names = {
        n["name"]
        for n in (pinned.get("user", {}).get("pinnedItems", {}).get("nodes") or [])
    }

    for r in repos:
        if r.name in pinned_names:
            r.deployment_hints.append("pinned")

    return Profile(
        username=user["login"],
        bio=user.get("bio"),
        profile_readme_chars=0,  # Task 5 will fill
        followers=user.get("followers", 0),
        public_repos=user.get("public_repos", 0),
        languages={},  # Task 5 will fill
        repos=repos,
        external_prs_merged=0,  # Task 5 will fill
        external_reviews=0,  # Task 5 will fill
        commit_dates=[],  # Task 10 will fill
        account_created_at=_parse_dt(user["created_at"]) or datetime.now(UTC),
    )
