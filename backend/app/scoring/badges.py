from collections.abc import Callable

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


# Each detector returns Badge | None. compute_badges runs them all and filters.
# Detectors are registered in Tasks 3-5.
_DETECTORS: list[Callable[[Profile, ScoreBreakdown], Badge | None]] = [
    _oss_contributor,
    _pr_master,
    _maintainer,
    _star_magnet,
    _polyglot,
]


def compute_badges(profile: Profile, breakdown: ScoreBreakdown) -> list[Badge]:
    earned: list[Badge] = []
    for det in _DETECTORS:
        result = det(profile, breakdown)
        if result is not None:
            earned.append(result)
    return earned
