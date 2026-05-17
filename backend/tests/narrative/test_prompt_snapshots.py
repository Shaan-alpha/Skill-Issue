import hashlib
import json
from datetime import UTC, datetime

from app.models import Badge, Report, ScoreBreakdown, ScoreResult, TierInfo
from app.narrative.prompts import build_messages


def _stable_report() -> Report:
    b = ScoreBreakdown(
        repo_quality=ScoreResult(points=25, max_points=30),
        engineering_maturity=ScoreResult(points=15, max_points=20),
        oss_collab=ScoreResult(points=10, max_points=15),
        consistency=ScoreResult(points=8, max_points=10),
        recruiter_signal=ScoreResult(points=12, max_points=15),
        learning_trajectory=ScoreResult(points=8, max_points=10),
    )
    return Report(
        username="snapshot-user",
        tier=TierInfo(
            name="Senior Engineer",
            sub_rank=78,
            band=(65, 80),
            next_tier="Staff Engineer",
            pts_to_next=2,
            prev_tier="Professional Developer",
            pts_above_prev=13,
        ),
        badges=[
            Badge(slug="oss-contributor", name="OSS", evidence="Merged PRs")
        ],
        breakdown=b,
        total=78,
        generated_at=datetime(2026, 5, 16, 12, 0, 0, tzinfo=UTC),
    )


def test_roast_prompt_stable_snapshot() -> None:
    msgs = build_messages("roast", _stable_report())
    dumped = json.dumps(msgs, sort_keys=True, indent=2)
    digest = hashlib.sha256(dumped.encode()).hexdigest()

    assert (
        digest
        == "ecc251618d249cb3906ad1fb18efd8298e59360a374f6e4c0909f74cee4a81fe"
    )


def test_mentor_prompt_stable_snapshot() -> None:
    msgs = build_messages("mentor", _stable_report())
    dumped = json.dumps(msgs, sort_keys=True, indent=2)
    digest = hashlib.sha256(dumped.encode()).hexdigest()

    assert (
        digest
        == "faf30bb04b785dd0ee12e70f331a2964b58afac29883bef9692ce8840bcac996"
    )
