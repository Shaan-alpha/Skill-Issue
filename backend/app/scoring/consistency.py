from datetime import UTC, datetime

from app.models import Evidence, Profile, ScoreResult
from app.scoring.base import make_result

MAX_POINTS = 10


def score(profile: Profile) -> ScoreResult:
    evidence: list[Evidence] = []
    points = 0

    dates = sorted(profile.commit_dates)
    if not dates:
        return make_result(points=0, max_points=MAX_POINTS, evidence=[])

    # 1. At least one commit in each of last 3 calendar months -> 4 pts
    now = datetime.now(UTC)
    last_3_months = []
    for i in range(3):
        # Rough month calculation
        m = now.month - i
        y = now.year
        while m <= 0:
            m += 12
            y -= 1
        last_3_months.append((y, m))

    hit_months = set()
    for d_str in dates:
        dt = datetime.strptime(d_str, "%Y-%m-%d").replace(tzinfo=UTC)
        for y, m in last_3_months:
            if dt.year == y and dt.month == m:
                hit_months.add((y, m))

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
    if len(dates) >= 1:
        max_gap = 0
        # Check gaps between commits
        for i in range(len(dates) - 1):
            d1 = datetime.strptime(dates[i], "%Y-%m-%d").replace(tzinfo=UTC)
            d2 = datetime.strptime(dates[i + 1], "%Y-%m-%d").replace(tzinfo=UTC)
            gap = (d2 - d1).days
            if gap > max_gap:
                max_gap = gap

        # Also check gap between last commit and today
        last_commit = datetime.strptime(dates[-1], "%Y-%m-%d").replace(tzinfo=UTC)
        gap_to_now = (now - last_commit).days
        if gap_to_now > max_gap:
            max_gap = gap_to_now

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

    return make_result(points=points, max_points=MAX_POINTS, evidence=evidence)
