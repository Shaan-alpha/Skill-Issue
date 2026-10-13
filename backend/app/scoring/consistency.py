from datetime import UTC, datetime, timedelta
from itertools import pairwise

from app.models import Evidence, Profile, ScoreResult
from app.scoring.base import make_result

MAX_POINTS = 10
ONE_YEAR = timedelta(days=365)


def _aware(d: datetime) -> datetime:
    # Defensive: ingestion stores tz-aware UTC datetimes, but tests may
    # construct profiles with naive datetimes — coerce so date math stays safe.
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def score(profile: Profile) -> ScoreResult:
    evidence: list[Evidence] = []
    points = 0

    now = datetime.now(UTC)
    # Ingestion collects two years of commit days because Learning Trajectory
    # compares the last year with the one before it. Every rule here is about
    # the last year only.
    year_ago = now - ONE_YEAR
    dates = sorted(d for d in map(_aware, profile.commit_dates) if d > year_ago)
    if not dates:
        return make_result(points=0, max_points=MAX_POINTS, evidence=[])

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

    # 2. Longest dry spell over the last year < 60 days -> 3 pts. The silence
    # before the first commit counts too, measured from the start of the window
    # or from account creation, whichever is later: a dry spell cannot predate
    # the account. Where a repo's commit page came back full, its older commits
    # went unseen, so only the stretch from that point on is judged.
    window_start = max(year_ago, _aware(profile.account_created_at))
    if profile.commit_history_complete_since is not None:
        window_start = max(window_start, _aware(profile.commit_history_complete_since))
    boundaries = [window_start, *(d for d in dates if d >= window_start), now]
    max_gap = max(max((later - earlier).days, 0) for earlier, later in pairwise(boundaries))

    if max_gap < 60:
        evidence.append(
            Evidence(
                signal="low_dry_spell",
                detail=f"Longest gap between commits was {max_gap} days (< 60)",
                weight=3,
            )
        )
        points += 3

    # 3. >= 30 commit days over the last 12 months -> 3 pts
    if len(dates) >= 30:
        evidence.append(
            Evidence(
                signal="high_volume",
                detail=f"Committed on {len(dates)} days in the last year",
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
