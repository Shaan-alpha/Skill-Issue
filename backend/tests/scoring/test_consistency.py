import pathlib
from datetime import UTC, datetime, timedelta

from app.models import Profile
from app.scoring.consistency import MAX_POINTS, score


def _load(name: str) -> Profile:
    return Profile.model_validate_json(
        (pathlib.Path(__file__).parent.parent / "fixtures" / name).read_text()
    )


def test_student_profile_scores_low() -> None:
    profile = _load("profile_student.json")
    profile.commit_dates = []
    result = score(profile)
    assert result.points == 0
    assert result.max_points == MAX_POINTS


def test_consistent_profile_scores_high() -> None:
    profile = _load("profile_senior.json")
    # Generate 40 commit dates as datetimes (matching the Profile schema and
    # what Pydantic produces in prod when ingestion passes YYYY-MM-DD strings).
    now = datetime.now(UTC)
    profile.commit_dates = [now - timedelta(days=i * 5) for i in range(40)]
    result = score(profile)
    assert result.points == 10  # 4 (cadence) + 3 (gap < 60) + 3 (vol >= 30)
    assert len(result.evidence) == 3


def test_dry_spell_scores_low() -> None:
    profile = _load("profile_senior.json")
    now = datetime.now(UTC)
    profile.commit_dates = [
        now - timedelta(days=1),
        now - timedelta(days=80),
    ]
    result = score(profile)
    # Cadence: might hit 2 months but not 3 -> 0 pts
    # Gap: 79 days > 60 -> 0 pts
    # Volume: 2 < 30 -> 0 pts
    assert result.points <= 4
