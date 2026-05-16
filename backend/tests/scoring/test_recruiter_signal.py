import pathlib
from datetime import UTC, datetime

from app.models import Profile, Repo
from app.scoring.recruiter_signal import MAX_POINTS, score


def _load(name: str) -> Profile:
    return Profile.model_validate_json(
        (pathlib.Path(__file__).parent.parent / "fixtures" / name).read_text()
    )


def test_student_profile_scores_low() -> None:
    profile = _load("profile_student.json")
    result = score(profile)
    assert result.points == 0
    assert result.max_points == MAX_POINTS


def test_senior_profile_scores_high() -> None:
    profile = _load("profile_senior.json")
    # Add 51 stars to one repo
    if profile.repos:
        profile.repos[0].stars = 51
    else:
        profile.repos = [
            Repo(
                name="x",
                full_name="y/x",
                primary_language="Python",
                stars=51,
                forks=0,
                is_fork=False,
                has_readme=True,
                has_tests=True,
                has_ci=True,
                deployment_hints=[],
                last_commit_at=datetime.now(UTC),
                created_at=datetime.now(UTC),
            )
        ]

    profile.has_sponsors_listing = True
    profile.blog = "https://shaan.dev"

    result = score(profile)
    assert result.points == 15
    assert len(result.evidence) == 3


def test_pro_member_signal() -> None:
    profile = _load("profile_oss.json")
    profile.company = "@google"
    profile.blog = None
    profile.hireable = False
    profile.repos = []

    result = score(profile)
    assert result.points == 5
    assert result.evidence[0].signal == "pro_verification"
