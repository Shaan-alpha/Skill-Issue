from __future__ import annotations

from app.models import TierInfo, TierName

# (lower inclusive, upper exclusive, tier name). Principal's upper is sentinel
# 101 so 100 still falls inside `[90, 101)`.
_BANDS: list[tuple[int, int, TierName]] = [
    (0, 20, "Hobbyist"),
    (20, 35, "Student Builder"),
    (35, 50, "Entry-Level Engineer"),
    (50, 65, "Professional Developer"),
    (65, 80, "Senior Engineer"),
    (80, 90, "Staff Engineer"),
    (90, 101, "Principal Engineer"),
]


def _band_for(total: int) -> tuple[int, int, TierName]:
    for lower, upper, name in _BANDS:
        if lower <= total < upper:
            return lower, upper, name
    raise ValueError(f"total {total} out of [0, 100]")


def assign_tier(total: int) -> TierInfo:
    if not 0 <= total <= 100:
        raise ValueError(f"total must be in [0, 100], got {total}")
    lower, upper, name = _band_for(total)

    # Display band uses inclusive upper for the natural reading.
    display_upper = 100 if name == "Principal Engineer" else upper

    # Sub-rank: where you sit inside the band, 0..100.
    span = display_upper - lower
    sub_rank = round((total - lower) / span * 100) if span else 0

    idx = next(i for i, (_, _, n) in enumerate(_BANDS) if n == name)
    next_name = _BANDS[idx + 1][2] if idx + 1 < len(_BANDS) else None
    prev_name = _BANDS[idx - 1][2] if idx > 0 else None

    pts_to_next = (upper - total) if next_name is not None else None
    pts_above_prev = total - lower

    return TierInfo(
        name=name,
        sub_rank=sub_rank,
        band=(lower, display_upper),
        next_tier=next_name,
        pts_to_next=pts_to_next,
        prev_tier=prev_name,
        pts_above_prev=pts_above_prev,
    )
