from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.models import Profile
from app.scoring.repo_quality import MAX_POINTS, score

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> Profile:
    return Profile.model_validate_json((FIXTURES / name).read_text())


# `recent_activity` (6 pts) fires on a non-fork commit inside a rolling 90-day
# window measured from `datetime.now(UTC)`, so a fixture with a hardcoded
# `last_commit_at` silently stops earning it once the file ages past 90 days —
# the suite goes red on a calendar date with no code change. That is exactly
# what happened on 2026-07-31: `profile_oss.json`'s newest commit (2026-05-01)
# turned 91 days old overnight and this file's 20-point expectation broke.
# `profile_senior.json` (2026-05-10) was 8 days behind it.
#
# Pin the recency-sensitive dates relative to now, the way `test_consistency.py`
# and `test_learning_trajectory.py` already do for the other time-windowed
# scorers, so these tests assert the scoring rule instead of the calendar.
def _with_recent_commit(profile: Profile) -> Profile:
    """Make the profile's newest repo unambiguously inside the 90-day window."""
    profile.repos[0].last_commit_at = datetime.now(UTC) - timedelta(days=1)
    return profile


def _with_stale_commits(profile: Profile) -> Profile:
    """Push every repo well outside the 90-day window."""
    stale = datetime.now(UTC) - timedelta(days=365)
    for repo in profile.repos:
        repo.last_commit_at = stale
    return profile


def test_student_profile_scores_zero() -> None:
    result = score(_with_stale_commits(_load("profile_student.json")))

    assert result.points == 0
    assert result.max_points == MAX_POINTS == 30
    assert result.evidence == []


def test_oss_profile_scores_twenty_without_deployment_hint() -> None:
    result = score(_with_recent_commit(_load("profile_oss.json")))

    assert result.points == 20
    assert [e.signal for e in result.evidence] == [
        "readme_majority",
        "testing_or_ci",
        "recent_activity",
    ]


def test_recent_activity_does_not_fire_once_every_commit_is_stale() -> None:
    result = score(_with_stale_commits(_load("profile_oss.json")))

    assert not any(e.signal == "recent_activity" for e in result.evidence)
    assert result.points == 14


def test_senior_profile_scores_twenty_six_until_license_signal_lands() -> None:
    result = score(_with_recent_commit(_load("profile_senior.json")))

    assert result.points == 26
    assert len(result.evidence) == 4


def test_evidence_weights_sum_to_points() -> None:
    result = score(_with_recent_commit(_load("profile_oss.json")))

    assert sum(e.weight for e in result.evidence) == result.points


def test_repo_quality_license_majority_fires_when_half_or_more_licensed() -> None:
    from app.models import Profile
    from app.scoring import repo_quality

    profile = Profile.model_validate_json((FIXTURES / "profile_senior.json").read_text())
    profile.licensed_repos = [r.full_name for r in profile.repos[: len(profile.repos) // 2 + 1]]
    result = repo_quality.score(profile)
    assert any(e.signal == "license_majority" for e in result.evidence)
    assert result.points >= 4


def test_repo_quality_license_majority_does_not_fire_when_few_licensed() -> None:
    from app.models import Profile
    from app.scoring import repo_quality

    profile = Profile.model_validate_json((FIXTURES / "profile_senior.json").read_text())
    profile.licensed_repos = [profile.repos[0].full_name]
    result = repo_quality.score(profile)
    assert not any(e.signal == "license_majority" for e in result.evidence)
