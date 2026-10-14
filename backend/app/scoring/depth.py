"""Tier-gated depth enrichment.

The function mutates the input Profile in place. Callers should run the base
scoring pass, decide a tier, call this, then re-score.

Review depth and cross-repo breadth need a request of their own. Licences
arrive with the repo list, so unlocking them is free. README depth, dependency
manifests, workflow counts and commit-subject quality come free for every tier
from ingestion's root listings, workflow probe and commit history.
"""

from typing import TYPE_CHECKING

from app.concurrency import gather_all
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


def _at_least(profile_tier: TierName, threshold: TierName) -> bool:
    return _TIER_RANK[profile_tier] >= _TIER_RANK[threshold]


async def _enrich_senior(profile: Profile, gh: "GitHubClient") -> None:
    profile.review_avg_comments = await gh.get_review_depth(profile.username)


async def _enrich_staff(profile: Profile, gh: "GitHubClient") -> None:
    profile.cross_repo_contribution_count = await gh.get_contribution_repo_count(
        profile.username, min_commits=10
    )


async def enrich_for_tier(profile: Profile, base_tier: TierName, gh: "GitHubClient") -> None:
    """Populate Profile depth-signal fields appropriate to the user's base tier.

    Every unlocked tier's reads are independent, so they all run at once; the
    client bounds how many requests are in flight.
    """
    if _at_least(base_tier, "Professional Developer"):
        # Every non-fork repo, the set Repo Quality divides by.
        profile.licensed_repos = [
            r.full_name for r in profile.repos if not r.is_fork and r.has_license
        ]

    steps = []
    if _at_least(base_tier, "Senior Engineer"):
        steps.append(_enrich_senior(profile, gh))
    if _at_least(base_tier, "Staff Engineer"):
        steps.append(_enrich_staff(profile, gh))
    await gather_all(*steps)
