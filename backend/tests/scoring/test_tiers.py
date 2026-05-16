import pytest

from app.scoring.tiers import assign_tier

# (total, expected_tier_name, expected_sub_rank, expected_next, expected_pts_to_next)
BOUNDARY_CASES = [
    (0,   "Hobbyist",               0,   "Student Builder",        20),
    (19,  "Hobbyist",               95,  "Student Builder",        1),
    (20,  "Student Builder",        0,   "Entry-Level Engineer",   15),
    (34,  "Student Builder",        93,  "Entry-Level Engineer",   1),
    (35,  "Entry-Level Engineer",   0,   "Professional Developer", 15),
    (50,  "Professional Developer", 0,   "Senior Engineer",        15),
    (64,  "Professional Developer", 93,  "Senior Engineer",        1),
    (65,  "Senior Engineer",        0,   "Staff Engineer",         15),
    (80,  "Staff Engineer",         0,   "Principal Engineer",     10),
    (89,  "Staff Engineer",         90,  "Principal Engineer",     1),
    (90,  "Principal Engineer",     0,   None,                     None),
    (100, "Principal Engineer",     100, None,                     None),
]


@pytest.mark.parametrize("total,name,sub,next_name,pts", BOUNDARY_CASES)
def test_assign_tier_boundaries(
    total: int, name: str, sub: int, next_name: str | None, pts: int | None
) -> None:
    info = assign_tier(total)
    assert info.name == name, f"total={total}"
    assert info.sub_rank == sub, f"total={total}"
    assert info.next_tier == next_name, f"total={total}"
    assert info.pts_to_next == pts, f"total={total}"


def test_assign_tier_band_endpoints() -> None:
    info = assign_tier(72)
    assert info.band == (65, 80)
    assert info.prev_tier == "Professional Developer"
    assert info.pts_above_prev == 7
