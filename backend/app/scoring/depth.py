"""Tier-gated depth enrichment.

The function mutates the input Profile in place. Callers should run the base
scoring pass, decide a tier, call this, then re-score.

Only signals that need a request of their own live here. README depth,
dependency manifests, workflow counts and commit-subject quality come free
from ingestion's root listings, workflow probe and commit history.
"""

from typing import TYPE_CHECKING

from app.concurrency import gather_all
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


def _at_least(profile_tier: TierName, threshold: TierName) -> bool:
    return _TIER_RANK[profile_tier] >= _TIER_RANK[threshold]


async def _enrich_professional(profile: Profile, repos: list[Repo], gh: "GitHubClient") -> None:
    license_ids = await gather_all(*(gh.get_license(*r.full_name.split("/", 1)) for r in repos))
    profile.licensed_repos = [
        r.full_name for r, license_id in zip(repos, license_ids, strict=True) if license_id
    ]


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
    top10 = [r for r in profile.repos if not r.is_fork][:10]

    steps = []
    if _at_least(base_tier, "Professional Developer"):
        steps.append(_enrich_professional(profile, top10, gh))
    if _at_least(base_tier, "Senior Engineer"):
        steps.append(_enrich_senior(profile, gh))
    if _at_least(base_tier, "Staff Engineer"):
        steps.append(_enrich_staff(profile, gh))
    await gather_all(*steps)
