import pathlib

from app.models import Profile
from app.scoring.engine import run_scoring_engine


def _load(name: str) -> Profile:
    return Profile.model_validate_json(
        (pathlib.Path(__file__).parent.parent / "fixtures" / name).read_text()
    )


def test_engine_aggregates_all_scorers() -> None:
    profile = _load("profile_senior.json")
    report = run_scoring_engine(profile)

    assert report.username == profile.username
    assert report.total >= 0
    assert report.total <= 100
    assert report.breakdown.repo_quality.max_points == 30
    assert report.breakdown.engineering_maturity.max_points == 20
    assert report.breakdown.oss_collab.max_points == 15
    assert report.breakdown.consistency.max_points == 10
    assert report.breakdown.recruiter_signal.max_points == 15
    assert report.breakdown.learning_trajectory.max_points == 10

    # Ensure total matches the sum
    assert report.total == (
        report.breakdown.repo_quality.points
        + report.breakdown.engineering_maturity.points
        + report.breakdown.oss_collab.points
        + report.breakdown.consistency.points
        + report.breakdown.recruiter_signal.points
        + report.breakdown.learning_trajectory.points
    )
