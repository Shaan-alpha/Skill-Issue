from datetime import UTC, datetime, timedelta
from itertools import pairwise

from app.models import Evidence, Profile, ScoreResult
from app.scoring.base import make_result

MAX_POINTS = 10
ONE_YEAR = timedelta(days=365)
# A gap this long is a dry spell. A stretch shorter than this can't contain
# one, so it is never judged on its own.
DRY_SPELL_DAYS = 60


def _aware(d: datetime) -> datetime:
    # Defensive: ingestion stores tz-aware UTC datetimes, but tests may
    # construct profiles with naive datetimes — coerce so date math stays safe.
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def _longest_gap(start: datetime, dates: list[datetime], end: datetime) -> int:
    boundaries = [start, *(d for d in dates if d >= start), end]
    return max(max((later - earlier).days, 0) for earlier, later in pairwise(boundaries))


def _days(n: int) -> str:
    return f"{n} {'day' if n == 1 else 'days'}"


def _dry_spell_evidence(
    profile: Profile, dates: list[datetime], year_ago: datetime, now: datetime
) -> str | None:
    """The detail for "no dry spell in the last year", or None if not earned.

    The silence before the first commit counts, measured from the start of the
    window or from account creation, whichever is later: a dry spell cannot
    predate the account.

    Where a repo's commit page came back full, its older commits went unseen.
    They could only shorten the gaps seen, so if the commits read show no dry
    spell, the year has none. Otherwise only the stretch where the history is
    complete can be judged, and the detail says where it starts.
    """
    window_start = max(year_ago, _aware(profile.account_created_at))
    gap = _longest_gap(window_start, dates, now)
    complete_since = profile.commit_history_complete_since
    cut = complete_since is not None and _aware(complete_since) > window_start
    if gap < DRY_SPELL_DAYS:
        bound = "at most " if cut else ""
        return f"Longest gap between commits was {bound}{_days(gap)} (< {DRY_SPELL_DAYS})"
    if not cut:
        return None
    start = _aware(complete_since)
    if (now - start).days < DRY_SPELL_DAYS:
        return None
    gap = _longest_gap(start, dates, now)
    if gap >= DRY_SPELL_DAYS:
        return None
    return (
        f"Longest gap between commits since {start.day} {start:%b %Y} was {_days(gap)} "
        f"(< {DRY_SPELL_DAYS}); earlier commits were only partly read"
    )


def score(profile: Profile) -> ScoreResult:
    evidence: list[Evidence] = []
    if profile.commit_activity_scope == "own_recent_repos":
        evidence.append(
            Evidence(
                signal="commit_activity_scope",
                detail=(
                    "Counted from the 5 most recently pushed own repositories only: "
                    "GitHub didn't return activity across all repositories"
                ),
                weight=0,
            )
        )
    points = 0

    now = datetime.now(UTC)
    # Ingestion collects two years of commit days because Learning Trajectory
    # compares the last year with the one before it. Every rule here is about
    # the last year only.
    year_ago = now - ONE_YEAR
    dates = sorted(d for d in map(_aware, profile.commit_dates) if d > year_ago)
    if not dates:
        return make_result(points=0, max_points=MAX_POINTS, evidence=evidence)

    # 1. At least one commit in each of last 3 calendar months -> 4 pts
    last_3_months: list[tuple[int, int]] = []
    for i in range(3):
        m = now.month - i
        y = now.year
        while m <= 0:
            m += 12
            y -= 1
        last_3_months.append((y, m))

    hit_months = {(d.year, d.month) for d in dates} & set(last_3_months)
    if len(hit_months) >= 3:
        evidence.append(
            Evidence(
                signal="active_cadence",
                detail="Committed in each of the last 3 months",
                weight=4,
            )
        )
        points += 4

    # 2. No dry spell (a 60-day gap) over the last year -> 3 pts
    dry_spell = _dry_spell_evidence(profile, dates, year_ago, now)
    if dry_spell is not None:
        evidence.append(Evidence(signal="low_dry_spell", detail=dry_spell, weight=3))
        points += 3

    # 3. >= 30 commit days over the last 12 months -> 3 pts
    if len(dates) >= 30:
        where = (
            " across public repositories"
            if profile.commit_activity_scope == "all_public_repos"
            else ""
        )
        # Days before a cut-off page's oldest went unread: the count is a floor.
        complete_since = profile.commit_history_complete_since
        floor = (
            "at least " if complete_since is not None and _aware(complete_since) > year_ago else ""
        )
        evidence.append(
            Evidence(
                signal="high_volume",
                detail=f"Committed on {floor}{len(dates)} days in the last year{where}",
                weight=3,
            )
        )
        points += 3

    if profile.cross_repo_contribution_count and profile.cross_repo_contribution_count >= 5:
        evidence.append(
            Evidence(
                signal="cross_repo_breadth",
                detail=(
                    f"Contributed substantially to {profile.cross_repo_contribution_count} "
                    "different repos in the last year"
                ),
                weight=0,
            )
        )

    return make_result(points=points, max_points=MAX_POINTS, evidence=evidence)
