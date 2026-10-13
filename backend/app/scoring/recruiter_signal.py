import re
from urllib.parse import urlsplit

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

    # 2. A GitHub recognition, or an organization named on the profile -> 5 pts.
    # The strongest true reason is the one stated. The company field is free
    # text GitHub never checks, so it is described, not called "verified".
    if profile.is_github_star:
        pro_detail = "GitHub Star recipient"
    elif profile.has_sponsors_listing:
        pro_detail = "GitHub Sponsors enabled"
    elif profile.is_developer_program_member:
        pro_detail = "GitHub Developer Program member"
    elif profile.company and profile.company.startswith("@"):
        pro_detail = "Names an @organization in the profile's company field"
    else:
        pro_detail = None
    if pro_detail:
        evidence.append(Evidence(signal="pro_verification", detail=pro_detail, weight=5))
        points += 5

    # 3. Profile has a website URL linked or marked as hireable -> 5 pts
    if profile.blog or profile.hireable:
        if profile.blog:
            host = _website_host(profile.blog)
            detail = f"Portfolio/website linked: {host}" if host else "Portfolio/website linked"
        else:
            detail = "Marked as hireable"
        evidence.append(Evidence(signal="professional_presence", detail=detail, weight=5))
        points += 5

    return make_result(points=points, max_points=MAX_POINTS, evidence=evidence)


_HOSTNAME = re.compile(r"^(?=.{1,253}$)[a-z0-9-]+(\.[a-z0-9-]+)+$")


def _website_host(website: str) -> str | None:
    """The hostname of the profile's website, or None when it isn't one.

    The field is free text and evidence goes into the narrator's prompt, so
    only a well-formed hostname ever leaves this function.
    """
    candidate = website.strip()
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    try:
        host = (urlsplit(candidate).hostname or "").lower()
    except ValueError:
        return None
    return host if _HOSTNAME.match(host) else None
