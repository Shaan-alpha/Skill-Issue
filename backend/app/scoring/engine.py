"""Two-pass scoring engine.

Pass 1: score the file-existence-only Profile to get a base total.
Pass 2: run tier-gated depth enrichment, then re-score on the enriched Profile.

The final tier may differ from the base tier — the depth signals applied are
the ones earned by the *base* score, but the displayed tier reflects the
enriched total.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.models import Profile, Report, ScoreBreakdown
from app.scoring import (
    consistency,
    engineering_maturity,
    learning_trajectory,
    oss_collab,
    recruiter_signal,
    repo_quality,
)
from app.scoring.badges import compute_badges
from app.scoring.depth import enrich_for_tier
from app.scoring.tiers import assign_tier

if TYPE_CHECKING:
    from app.github.client import GitHubClient


def _score(profile: Profile) -> ScoreBreakdown:
    return ScoreBreakdown(
        repo_quality=repo_quality.score(profile),
        engineering_maturity=engineering_maturity.score(profile),
        oss_collab=oss_collab.score(profile),
        consistency=consistency.score(profile),
        recruiter_signal=recruiter_signal.score(profile),
        learning_trajectory=learning_trajectory.score(profile),
    )


async def run_scoring_engine(profile: Profile, gh: GitHubClient) -> Report:
    """Score, enrich, re-score, then build the final Report."""
    base_breakdown = _score(profile)
    base_total = base_breakdown.total()
    base_tier = assign_tier(base_total).name

    await enrich_for_tier(profile, base_tier, gh)

    final_breakdown = _score(profile)
    final_total = final_breakdown.total()
    final_tier_info = assign_tier(final_total)

    badges = compute_badges(profile, final_breakdown)

    return Report(
        username=profile.username,
        tier=final_tier_info,
        badges=badges,
        breakdown=final_breakdown,
        total=final_total,
        generated_at=datetime.now(UTC),
    )
