from app.models import Evidence, Profile, ScoreResult
from app.scoring.base import make_result

MAX_POINTS = 15


def score(profile: Profile) -> ScoreResult:
    evidence: list[Evidence] = []
    points = 0

    # 1. Any repo with > 50 stars -> 5 pts
    top_stars = max((r.stars for r in profile.repos), default=0)
    if top_stars > 50:
        evidence.append(
            Evidence(
                signal="popular_repo",
                detail=f"Top repository has {top_stars} stars (> 50)",
                weight=5,
            )
        )
        points += 5

    # 2. GitHub Sponsors enabled OR verified organization member -> 5 pts
    has_pro_signal = (
        profile.has_sponsors_listing
        or profile.is_github_star
        or profile.is_developer_program_member
        or (profile.company and profile.company.startswith("@"))
    )
    if has_pro_signal:
        detail = "Verified organization or developer program membership"
        if profile.has_sponsors_listing:
            detail = "GitHub Sponsors enabled"
        if profile.is_github_star:
            detail = "GitHub Star recipient"

        evidence.append(Evidence(signal="pro_verification", detail=detail, weight=5))
        points += 5

    # 3. Profile has a website URL linked or marked as hireable -> 5 pts
    if profile.blog or profile.hireable:
        detail = (
            f"Portfolio/Website linked: {profile.blog}" if profile.blog else "Marked as hireable"
        )
        evidence.append(Evidence(signal="professional_presence", detail=detail, weight=5))
        points += 5

    return make_result(points=points, max_points=MAX_POINTS, evidence=evidence)
