from datetime import UTC, datetime

from app.models import DeveloperCategory, Profile, Report, ScoreBreakdown
from app.scoring import (
    consistency,
    engineering_maturity,
    learning_trajectory,
    oss_collab,
    recruiter_signal,
    repo_quality,
)


def run_scoring_engine(profile: Profile) -> Report:
    """
    Runs all deterministic scorers and aggregates them into a final Report.
    """
    breakdown = ScoreBreakdown(
        repo_quality=repo_quality.score(profile),
        engineering_maturity=engineering_maturity.score(profile),
        oss_collab=oss_collab.score(profile),
        consistency=consistency.score(profile),
        recruiter_signal=recruiter_signal.score(profile),
        learning_trajectory=learning_trajectory.score(profile),
    )

    total = breakdown.total()

    # Heuristic categorization
    category: DeveloperCategory = "Student Builder"

    if total >= 80:
        category = "Senior Engineer"
    elif total >= 60:
        category = "Professional Developer"
    elif breakdown.oss_collab.points >= 10:
        category = "OSS Contributor"
    elif breakdown.recruiter_signal.points >= 8:
        category = "Entry-Level Engineer"
    elif breakdown.consistency.points >= 8:
        category = "Indie Hacker"

    return Report(
        username=profile.username,
        category=category,
        breakdown=breakdown,
        total=total,
        generated_at=datetime.now(UTC),
    )
