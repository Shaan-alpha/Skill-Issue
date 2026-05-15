from datetime import UTC, datetime, timedelta

from app.models import Evidence, Profile, ScoreResult
from app.scoring.base import make_result

MAX_POINTS = 10


def score(profile: Profile) -> ScoreResult:
    evidence: list[Evidence] = []
    points = 0
    now = datetime.now(UTC)

    # 1. Account age > 3 years -> 3 pts
    age_days = (now - profile.account_created_at).days
    if age_days > 365 * 3:
        years = round(age_days / 365, 1)
        evidence.append(
            Evidence(
                signal="account_longevity",
                detail=f"Account age is {years} years (> 3)",
                weight=3,
            )
        )
        points += 3

    # 2. Significant growth in repository count in the last year (+3 repos) -> 3 pts
    one_year_ago = now - timedelta(days=365)
    new_repos = [r for r in profile.repos if not r.is_fork and r.created_at > one_year_ago]
    if len(new_repos) >= 3:
        evidence.append(
            Evidence(
                signal="repo_growth",
                detail=f"Created {len(new_repos)} new repositories in the last 12 months",
                weight=3,
            )
        )
        points += 3

    # 3. Consistent year-over-year commit activity (at least some commits in each of last 2 years) -> 4 pts
    two_years_ago = now - timedelta(days=730)

    y1_commits = 0
    y2_commits = 0
    for d in profile.commit_dates:
        # Pydantic parsed them as datetime
        if d > one_year_ago:
            y1_commits += 1
        elif d > two_years_ago:
            y2_commits += 1

    if y1_commits > 0 and y2_commits > 0:
        evidence.append(
            Evidence(
                signal="yoy_activity",
                detail="Maintained commit activity across the last 2 consecutive years",
                weight=4,
            )
        )
        points += 4

    return make_result(points=points, max_points=MAX_POINTS, evidence=evidence)
