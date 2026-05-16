from datetime import UTC, datetime

from app.models import (
    Badge,
    Report,
    ScoreBreakdown,
    ScoreResult,
    TierInfo,
)
from app.narrative.cache import NarrativeCache


def _report(total: int = 65, badge_slugs: list[str] | None = None) -> Report:
    breakdown = ScoreBreakdown(
        repo_quality=ScoreResult(points=total - 35, max_points=30),
        engineering_maturity=ScoreResult(points=10, max_points=20),
        oss_collab=ScoreResult(points=15, max_points=15),
        consistency=ScoreResult(points=3, max_points=10),
        recruiter_signal=ScoreResult(points=5, max_points=15),
        learning_trajectory=ScoreResult(points=2, max_points=10),
    )
    # Force breakdown total to match `total`
    breakdown.repo_quality = ScoreResult(
        points=total
        - sum(
            v.points
            for k, v in breakdown.__dict__.items()
            if k != "repo_quality"
        ),
        max_points=30,
    )
    return Report(
        username="alice",
        tier=TierInfo(
            name="Senior Engineer",
            sub_rank=0,
            band=(65, 80),
            next_tier="Staff Engineer",
            pts_to_next=15,
            prev_tier="Professional Developer",
            pts_above_prev=0,
        ),
        badges=[Badge(slug=s, name=s, evidence="x") for s in (badge_slugs or [])],
        breakdown=breakdown,
        total=total,
        generated_at=datetime.now(UTC),
    )


def test_scores_hash_stable_across_equivalent_reports() -> None:
    h1 = NarrativeCache.scores_hash(_report(total=65, badge_slugs=["a", "b"]))
    h2 = NarrativeCache.scores_hash(_report(total=65, badge_slugs=["b", "a"]))
    assert h1 == h2  # badge order doesn't affect the hash


def test_scores_hash_differs_when_total_changes() -> None:
    h1 = NarrativeCache.scores_hash(_report(total=64))
    h2 = NarrativeCache.scores_hash(_report(total=65))
    assert h1 != h2


def test_get_returns_none_on_miss() -> None:
    c = NarrativeCache(max_entries=4)
    assert c.get("missing-key") is None


def test_put_then_get_roundtrip() -> None:
    c = NarrativeCache(max_entries=4)
    c.put("k", "value")
    assert c.get("k") == "value"


def test_lru_evicts_oldest_on_overflow() -> None:
    c = NarrativeCache(max_entries=2)
    c.put("a", "1")
    c.put("b", "2")
    c.put("c", "3")  # evicts "a"
    assert c.get("a") is None
    assert c.get("b") == "2"
    assert c.get("c") == "3"


def test_get_moves_entry_to_recently_used() -> None:
    c = NarrativeCache(max_entries=2)
    c.put("a", "1")
    c.put("b", "2")
    assert c.get("a") == "1"  # touches "a"; "b" is now LRU
    c.put("c", "3")  # evicts "b"
    assert c.get("a") == "1"
    assert c.get("b") is None
    assert c.get("c") == "3"


def test_key_is_a_string_built_from_three_inputs() -> None:
    k = NarrativeCache.key("alice", "deadbeef", "roast")
    assert isinstance(k, str)
    assert "alice" in k
    assert "deadbeef" in k
    assert "roast" in k
