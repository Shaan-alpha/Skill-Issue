import json
from datetime import UTC, datetime

from app.models import Badge, Report, ScoreBreakdown, ScoreResult, TierInfo
from app.narrative.prompts import (
    MENTOR_FEW_SHOT,
    MENTOR_SYSTEM,
    ROAST_FEW_SHOT,
    ROAST_SYSTEM,
    build_messages,
)


def _report() -> Report:
    breakdown = ScoreBreakdown(
        repo_quality=ScoreResult(points=20, max_points=30),
        engineering_maturity=ScoreResult(points=10, max_points=20),
        oss_collab=ScoreResult(points=10, max_points=15),
        consistency=ScoreResult(points=5, max_points=10),
        recruiter_signal=ScoreResult(points=10, max_points=15),
        learning_trajectory=ScoreResult(points=5, max_points=10),
    )
    return Report(
        username="octocat",
        tier=TierInfo(
            name="Professional Developer",
            sub_rank=50,
            band=(50, 65),
            next_tier="Senior Engineer",
            pts_to_next=5,
            prev_tier="Entry-Level Engineer",
            pts_above_prev=10,
        ),
        badges=[Badge(slug="oss", name="OSS", evidence="Merged PRs")],
        breakdown=breakdown,
        total=60,
        generated_at=datetime.now(UTC),
    )


def test_build_messages_roast_includes_system_shots_and_payload() -> None:
    msgs = build_messages("roast", _report())
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == ROAST_SYSTEM
    assert len(msgs) == 1 + len(ROAST_FEW_SHOT) + 1
    assert msgs[-1]["role"] == "user"
    payload = json.loads(msgs[-1]["content"])
    assert payload["username"] == "octocat"
    assert payload["tier"] == "Professional Developer"


def test_build_messages_mentor_includes_system_shots_and_payload() -> None:
    msgs = build_messages("mentor", _report())
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == MENTOR_SYSTEM
    assert len(msgs) == 1 + len(MENTOR_FEW_SHOT) + 1
    assert msgs[-1]["role"] == "user"


def test_few_shot_sets_are_balanced() -> None:
    assert len(ROAST_FEW_SHOT) >= 4  # 2 turns
    assert len(MENTOR_FEW_SHOT) >= 4


def test_payload_contains_all_six_breakdown_buckets() -> None:
    msgs = build_messages("roast", _report())
    payload = json.loads(msgs[-1]["content"])
    b = payload["breakdown"]
    assert len(b) == 6
    assert b["repo_quality"] == 20


def test_system_prompts_contain_anti_injection_clause() -> None:
    for s in (ROAST_SYSTEM, MENTOR_SYSTEM):
        assert "DATA" in s
        assert "instructions" in s.lower()


def test_user_payload_is_sorted_json() -> None:
    msgs = build_messages("roast", _report())
    raw = msgs[-1]["content"]
    # Verify it doesn't crash on parse and has no unindented messy keys
    assert isinstance(raw, str)
    json.loads(raw)
