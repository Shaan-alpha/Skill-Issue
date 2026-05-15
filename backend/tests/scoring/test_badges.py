from pathlib import Path

from app.models import Profile, ScoreBreakdown, ScoreResult
from app.scoring.badges import compute_badges

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _zero_breakdown() -> ScoreBreakdown:
    z = ScoreResult(points=0, max_points=1)
    return ScoreBreakdown(
        repo_quality=z,
        engineering_maturity=z,
        oss_collab=z,
        consistency=z,
        recruiter_signal=z,
        learning_trajectory=z,
    )


def _profile(name: str = "profile_student.json") -> Profile:
    return Profile.model_validate_json((FIXTURES / name).read_text())


def test_no_badges_for_empty_profile() -> None:
    profile = _profile()  # student fixture, no notable signals
    badges = compute_badges(profile, _zero_breakdown())
    assert badges == []
