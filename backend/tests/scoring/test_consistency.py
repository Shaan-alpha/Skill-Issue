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


def test_a_cut_off_commit_history_is_not_read_as_a_dry_spell() -> None:
    """Ingestion reads each repo's 100 most recent commits. A developer who
    commits every three days arrives with ~300 days of history and nothing
    before it; that missing stretch is the page limit, not silence."""
    profile = _load("profile_senior.json")
    profile.account_created_at = datetime(2015, 1, 1, tzinfo=UTC)
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    profile.commit_dates = [today - timedelta(days=3 * i) for i in range(100)]
    profile.commit_history_complete_since = min(profile.commit_dates)

    assert "low_dry_spell" in _signals(profile)


def test_gaps_before_the_history_is_complete_are_not_judged() -> None:
    """A sparse repo's old commits can't show a dry spell in the months where
    a busier repo's commits were cut off."""
    profile = _load("profile_senior.json")
    profile.account_created_at = datetime(2015, 1, 1, tzinfo=UTC)
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    busy = [today - timedelta(days=i) for i in range(100)]
    profile.commit_dates = [today - timedelta(days=250), *busy]
    profile.commit_history_complete_since = min(busy)

    assert "low_dry_spell" in _signals(profile)


def test_a_one_day_gap_reads_as_one_day() -> None:
    profile = _load("profile_senior.json")
    profile.account_created_at = datetime(2015, 1, 1, tzinfo=UTC)
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    profile.commit_dates = [today - timedelta(days=i) for i in range(366)]

    details = [e.detail for e in score(profile).evidence if e.signal == "low_dry_spell"]
    assert details == ["Longest gap between commits was 1 day (< 60)"]


def _dry_spell(profile: Profile) -> list[str]:
    return [e.detail for e in score(profile).evidence if e.signal == "low_dry_spell"]


def _midnight() -> datetime:
    return datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)


def test_a_burst_too_short_to_hold_a_dry_spell_earns_nothing() -> None:
    """A full page of commits from the last five days says nothing about the
    rest of the year. A stretch shorter than 60 days can't show a 60-day gap,
    so judging it alone would hand out the points to any burst."""
    profile = _load("profile_senior.json")
    profile.account_created_at = datetime(2015, 1, 1, tzinfo=UTC)
    today = _midnight()
    burst = [today - timedelta(days=i) for i in range(5)]
    profile.commit_dates = [today - timedelta(days=300), today - timedelta(days=290), *burst]
    profile.commit_history_complete_since = min(burst)

    assert _dry_spell(profile) == []


def test_evidence_names_where_a_cut_off_history_was_judged_from() -> None:
    """Judged only from the day the history is complete, the evidence says so
    rather than claiming the whole year."""
    profile = _load("profile_senior.json")
    profile.account_created_at = datetime(2015, 1, 1, tzinfo=UTC)
    today = _midnight()
    profile.commit_dates = [today - timedelta(days=3 * i) for i in range(100)]
    start = min(profile.commit_dates)
    profile.commit_history_complete_since = start

    assert _dry_spell(profile) == [
        f"Longest gap between commits since {start.day} {start:%b %Y} was 3 days (< 60); "
        "earlier commits were only partly read"
    ]


def test_visible_gaps_bound_the_hidden_ones() -> None:
    """Commits a cut-off page hid could only shorten the gaps, so when the
    commits that were read already show no 60-day gap, the year is judged."""
    profile = _load("profile_senior.json")
    profile.account_created_at = datetime(2015, 1, 1, tzinfo=UTC)
    today = _midnight()
    busy = [today - timedelta(days=i) for i in range(30)]
    steady = [today - timedelta(days=20 * i) for i in range(19)]
    profile.commit_dates = sorted(set(busy + steady))
    profile.commit_history_complete_since = min(busy)

    assert _dry_spell(profile) == ["Longest gap between commits was at most 20 days (< 60)"]


def test_consistency_appends_cross_repo_evidence_when_available() -> None:
    profile = _load("profile_senior.json")
    now = datetime.now(UTC)
    profile.commit_dates = [now - timedelta(days=i * 5) for i in range(40)]
    profile.cross_repo_contribution_count = 8
    result = score(profile)
    assert any(e.signal == "cross_repo_breadth" for e in result.evidence)


_FALLBACK_NOTE = (
    "Counted from the 5 most recently pushed own repositories only: "
    "GitHub didn't return activity across all repositories"
)


def _every_fifth_day(profile: Profile) -> Profile:
    now = datetime.now(UTC)
    profile.commit_dates = [now - timedelta(days=i * 5) for i in range(73)]
    return profile


def test_volume_evidence_names_public_repositories() -> None:
    profile = _every_fifth_day(_load("profile_senior.json"))

    details = {e.signal: e.detail for e in score(profile).evidence}

    assert (
        details["high_volume"] == "Committed on 73 days in the last year across public repositories"
    )


def test_a_fallback_sample_says_what_it_counted() -> None:
    profile = _every_fifth_day(_load("profile_senior.json"))
    profile.commit_activity_scope = "own_recent_repos"

    result = score(profile)
    rows = {e.signal: (e.detail, e.weight) for e in result.evidence}

    assert rows["high_volume"][0] == "Committed on 73 days in the last year"
    assert rows["commit_activity_scope"] == (_FALLBACK_NOTE, 0)
    assert result.points == 10


def test_the_fallback_note_shows_even_without_commit_days() -> None:
    profile = _load("profile_senior.json")
    profile.commit_dates = []
    profile.commit_activity_scope = "own_recent_repos"

    result = score(profile)

    assert result.points == 0
    assert [(e.signal, e.detail) for e in result.evidence] == [
        ("commit_activity_scope", _FALLBACK_NOTE)
    ]
