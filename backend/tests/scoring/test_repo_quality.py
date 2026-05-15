from pathlib import Path

from app.models import Profile
from app.scoring.repo_quality import MAX_POINTS, score

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> Profile:
    return Profile.model_validate_json((FIXTURES / name).read_text())


def test_student_profile_scores_zero() -> None:
    result = score(_load("profile_student.json"))

    assert result.points == 0
    assert result.max_points == MAX_POINTS == 30
    assert result.evidence == []


def test_oss_profile_scores_twenty_without_deployment_hint() -> None:
    result = score(_load("profile_oss.json"))

    assert result.points == 20
    assert [e.signal for e in result.evidence] == [
        "readme_majority",
        "testing_or_ci",
        "recent_activity",
    ]


def test_senior_profile_scores_twenty_six_until_license_signal_lands() -> None:
    result = score(_load("profile_senior.json"))

    assert result.points == 26
    assert len(result.evidence) == 4


def test_evidence_weights_sum_to_points() -> None:
    result = score(_load("profile_oss.json"))

    assert sum(e.weight for e in result.evidence) == result.points


def test_repo_quality_license_majority_fires_when_half_or_more_licensed() -> None:
    from app.models import Profile
    from app.scoring import repo_quality

    profile = Profile.model_validate_json(
        (FIXTURES / "profile_senior.json").read_text()
    )
    profile.licensed_repos = [r.full_name for r in profile.repos[: len(profile.repos) // 2 + 1]]
    result = repo_quality.score(profile)
    assert any(e.signal == "license_majority" for e in result.evidence)
    assert result.points >= 4


def test_repo_quality_license_majority_does_not_fire_when_few_licensed() -> None:
    from app.models import Profile
    from app.scoring import repo_quality

    profile = Profile.model_validate_json(
        (FIXTURES / "profile_senior.json").read_text()
    )
    profile.licensed_repos = [profile.repos[0].full_name]
    result = repo_quality.score(profile)
    assert not any(e.signal == "license_majority" for e in result.evidence)
