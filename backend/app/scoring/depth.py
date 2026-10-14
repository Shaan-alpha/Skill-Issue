"""Tier-gated depth enrichment.

The function mutates the input Profile in place. Callers should run the base
scoring pass, decide a tier, call this, then re-score.

Review depth needs a request of its own. Licences arrive with the repo list
and cross-repo breadth with ingestion's commit activity, so unlocking them is
free. README depth, dependency manifests, workflow counts and commit-subject
quality come free for every tier from ingestion's root listings, workflow
probe and commit sample.
"""

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


def _at_least(profile_tier: TierName, threshold: TierName) -> bool:
    return _TIER_RANK[profile_tier] >= _TIER_RANK[threshold]


async def _enrich_senior(profile: Profile, gh: "GitHubClient") -> None:
    profile.review_avg_comments = await gh.get_review_depth(profile.username)


async def enrich_for_tier(profile: Profile, base_tier: TierName, gh: "GitHubClient") -> None:
    """Populate Profile depth-signal fields appropriate to the user's base tier.

    Only review depth needs a request of its own; licences and cross-repo
    breadth come with data ingestion already read.
    """
    if _at_least(base_tier, "Professional Developer"):
        # Every listed non-fork repo, the set Repo Quality divides by.
        profile.licensed_repos = [
            r.full_name for r in profile.repos if not r.is_fork and r.has_license
        ]
    if _at_least(base_tier, "Staff Engineer"):
        # Public repos with 10+ commits last year, counted by ingestion.
        profile.cross_repo_contribution_count = profile.substantial_repo_count
    if _at_least(base_tier, "Senior Engineer"):
        await _enrich_senior(profile, gh)
