from datetime import UTC, datetime
from typing import Any

import pytest

from app.github.client import GitHubCallCapExceeded, GitHubRateLimited
from app.ingestion.activity import (
    activity_windows,
    commit_subjects,
    contribution_activity,
    sample_activity,
)

WINDOWS = {
    "from": "2025-10-15T00:00:00+00:00",
    "to": "2026-10-15T00:00:00+00:00",
    "priorFrom": "2024-10-15T00:00:00+00:00",
}


class _GraphQL:
    """A GitHubClient stand-in that answers CommitActivity with one payload."""

    def __init__(self, payload: Any = None, error: Exception | None = None) -> None:
        self.payload, self.error = payload, error
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def graphql(self, query: str, variables: dict[str, object]) -> Any:
        self.calls.append((query, variables))
        if self.error is not None:
            raise self.error
        return self.payload


def _repo(
    *days: str, private: bool = False, total: int | None = None, more: bool = False
) -> dict[str, object]:
    return {
        "repository": {"isPrivate": private},
        "contributions": {
            "totalCount": len(days) if total is None else total,
            "pageInfo": {"hasNextPage": more},
            "nodes": [{"occurredAt": f"{d}T07:00:00Z"} for d in days],
        },
    }


def _payload(last_year: list[Any], prior_year: list[Any] | None = None) -> dict[str, object]:
    user: dict[str, object] = {"lastYear": {"commitContributionsByRepository": last_year}}
    if prior_year is not None:
        user["priorYear"] = {"commitContributionsByRepository": prior_year}
    return {"user": user}


def _day(iso: str) -> datetime:
    return datetime.fromisoformat(iso).replace(tzinfo=UTC)


@pytest.mark.asyncio
async def test_public_commit_days_from_every_repository_count() -> None:
    """Org work counts: gaearon's react/react commits sit in a repo he doesn't own."""
    gh = _GraphQL(
        _payload(
            [_repo("2026-09-03", "2026-09-02"), _repo("2026-08-23")],
            [_repo("2025-06-01")],
        )
    )

    activity = await contribution_activity("gaearon", gh, WINDOWS)

    assert activity is not None
    assert activity.days == {
        _day("2026-09-03"),
        _day("2026-09-02"),
        _day("2026-08-23"),
        _day("2025-06-01"),
    }
    assert activity.scope == "all_public_repos"
    assert gh.calls[0][1] == {"login": "gaearon", **WINDOWS}


@pytest.mark.asyncio
async def test_private_repositories_contribute_nothing() -> None:
    """What a token sees of private repos differs by token; reports are cached
    by username. A repository whose privacy is unknown counts as private."""
    gh = _GraphQL(
        _payload(
            [
                _repo("2026-09-03", private=True, total=50),
                {
                    "repository": {},
                    "contributions": {"nodes": [{"occurredAt": "2026-09-04T07:00:00Z"}]},
                },
            ],
            [_repo("2025-06-01", private=True)],
        )
    )

    activity = await contribution_activity("alice", gh, WINDOWS)

    assert activity is not None
    assert activity.days == frozenset()
    assert activity.substantial_repo_count == 0


@pytest.mark.asyncio
async def test_a_cut_off_page_marks_where_the_history_is_complete() -> None:
    """Nodes come newest first, 100 days per repo. Past a cut-off page, the
    history is complete only from the latest of the cut-off repos' oldest days."""
    gh = _GraphQL(
        _payload(
            [
                _repo("2026-10-10", "2026-06-02", more=True),
                _repo("2026-10-12", "2026-07-01", more=True),
                _repo("2025-11-01"),
            ]
        )
    )

    activity = await contribution_activity("torvalds", gh, WINDOWS)

    assert activity is not None
    assert activity.complete_since == _day("2026-07-01")


@pytest.mark.asyncio
async def test_no_cut_off_page_means_the_history_is_complete() -> None:
    gh = _GraphQL(_payload([_repo("2026-10-10", "2025-11-01")]))

    activity = await contribution_activity("alice", gh, WINDOWS)

    assert activity is not None
    assert activity.complete_since is None


@pytest.mark.asyncio
async def test_substantial_repositories_have_ten_or_more_commits() -> None:
    gh = _GraphQL(
        _payload(
            [
                _repo("2026-09-03", total=263),
                _repo("2026-09-01", total=10),
                _repo("2026-08-01", total=9),
                _repo("2026-08-02", total=50, private=True),
            ]
        )
    )

    activity = await contribution_activity("gaearon", gh, WINDOWS)

    assert activity is not None
    assert activity.substantial_repo_count == 2


@pytest.mark.asyncio
async def test_an_account_with_no_public_commits_has_no_days() -> None:
    gh = _GraphQL(_payload([], []))

    activity = await contribution_activity("newcomer", gh, WINDOWS)

    assert activity is not None
    assert (activity.days, activity.complete_since, activity.substantial_repo_count) == (
        frozenset(),
        None,
        0,
    )
    assert activity.scope == "all_public_repos"


@pytest.mark.asyncio
async def test_malformed_entries_are_skipped() -> None:
    gh = _GraphQL(
        _payload(
            [
                {"repository": None, "contributions": None},
                {"repository": {"isPrivate": False}, "contributions": None},
                {
                    "repository": {"isPrivate": False},
                    "contributions": {
                        "nodes": [{"occurredAt": None}, {"occurredAt": "2026"}, {}, None]
                    },
                },
                _repo("2026-09-03"),
            ]
        )
    )

    activity = await contribution_activity("alice", gh, WINDOWS)

    assert activity is not None
    assert activity.days == {_day("2026-09-03")}


@pytest.mark.asyncio
async def test_a_missing_prior_year_still_uses_the_last_year() -> None:
    gh = _GraphQL(_payload([_repo("2026-09-03")]))

    activity = await contribution_activity("alice", gh, WINDOWS)

    assert activity is not None
    assert activity.days == {_day("2026-09-03")}


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [GitHubRateLimited("limited"), GitHubCallCapExceeded(151, 150)])
async def test_a_rate_limit_or_the_call_cap_fails_the_analysis(error: Exception) -> None:
    with pytest.raises(type(error)):
        await contribution_activity("alice", _GraphQL(error=error), WINDOWS)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "gh",
    [
        _GraphQL(error=RuntimeError("GraphQL error: RESOURCE_LIMITS_EXCEEDED")),
        _GraphQL({}),
        _GraphQL({"user": None}),
        _GraphQL({"user": {"lastYear": None}}),
    ],
    ids=["error", "no-user-key", "null-user", "null-last-year"],
)
async def test_activity_github_cannot_produce_is_none(gh: _GraphQL) -> None:
    """The caller then falls back to the commit sample."""
    assert await contribution_activity("alice", gh, WINDOWS) is None


def test_windows_are_whole_utc_days_ending_tonight() -> None:
    """Whole days keep the query, and so its cache key, the same all day."""
    morning = datetime(2026, 10, 14, 8, 15, 42, 123456, tzinfo=UTC)
    evening = datetime(2026, 10, 14, 19, 3, 7, 654321, tzinfo=UTC)

    assert activity_windows(morning) == activity_windows(evening) == WINDOWS


def _commit(day: str, committed: str | None = None, message: str = "Fix") -> dict[str, object]:
    return {
        "commit": {
            "author": {"date": f"{day}T12:00:00Z"},
            "committer": {"date": f"{committed or day}T12:00:00Z"},
            "message": message,
        }
    }


def test_a_full_sample_page_is_complete_from_its_oldest_committer_day() -> None:
    """GitHub filters and orders a commit list by committer date. A rebased
    commit keeps an older author date, which must not stretch the coverage."""
    page = [_commit(f"2026-{m:02d}-{d:02d}") for m in (5, 6, 7, 8) for d in range(1, 31)][:99]
    page.append(_commit("2026-01-05", committed="2026-08-03"))

    activity = sample_activity([page, [_commit("2026-02-01")]])

    assert activity.complete_since == _day("2026-05-01")
    assert _day("2026-01-05") in activity.days
    assert _day("2026-02-01") in activity.days


def test_short_sample_pages_mean_the_history_is_complete() -> None:
    activity = sample_activity([[_commit("2026-09-01")], []])

    assert activity.complete_since is None
    assert activity.days == {_day("2026-09-01")}
    assert (activity.scope, activity.substantial_repo_count) == ("own_recent_repos", None)


def test_commit_subjects_are_bounded_first_lines() -> None:
    """Commit messages are untrusted text: only a bounded first line is kept."""
    pages = [
        [
            _commit("2026-09-01", message="Add retry budget\n\nLong body"),
            _commit("2026-09-02", message="   "),
            _commit("2026-09-03", message="x" * 600),
        ]
    ]

    assert commit_subjects(pages) == ["Add retry budget", "x" * 500]
