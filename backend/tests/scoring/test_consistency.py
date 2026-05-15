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
    # Generate 40 commit dates, one every 5 days (covering ~200 days)
    now = datetime.now(UTC)
    dates = []
    for i in range(40):
        d = now - timedelta(days=i * 5)
        dates.append(d.strftime("%Y-%m-%d"))

    profile.commit_dates = dates
    result = score(profile)
    assert result.points == 10  # 4 (cadence) + 3 (gap < 60) + 3 (vol >= 30)
    assert len(result.evidence) == 3


def test_dry_spell_scores_low() -> None:
    profile = _load("profile_senior.json")
    # Two commits with a large gap
    now = datetime.now(UTC)
    dates = [
        (now - timedelta(days=1)).strftime("%Y-%m-%d"),
        (now - timedelta(days=80)).strftime("%Y-%m-%d"),
    ]
    profile.commit_dates = dates
    result = score(profile)
    # Cadence: might hit 2 months but not 3 -> 0 pts
    # Gap: 79 days > 60 -> 0 pts
    # Volume: 2 < 30 -> 0 pts
    assert result.points <= 4
