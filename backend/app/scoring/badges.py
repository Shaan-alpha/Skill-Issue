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


# Each detector returns Badge | None. compute_badges runs them all and filters.
# Detectors are registered in Tasks 3-5.
_DETECTORS: list[Callable[[Profile, ScoreBreakdown], Badge | None]] = [
    _oss_contributor,
    _pr_master,
    _maintainer,
]


def compute_badges(profile: Profile, breakdown: ScoreBreakdown) -> list[Badge]:
    earned: list[Badge] = []
    for det in _DETECTORS:
        result = det(profile, breakdown)
        if result is not None:
            earned.append(result)
    return earned
