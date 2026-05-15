from app.models import Evidence, Profile, ScoreResult
from app.scoring.base import make_result

MAX_POINTS = 15


def score(profile: Profile) -> ScoreResult:
    evidence: list[Evidence] = []
    points = 0

    # `external_prs_merged >= 1` -> 5 pts; `>= 10` -> 5 more pts (total 10)
    if profile.external_prs_merged >= 1:
        pr_points = 5
        if profile.external_prs_merged >= 10:
            pr_points += 5
        evidence.append(
            Evidence(
                signal="oss_contributions",
                detail=f"Merged {profile.external_prs_merged} pull requests into external repositories",
                weight=pr_points,
            )
        )
        points += pr_points

    # `external_reviews >= 1` -> 3 pts
    if profile.external_reviews >= 1:
        evidence.append(
            Evidence(
                signal="code_review",
                detail=f"Reviewed {profile.external_reviews} external pull requests",
                weight=3,
            )
        )
        points += 3

    # Cross-org diversity: >= 2 distinct orgs in external PRs -> 2 pts
    if len(profile.external_orgs) >= 2:
        evidence.append(
            Evidence(
                signal="org_diversity",
                detail=f"Collaborated across {len(profile.external_orgs)} distinct organizations",
                weight=2,
            )
        )
        points += 2

    return make_result(points=points, max_points=MAX_POINTS, evidence=evidence)
