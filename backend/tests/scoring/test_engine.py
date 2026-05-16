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
    gh.get_license.assert_not_called()


@pytest.mark.asyncio
async def test_engine_runs_depth_for_high_scorer() -> None:
    profile = _profile("profile_senior.json")
    gh = AsyncMock()
    gh.get_license.return_value = "MIT"
    gh.list_workflow_files.return_value = ["ci.yml"]
    gh.get_repo_readme_text.return_value = "# README\n## Setup"
    gh.get_review_depth.return_value = 200
    gh.get_repo_root_contents.return_value = ["pyproject.toml"]
    gh.list_recent_commits_sample.return_value = ["feat: add foo"]
    gh.get_contribution_repo_count.return_value = 10

    report = await run_scoring_engine(profile, gh)

    assert report.tier.name in {"Professional Developer", "Senior Engineer", "Staff Engineer"}
    gh.get_license.assert_called()
    assert report.total == (
        report.breakdown.repo_quality.points
        + report.breakdown.engineering_maturity.points
        + report.breakdown.oss_collab.points
        + report.breakdown.consistency.points
        + report.breakdown.recruiter_signal.points
        + report.breakdown.learning_trajectory.points
    )
