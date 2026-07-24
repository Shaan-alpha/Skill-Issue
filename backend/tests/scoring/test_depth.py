from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.models import Profile, Repo
from app.scoring.depth import enrich_for_tier


def _bare_profile() -> Profile:
    return Profile(
        username="alice",
        bio=None,
        profile_readme_chars=0,
        followers=0,
        public_repos=2,
        languages={},
        repos=[
            Repo(
                name="a",
                full_name="alice/a",
                primary_language="Python",
                stars=10,
                forks=0,
                is_fork=False,
                has_readme=True,
                has_tests=False,
                has_ci=True,
                deployment_hints=[],
                size_kb=100,
                last_commit_at=None,
                created_at=datetime.now(UTC),
            ),
        ],
        external_prs_merged=0,
        external_reviews=0,
        commit_dates=[],
        account_created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_hobbyist_tier_does_no_enrichment() -> None:
    profile = _bare_profile()
    gh = AsyncMock()
    await enrich_for_tier(profile, "Hobbyist", gh)
    assert profile.licensed_repos == []
    assert profile.workflow_counts == {}
    assert profile.readme_lengths == {}
    assert profile.review_avg_comments is None
    gh.get_license.assert_not_called()
    gh.list_workflow_files.assert_not_called()


@pytest.mark.asyncio
async def test_professional_tier_runs_license_workflow_readme() -> None:
    profile = _bare_profile()
    gh = AsyncMock()
    gh.get_license.return_value = "MIT"
    gh.list_workflow_files.return_value = ["ci.yml", "release.yml"]
    gh.get_repo_readme_text.return_value = "# README\n\n## Setup\n\n## Usage\n"

    await enrich_for_tier(profile, "Professional Developer", gh)

    assert "alice/a" in profile.licensed_repos
    assert profile.workflow_counts.get("alice/a") == 2
    assert profile.readme_lengths.get("alice/a", 0) > 0
    gh.get_review_depth.assert_not_called()
    gh.get_contribution_repo_count.assert_not_called()


@pytest.mark.asyncio
async def test_senior_tier_adds_review_depth_and_dep_files() -> None:
    profile = _bare_profile()
    gh = AsyncMock()
    gh.get_license.return_value = None
    gh.list_workflow_files.return_value = []
    gh.get_repo_readme_text.return_value = ""
    gh.get_review_depth.return_value = 250
    gh.get_repo_root_contents.return_value = ["package.json", "src", "Dockerfile"]

    await enrich_for_tier(profile, "Senior Engineer", gh)

    assert profile.review_avg_comments == 250
    assert "package.json" in profile.dep_files.get("alice/a", [])


@pytest.mark.asyncio
async def test_staff_tier_adds_commit_quality_and_cross_repo() -> None:
    profile = _bare_profile()
    gh = AsyncMock()
    gh.get_license.return_value = None
    gh.list_workflow_files.return_value = []
    gh.get_repo_readme_text.return_value = ""
    gh.get_review_depth.return_value = None
    gh.get_repo_root_contents.return_value = []
    gh.list_recent_commits_sample.return_value = [
        "feat: add thing",
        "fix: handle null",
        "wip",
    ]
    gh.get_contribution_repo_count.return_value = 12

    await enrich_for_tier(profile, "Staff Engineer", gh)

    assert isinstance(profile.commit_message_quality, int)
    assert 0 <= profile.commit_message_quality <= 100
    assert profile.cross_repo_contribution_count == 12


def test_commit_message_quality_bounds_and_edge_cases() -> None:
    from app.scoring.depth import _commit_message_quality

    assert _commit_message_quality(["feat: add thing"]) == 100  # conventional
    assert _commit_message_quality(["x" * 60]) == 100  # long first line
    assert _commit_message_quality([""]) == 0  # empty must not IndexError
    # Pathological long/scope message: no crash, bounded processing.
    huge = "feat(" + "a" * 10_000 + "): " + "z" * 100_000
    assert isinstance(_commit_message_quality([huge]), int)
