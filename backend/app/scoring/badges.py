from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from app.models import Badge, Profile, ScoreBreakdown


def _oss_contributor(profile: Profile, _: ScoreBreakdown) -> Badge | None:
    if profile.external_prs_merged < 10:
        return None
    return Badge(
        slug="oss-contributor",
        name="OSS Contributor",
        evidence=f"Merged {profile.external_prs_merged} external PRs across {len(profile.external_orgs)} orgs",
    )


def _pr_master(profile: Profile, _: ScoreBreakdown) -> Badge | None:
    if profile.external_prs_merged < 50:
        return None
    return Badge(
        slug="pr-master",
        name="PR Master",
        evidence=f"{profile.external_prs_merged} external PRs merged (top-decile volume)",
    )


def _maintainer(profile: Profile, _: ScoreBreakdown) -> Badge | None:
    if profile.external_reviews < 25:
        return None
    return Badge(
        slug="maintainer",
        name="Maintainer",
        evidence=f"Reviewed {profile.external_reviews} external PRs",
    )


def _star_magnet(profile: Profile, _: ScoreBreakdown) -> Badge | None:
    top = max((r for r in profile.repos if not r.is_fork), key=lambda r: r.stars, default=None)
    if top is None or top.stars < 1000:
        return None
    return Badge(
        slug="star-magnet",
        name="Star Magnet",
        evidence=f"{top.full_name} has {top.stars} stars",
    )


def _polyglot(profile: Profile, _: ScoreBreakdown) -> Badge | None:
    total_bytes = sum(profile.languages.values())
    if total_bytes == 0:
        return None
    significant = [lang for lang, b in profile.languages.items() if b / total_bytes >= 0.05]
    if len(significant) < 4:
        return None
    return Badge(
        slug="polyglot",
        name="Polyglot",
        evidence=f"Significant in {len(significant)} languages: {', '.join(sorted(significant))}",
    )


def _long_haul(profile: Profile, _: ScoreBreakdown) -> Badge | None:
    now = datetime.now(UTC)
    age_years = (now - profile.account_created_at).days / 365
    if age_years < 8:
        return None
    one_year_ago = now - timedelta(days=365)
    recent = any(
        (d if d.tzinfo else d.replace(tzinfo=UTC)) > one_year_ago for d in profile.commit_dates
    )
    if not recent:
        return None
    return Badge(
        slug="long-haul",
        name="Long-haul",
        evidence=f"Active for {age_years:.1f} years, still committing",
    )


def _indie_hacker(profile: Profile, breakdown: ScoreBreakdown) -> Badge | None:
    if breakdown.consistency.points < 8:
        return None
    if not profile.blog:
        return None
    if profile.hireable:
        return None
    if profile.company:
        return None
    return Badge(
        slug="indie-hacker",
        name="Indie Hacker",
        evidence="Consistent solo shipper with a public portfolio",
    )


def _toolmaker(profile: Profile, _: ScoreBreakdown) -> Badge | None:
    qualifying = [r for r in profile.repos if not r.is_fork and r.stars >= 200]
    if len(qualifying) < 2:
        return None
    names = ", ".join(r.full_name for r in sorted(qualifying, key=lambda r: -r.stars)[:3])
    return Badge(
        slug="toolmaker",
        name="Toolmaker",
        evidence=f"{len(qualifying)} repos with ≥200 stars: {names}",
    )


# Each detector returns Badge | None. compute_badges runs them all and filters.
# Detectors are registered in Tasks 3-5.
_DETECTORS: list[Callable[[Profile, ScoreBreakdown], Badge | None]] = [
    _oss_contributor,
    _pr_master,
    _maintainer,
    _star_magnet,
    _polyglot,
    _long_haul,
    _indie_hacker,
    _toolmaker,
]


def compute_badges(profile: Profile, breakdown: ScoreBreakdown) -> list[Badge]:
    earned: list[Badge] = []
    for det in _DETECTORS:
        result = det(profile, breakdown)
        if result is not None:
            earned.append(result)
    return earned
