import re
from urllib.parse import urlsplit

from app.models import Evidence, Profile, ScoreResult
from app.scoring.base import make_result

MAX_POINTS = 15

# What a hiring manager sees in the first seconds on a profile (rebalanced
# 2026-10-13, approved by Shaan): a written profile README, curated pins and a
# bio, a way to reach the person, one project people use, and GitHub's own
# recognition. PLAN v0.1.0 intended the first three; they were fetched but
# never scored.
_README_MIN_CHARS = 200  # visible text; GitHub's starter template is mostly a comment
_MIN_PINS = 3
_POPULAR_STARS = 50


def score(profile: Profile) -> ScoreResult:
    evidence: list[Evidence] = []

    if profile.profile_readme_chars >= _README_MIN_CHARS:
        evidence.append(
            Evidence(
                signal="profile_readme",
                detail=f"Profile README with {profile.profile_readme_chars} characters of content",
                weight=3,
            )
        )

    if profile.pinned_count >= _MIN_PINS:
        evidence.append(
            Evidence(
                signal="curated_pins",
                detail=f"Pins {profile.pinned_count} repositories to the profile",
                weight=3,
            )
        )

    # Free text: only its presence is evidence, never its content, because
    # evidence goes into the narrator's prompt.
    if profile.bio and profile.bio.strip():
        evidence.append(Evidence(signal="bio", detail="Profile bio filled in", weight=2))

    if profile.blog or profile.hireable:
        if profile.blog:
            host = _website_host(profile.blog)
            detail = f"Portfolio/website linked: {host}" if host else "Portfolio/website linked"
        else:
            detail = "Marked as hireable"
        evidence.append(Evidence(signal="professional_presence", detail=detail, weight=2))

    top_stars = max((r.stars for r in profile.repos), default=0)
    if top_stars > _POPULAR_STARS:
        evidence.append(
            Evidence(
                signal="popular_repo",
                detail=f"Top repository has {top_stars} stars (> {_POPULAR_STARS})",
                weight=3,
            )
        )

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
        evidence.append(Evidence(signal="pro_verification", detail=pro_detail, weight=2))

    return make_result(
        points=sum(e.weight for e in evidence), max_points=MAX_POINTS, evidence=evidence
    )


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
