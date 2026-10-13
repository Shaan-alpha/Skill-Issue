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
    # A commit day every 5 days across the whole last year (73 days), as
    # datetimes (matching the Profile schema and what Pydantic produces in prod
    # when ingestion passes YYYY-MM-DD strings). The window must be covered end
    # to end: a profile active only in its last 195 days had a 170-day silence.
    now = datetime.now(UTC)
    profile.commit_dates = [now - timedelta(days=i * 5) for i in range(73)]
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


def _signals(profile: Profile) -> set[str]:
    return {e.signal for e in score(profile).evidence}


def test_single_recent_commit_is_not_a_low_dry_spell() -> None:
    """One commit day ten days ago means the user was silent for the ~355 days
    before it. The gap from the start of the window counts as a dry spell."""
    profile = _load("profile_senior.json")
    now = datetime.now(UTC)
    profile.account_created_at = now - timedelta(days=5 * 365)
    profile.commit_dates = [now - timedelta(days=10)]

    assert "low_dry_spell" not in _signals(profile)


def test_volume_counts_only_commit_days_in_the_last_year() -> None:
    """Ingestion collects two years of commit days (Learning Trajectory needs the
    older year), but the volume rule and its evidence are about the last year."""
    profile = _load("profile_senior.json")
    now = datetime.now(UTC)
    profile.account_created_at = now - timedelta(days=5 * 365)
    last_year = [now - timedelta(days=10 * i + 1) for i in range(20)]
    year_before = [now - timedelta(days=400 + 20 * i) for i in range(15)]
    profile.commit_dates = sorted(last_year + year_before)

    result = score(profile)
    assert "high_volume" not in {e.signal for e in result.evidence}
    assert not any("35" in e.detail for e in result.evidence)


def test_a_gap_older_than_a_year_does_not_cost_the_dry_spell_points() -> None:
    profile = _load("profile_senior.json")
    now = datetime.now(UTC)
    profile.account_created_at = now - timedelta(days=5 * 365)
    steady_last_year = [now - timedelta(days=5 * i) for i in range(73)]
    old_gap = [now - timedelta(days=450), now - timedelta(days=550)]
    profile.commit_dates = sorted(steady_last_year + old_gap)

    assert "low_dry_spell" in _signals(profile)


def test_an_account_younger_than_a_year_is_judged_from_its_creation() -> None:
    """A dry spell cannot predate the account. Committing weekly since creation
    100 days ago is consistent, not a 265-day silence."""
    profile = _load("profile_senior.json")
    now = datetime.now(UTC)
    profile.account_created_at = now - timedelta(days=100)
    profile.commit_dates = [now - timedelta(days=d) for d in range(95, 0, -7)]

    assert "low_dry_spell" in _signals(profile)


def test_consistency_appends_cross_repo_evidence_when_available() -> None:
    profile = _load("profile_senior.json")
    now = datetime.now(UTC)
    profile.commit_dates = [now - timedelta(days=i * 5) for i in range(40)]
    profile.cross_repo_contribution_count = 8
    result = score(profile)
    assert any(e.signal == "cross_repo_breadth" for e in result.evidence)
