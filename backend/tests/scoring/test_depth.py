import asyncio
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
    assert profile.review_avg_comments is None
    gh.get_license.assert_not_called()
    gh.list_workflow_files.assert_not_called()


@pytest.mark.asyncio
async def test_professional_tier_reads_licenses() -> None:
    profile = _bare_profile()
    gh = AsyncMock()
    gh.get_license.return_value = "MIT"

    await enrich_for_tier(profile, "Professional Developer", gh)

    assert profile.licensed_repos == ["alice/a"]
    gh.get_review_depth.assert_not_called()
    gh.get_contribution_repo_count.assert_not_called()


@pytest.mark.asyncio
async def test_depth_keeps_the_workflow_counts_ingestion_already_found() -> None:
    """Ingestion counts every repo's workflow files in one GraphQL probe, so the
    old per-repo `.github/workflows` listing (one call each for the top ten)
    would only repeat the work, and overwrite the result."""
    profile = _bare_profile()
    profile.workflow_counts = {"alice/a": 2}
    gh = AsyncMock()
    gh.get_license.return_value = None

    await enrich_for_tier(profile, "Staff Engineer", gh)

    assert profile.workflow_counts == {"alice/a": 2}
    gh.list_workflow_files.assert_not_called()


@pytest.mark.asyncio
async def test_senior_tier_adds_review_depth() -> None:
    profile = _bare_profile()
    gh = AsyncMock()
    gh.get_license.return_value = None
    gh.get_review_depth.return_value = 250

    await enrich_for_tier(profile, "Senior Engineer", gh)

    assert profile.review_avg_comments == 250
    gh.get_contribution_repo_count.assert_not_called()


@pytest.mark.asyncio
async def test_staff_tier_adds_cross_repo_breadth() -> None:
    profile = _bare_profile()
    gh = AsyncMock()
    gh.get_license.return_value = None
    gh.get_review_depth.return_value = None
    gh.get_contribution_repo_count.return_value = 12

    await enrich_for_tier(profile, "Staff Engineer", gh)

    assert profile.cross_repo_contribution_count == 12


class _OverlapFake:
    """Depth-enrichment GitHub double recording which reads were in flight together."""

    def __init__(self) -> None:
        self.in_flight: list[str] = []
        self.pairs: set[frozenset[str]] = set()

    async def _call(self, name: str, result: object) -> object:
        self.pairs.update(frozenset((name, other)) for other in self.in_flight if other != name)
        self.in_flight.append(name)
        try:
            await asyncio.sleep(0.005)
            return result
        finally:
            self.in_flight.remove(name)

    def ran_together(self, a: str, b: str) -> bool:
        return frozenset((a, b)) in self.pairs

    async def get_license(self, owner: str, name: str) -> object:
        return await self._call("license", None)

    async def get_review_depth(self, username: str) -> object:
        return await self._call("review_depth", None)

    async def get_contribution_repo_count(self, username: str, *, min_commits: int) -> object:
        return await self._call("contribution_repos", 0)


@pytest.mark.asyncio
async def test_unlocked_tiers_enrich_concurrently() -> None:
    """Each tier's reads are independent of the others', so a Staff-tier
    profile shouldn't wait for the Professional reads before starting the
    Senior and Staff ones."""
    profile = _bare_profile()
    gh = _OverlapFake()

    await enrich_for_tier(profile, "Staff Engineer", gh)

    assert gh.ran_together("license", "review_depth")
    assert gh.ran_together("review_depth", "contribution_repos")
    assert gh.ran_together("license", "contribution_repos")


@pytest.mark.asyncio
async def test_depth_spends_no_calls_on_data_ingestion_already_has() -> None:
    """README size, manifests and commit subjects come from ingestion's own
    reads now: ten README downloads, five root listings and five commit
    samples per Staff-tier analysis were spent on nothing."""
    profile = _bare_profile()
    gh = AsyncMock()
    gh.get_license.return_value = None
    gh.get_review_depth.return_value = None
    gh.get_contribution_repo_count.return_value = 0

    await enrich_for_tier(profile, "Staff Engineer", gh)

    gh.get_repo_readme_text.assert_not_called()
    gh.get_repo_root_contents.assert_not_called()
    gh.list_recent_commits_sample.assert_not_called()
