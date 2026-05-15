from collections.abc import Callable

from app.models import Badge, Profile, ScoreBreakdown

# Each detector returns Badge | None. compute_badges runs them all and filters.
# Detectors are registered in Tasks 3-5.
_DETECTORS: list[Callable[[Profile, ScoreBreakdown], Badge | None]] = []


def compute_badges(profile: Profile, breakdown: ScoreBreakdown) -> list[Badge]:
    earned: list[Badge] = []
    for det in _DETECTORS:
        result = det(profile, breakdown)
        if result is not None:
            earned.append(result)
    return earned
