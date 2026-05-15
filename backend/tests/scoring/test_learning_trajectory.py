import pathlib
from datetime import UTC, datetime, timedelta

from app.models import Profile, Repo
from app.scoring.learning_trajectory import MAX_POINTS, score


def _load(name: str) -> Profile:
    return Profile.model_validate_json(
        (pathlib.Path(__file__).parent.parent / "fixtures" / name).read_text()
    )


def test_student_profile_scores_low() -> None:
    profile = _load("profile_student.json")
    # Fresh account, no repos in last year, no commits
    profile.account_created_at = datetime.now(UTC) - timedelta(days=100)
    profile.repos = []
    profile.commit_dates = []

    result = score(profile)
    assert result.points == 0
    assert result.max_points == MAX_POINTS


def test_senior_profile_scores_high() -> None:
    profile = _load("profile_senior.json")
    now = datetime.now(UTC)

    # 1. Old account
    profile.account_created_at = now - timedelta(days=365 * 5)

    # 2. Repo growth
    profile.repos = [
        Repo(
            name="r1",
            full_name="u/r1",
            primary_language="X",
            stars=0,
            forks=0,
            is_fork=False,
            has_readme=True,
            has_tests=False,
            has_ci=False,
            deployment_hints=[],
            last_commit_at=now,
            created_at=now - timedelta(days=10),
        ),
        Repo(
            name="r2",
            full_name="u/r2",
            primary_language="X",
            stars=0,
            forks=0,
            is_fork=False,
            has_readme=True,
            has_tests=False,
            has_ci=False,
            deployment_hints=[],
            last_commit_at=now,
            created_at=now - timedelta(days=20),
        ),
        Repo(
            name="r3",
            full_name="u/r3",
            primary_language="X",
            stars=0,
            forks=0,
            is_fork=False,
            has_readme=True,
            has_tests=False,
            has_ci=False,
            deployment_hints=[],
            last_commit_at=now,
            created_at=now - timedelta(days=30),
        ),
    ]

    # 3. YOY activity
    profile.commit_dates = [
        now - timedelta(days=5),
        now - timedelta(days=400),
    ]

    result = score(profile)
    assert result.points == 10
    assert len(result.evidence) == 3


def test_partial_signals() -> None:
    profile = _load("profile_oss.json")
    now = datetime.now(UTC)

    # Only account age
    profile.account_created_at = now - timedelta(days=365 * 4)
    profile.repos = []
    profile.commit_dates = [now - timedelta(days=5)]  # Only Y1

    result = score(profile)
    assert result.points == 3
    assert result.evidence[0].signal == "account_longevity"
