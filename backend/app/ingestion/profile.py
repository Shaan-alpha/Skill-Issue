from __future__ import annotations

from datetime import UTC, datetime
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
    external_prs_merged = external_user.get("pullRequests", {}).get("totalCount", 0)
    external_reviews = (
        external_user.get("contributionsCollection", {})
        .get("pullRequestReviewContributions", {})
        .get("totalCount", 0)
    )

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
        commit_dates=[],  # Task 10 will fill
        account_created_at=_parse_dt(user["created_at"]) or datetime.now(UTC),
    )
