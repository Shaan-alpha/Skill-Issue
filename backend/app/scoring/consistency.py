from datetime import UTC, datetime

from app.models import Evidence, Profile, ScoreResult
from app.scoring.base import make_result

MAX_POINTS = 10


def score(profile: Profile) -> ScoreResult:
    evidence: list[Evidence] = []
    points = 0

    # Defensive: ingestion stores tz-aware UTC datetimes, but tests may
    # construct profiles with naive datetimes — coerce so date math stays safe.
    dates = sorted(d if d.tzinfo else d.replace(tzinfo=UTC) for d in profile.commit_dates)
    if not dates:
        return make_result(points=0, max_points=MAX_POINTS, evidence=[])

    now = datetime.now(UTC)

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

    # 2. Longest dry spell over the last year < 60 days -> 3 pts
    max_gap = 0
    for i in range(len(dates) - 1):
        gap = (dates[i + 1] - dates[i]).days
        max_gap = max(max_gap, gap)
    gap_to_now = (now - dates[-1]).days
    max_gap = max(max_gap, gap_to_now)

    if max_gap < 60:
        evidence.append(
            Evidence(
                signal="low_dry_spell",
                detail=f"Longest gap between commits was {max_gap} days (< 60)",
                weight=3,
            )
        )
        points += 3

    # 3. >= 30 commits over the last 12 months -> 3 pts
    if len(dates) >= 30:
        evidence.append(
            Evidence(
                signal="high_volume",
                detail=f"Total of {len(dates)} commit days in the last year",
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
