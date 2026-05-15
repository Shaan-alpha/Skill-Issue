import pathlib

from app.models import Profile
from app.scoring.engineering_maturity import MAX_POINTS, score


def _load(name: str) -> Profile:
    return Profile.model_validate_json(
        (pathlib.Path(__file__).parent.parent / "fixtures" / name).read_text()
    )


def test_student_profile_scores_low() -> None:
    profile = _load("profile_student.json")
    result = score(profile)
    # The student profile gets 4 pts for Python (typed language)
    # But lacks size, CI, deployment+tests, and significant language diversity
    assert 0 <= result.points <= 8
    assert result.max_points == MAX_POINTS == 20


def test_senior_profile_scores_high() -> None:
    profile = _load("profile_senior.json")
    profile.repos[0].size_kb = 250  # Give it the size points
    result = score(profile)
    assert result.points >= 16
    assert len(result.evidence) >= 4


def test_evidence_weights_sum_to_points() -> None:
    profile = _load("profile_oss.json")
    profile.repos[0].size_kb = 250
    result = score(profile)
    assert sum(e.weight for e in result.evidence) == result.points


def test_engineering_maturity_uses_workflow_count_when_available() -> None:
    profile = _load("profile_senior.json")
    profile.workflow_counts = {profile.repos[0].full_name: 3, profile.repos[1].full_name: 2}
    result = score(profile)
    ci_evidence = next(e for e in result.evidence if e.signal == "ci_culture")
    assert "workflows" in ci_evidence.detail.lower()
