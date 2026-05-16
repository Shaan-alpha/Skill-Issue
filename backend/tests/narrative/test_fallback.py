from datetime import UTC, datetime

from app.models import (
    Badge,
    Report,
    ScoreBreakdown,
    ScoreResult,
    TierInfo,
)
from app.narrative.fallback import fallback_narrative


def _sample_report(tier_name: str, total: int, badges: list[str]) -> Report:
    z = ScoreResult(points=0, max_points=1)
    breakdown = ScoreBreakdown(
        repo_quality=ScoreResult(points=total - 10, max_points=30),
        engineering_maturity=ScoreResult(points=5, max_points=20),
        oss_collab=ScoreResult(points=5, max_points=15),
        consistency=z,
        recruiter_signal=z,
        learning_trajectory=z,
    )
    return Report(
        username="testuser",
        tier=TierInfo(
            name=tier_name,
            sub_rank=0,
            band=(0, 100),
            next_tier=None,
            pts_to_next=10,
            prev_tier=None,
            pts_above_prev=0,
        ),
        badges=[Badge(slug=b, name=b, evidence="x") for b in badges],
        breakdown=breakdown,
        total=total,
        generated_at=datetime.now(UTC),
    )


def test_roast_fallback_embeds_real_metrics() -> None:
    rep = _sample_report("Senior Engineer", 72, ["oss-contributor", "star-magnet"])
    res = fallback_narrative("roast", rep)
    assert "72" in res
    assert "Senior Engineer" in res
    assert "2 badges" in res.lower()
    assert "offline" in res.lower()


def test_mentor_fallback_embeds_real_metrics() -> None:
    rep = _sample_report("Hobbyist", 15, [])
    res = fallback_narrative("mentor", rep)
    assert "15" in res
    assert "Hobbyist" in res
    assert "0 badges" in res.lower()
    assert "offline" in res.lower()
