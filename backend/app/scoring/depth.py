"""Tier-gated depth enrichment.

The function mutates the input Profile in place. Callers should run the base
scoring pass, decide a tier, call this, then re-score.
"""

import re
from typing import TYPE_CHECKING

from app.ingestion.profile import gather_all
from app.models import Profile, Repo, TierName

if TYPE_CHECKING:
    from app.github.client import GitHubClient

_TIER_RANK: dict[TierName, int] = {
    "Hobbyist": 0,
    "Student Builder": 1,
    "Entry-Level Engineer": 2,
    "Professional Developer": 3,
    "Senior Engineer": 4,
    "Staff Engineer": 5,
    "Principal Engineer": 6,
}

_DEP_FILES = {
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "cargo.toml",
    "go.mod",
    "gemfile",
    "composer.json",
}

# v1.0.7 SI-36: bounded scope group `\([^)]{0,100}\)` (was greedy `\(.+\)`) since
# commit messages are attacker-influenced (analyze your own crafted repo).
_CONVENTIONAL_PREFIX = re.compile(
    r"^(feat|fix|chore|docs|refactor|test|perf|build|ci|style|revert)(\([^)]{0,100}\))?: ", re.I
)

# Truncate each untrusted commit message before regex/splitlines processing.
_COMMIT_MSG_MAX = 500


def _at_least(profile_tier: TierName, threshold: TierName) -> bool:
    return _TIER_RANK[profile_tier] >= _TIER_RANK[threshold]


async def _enrich_repo_professional(repo_full_name: str, gh: "GitHubClient") -> dict[str, object]:
    owner, name = repo_full_name.split("/", 1)
    license_id, readme = await gather_all(
        gh.get_license(owner, name), gh.get_repo_readme_text(owner, name)
    )
    return {
        "full_name": repo_full_name,
        "license_id": license_id,
        "readme_length": len(readme or ""),
    }


async def _enrich_repo_senior(repo_full_name: str, gh: "GitHubClient") -> dict[str, object]:
    owner, name = repo_full_name.split("/", 1)
    contents = await gh.get_repo_root_contents(owner, name)
    lowered = {e.lower() for e in contents}
    return {
        "full_name": repo_full_name,
        "dep_files": sorted(lowered & _DEP_FILES),
    }


def _commit_message_quality(messages: list[str]) -> int:
    if not messages:
        return 0
    good = 0
    for raw in messages:
        m = raw[:_COMMIT_MSG_MAX]
        first_line = (m.splitlines() or [""])[0]
        if len(first_line) >= 50 or _CONVENTIONAL_PREFIX.match(m):
            good += 1
    return round(good / len(messages) * 100)


async def _enrich_professional(profile: Profile, repos: list[Repo], gh: "GitHubClient") -> None:
    results = await gather_all(*(_enrich_repo_professional(r.full_name, gh) for r in repos))
    profile.licensed_repos = [str(r["full_name"]) for r in results if r["license_id"] is not None]
    profile.readme_lengths = {
        str(r["full_name"]): int(r["readme_length"])  # type: ignore[arg-type]
        for r in results
        if int(r["readme_length"])  # type: ignore[arg-type]
    }


async def _enrich_senior(profile: Profile, repos: list[Repo], gh: "GitHubClient") -> None:
    review_depth, dep_results = await gather_all(
        gh.get_review_depth(profile.username),
        gather_all(*(_enrich_repo_senior(r.full_name, gh) for r in repos)),
    )
    profile.review_avg_comments = review_depth  # type: ignore[assignment]
    profile.dep_files = {
        str(r["full_name"]): list(r["dep_files"])  # type: ignore[arg-type]
        for r in dep_results  # type: ignore[union-attr]
        if r["dep_files"]  # type: ignore[index]
    }


async def _enrich_staff(profile: Profile, repos: list[Repo], gh: "GitHubClient") -> None:
    commit_samples, cross_repo_count = await gather_all(
        gather_all(
            *(gh.list_recent_commits_sample(*r.full_name.split("/", 1), limit=20) for r in repos)
        ),
        gh.get_contribution_repo_count(profile.username, min_commits=10),
    )
    all_messages = [m for batch in commit_samples for m in batch]  # type: ignore[union-attr]
    profile.commit_message_quality = _commit_message_quality(all_messages)
    profile.cross_repo_contribution_count = cross_repo_count  # type: ignore[assignment]


async def enrich_for_tier(profile: Profile, base_tier: TierName, gh: "GitHubClient") -> None:
    """Populate Profile depth-signal fields appropriate to the user's base tier.

    Every unlocked tier's reads are independent, so they all run at once; the
    client bounds how many requests are in flight.
    """
    non_fork = [r for r in profile.repos if not r.is_fork]
    top10 = non_fork[:10]
    top5 = non_fork[:5]

    steps = []
    if _at_least(base_tier, "Professional Developer"):
        steps.append(_enrich_professional(profile, top10, gh))
    if _at_least(base_tier, "Senior Engineer"):
        steps.append(_enrich_senior(profile, top5, gh))
    if _at_least(base_tier, "Staff Engineer"):
        steps.append(_enrich_staff(profile, top5, gh))
    await gather_all(*steps)
