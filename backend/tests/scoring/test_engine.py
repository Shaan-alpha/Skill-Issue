from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.models import Profile
from app.scoring.engine import run_scoring_engine

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _profile(name: str) -> Profile:
    return Profile.model_validate_json((FIXTURES / name).read_text())


@pytest.mark.asyncio
async def test_engine_returns_tier_and_badges_for_student() -> None:
    profile = _profile("profile_student.json")
    gh = AsyncMock()  # never called for Hobbyist/Student tiers
    report = await run_scoring_engine(profile, gh)

    assert report.tier.name in {"Hobbyist", "Student Builder"}
    assert isinstance(report.badges, list)
    assert report.total == report.breakdown.total()
    assert gh.mock_calls == []


@pytest.mark.asyncio
async def test_engine_runs_depth_for_high_scorer() -> None:
    profile = _profile("profile_senior.json")
    profile.repos[0].has_license = True
    gh = AsyncMock()
    gh.get_review_depth.return_value = 200

    report = await run_scoring_engine(profile, gh)

    assert report.tier.name in {"Professional Developer", "Senior Engineer", "Staff Engineer"}
    assert profile.licensed_repos == [profile.repos[0].full_name]
    assert report.total == (
        report.breakdown.repo_quality.points
        + report.breakdown.engineering_maturity.points
        + report.breakdown.oss_collab.points
        + report.breakdown.consistency.points
        + report.breakdown.recruiter_signal.points
        + report.breakdown.learning_trajectory.points
    )


@pytest.mark.asyncio
async def test_a_prolific_licensed_portfolio_earns_licence_majority() -> None:
    """Thirty repos, all licensed: the licence rule must see all thirty."""
    profile = _profile("profile_senior.json")
    template = profile.repos[0]
    profile.repos = [
        template.model_copy(update={"name": f"r{i}", "full_name": f"x/r{i}", "has_license": True})
        for i in range(30)
    ]
    gh = AsyncMock()
    gh.get_review_depth.return_value = None

    report = await run_scoring_engine(profile, gh)

    assert report.tier.name in {"Professional Developer", "Senior Engineer", "Staff Engineer"}
    signals = [e.signal for e in report.breakdown.repo_quality.evidence]
    assert "license_majority" in signals
