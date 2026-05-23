"""Tier-gated depth enrichment.

The function mutates the input Profile in place. Callers should run the base
scoring pass, decide a tier, call this, then re-score.
"""

import asyncio
import re
from typing import TYPE_CHECKING

from app.models import Profile, TierName

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

_CONVENTIONAL_PREFIX = re.compile(
    r"^(feat|fix|chore|docs|refactor|test|perf|build|ci|style|revert)(\(.+\))?: ", re.I
)


def _at_least(profile_tier: TierName, threshold: TierName) -> bool:
    return _TIER_RANK[profile_tier] >= _TIER_RANK[threshold]


async def _enrich_repo_professional(repo_full_name: str, gh: "GitHubClient") -> dict[str, object]:
    owner, name = repo_full_name.split("/", 1)
    license_task = gh.get_license(owner, name)
    workflows_task = gh.list_workflow_files(owner, name)
    readme_task = gh.get_repo_readme_text(owner, name)
    license_id, workflows, readme = await asyncio.gather(license_task, workflows_task, readme_task)
    return {
        "full_name": repo_full_name,
        "license_id": license_id,
        "workflow_count": len(workflows),
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
    good = sum(1 for m in messages if len(m.splitlines()[0]) >= 50 or _CONVENTIONAL_PREFIX.match(m))
    return round(good / len(messages) * 100)


async def enrich_for_tier(profile: Profile, base_tier: TierName, gh: "GitHubClient") -> None:
    """Populate Profile depth-signal fields appropriate to the user's base tier."""
    non_fork = [r for r in profile.repos if not r.is_fork]
    top10 = non_fork[:10]
    top5 = non_fork[:5]

    if _at_least(base_tier, "Professional Developer"):
        results = await asyncio.gather(*(_enrich_repo_professional(r.full_name, gh) for r in top10))
        profile.licensed_repos = [
            str(r["full_name"]) for r in results if r["license_id"] is not None
        ]
        profile.workflow_counts = {
            str(r["full_name"]): int(r["workflow_count"])  # type: ignore[arg-type]
            for r in results
            if int(r["workflow_count"])  # type: ignore[arg-type]
        }
        profile.readme_lengths = {
            str(r["full_name"]): int(r["readme_length"])  # type: ignore[arg-type]
            for r in results
            if int(r["readme_length"])  # type: ignore[arg-type]
        }

    if _at_least(base_tier, "Senior Engineer"):
        profile.review_avg_comments = await gh.get_review_depth(profile.username)
        dep_results = await asyncio.gather(*(_enrich_repo_senior(r.full_name, gh) for r in top5))
        profile.dep_files = {
            str(r["full_name"]): list(r["dep_files"])  # type: ignore[arg-type]
            for r in dep_results
            if r["dep_files"]
        }

    if _at_least(base_tier, "Staff Engineer"):
        commit_samples = await asyncio.gather(
            *(gh.list_recent_commits_sample(*r.full_name.split("/", 1), limit=20) for r in top5)
        )
        all_messages = [m for batch in commit_samples for m in batch]
        profile.commit_message_quality = _commit_message_quality(all_messages)
        profile.cross_repo_contribution_count = await gh.get_contribution_repo_count(
            profile.username, min_commits=10
        )
