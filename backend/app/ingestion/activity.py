"""Commit activity: the days a user committed on, for Consistency and
Learning Trajectory.

GitHub's contribution data covers every repository the user committed to,
their organisations' included. Private repositories are left out: what a
token can see of them differs from token to token, and reports are cached by
username alone.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, NamedTuple

from app.github.client import GitHubCallCapExceeded, GitHubRateLimited
from app.github.queries import COMMIT_ACTIVITY

if TYPE_CHECKING:
    from app.github.client import GitHubClient
    from app.models import CommitActivityScope

logger = logging.getLogger(__name__)

# Commits in a repository for it to count toward cross-repo breadth (Staff+).
SUBSTANTIAL_COMMITS = 10


class CommitActivity(NamedTuple):
    days: frozenset[datetime]
    # Every commit day after this is visible; None when nothing was cut off.
    complete_since: datetime | None
    substantial_repo_count: int | None
    scope: CommitActivityScope


def activity_windows(now: datetime) -> dict[str, str]:
    """The query's windows, in whole UTC days so its cache key holds all day:
    the 365 days up to tonight's midnight, and the 365 days before them."""
    to = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    start = to - timedelta(days=365)
    return {
        "from": start.isoformat(),
        "to": to.isoformat(),
        "priorFrom": (start - timedelta(days=365)).isoformat(),
    }


def _day(node: Any) -> datetime | None:
    occurred = str(node.get("occurredAt") or "") if isinstance(node, dict) else ""
    try:
        return datetime.strptime(occurred[:10], "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError:
        return None


def _public(entries: Any) -> list[dict[str, Any]]:
    # A repository whose privacy is unknown is treated as private.
    return [
        entry
        for entry in entries or []
        if isinstance(entry, dict)
        and isinstance(entry.get("repository"), dict)
        and entry["repository"].get("isPrivate") is False
    ]


def _days(connection: dict[str, Any]) -> list[datetime]:
    return [d for d in map(_day, connection.get("nodes") or []) if d is not None]


async def contribution_activity(
    login: str, gh: GitHubClient, windows: dict[str, str]
) -> CommitActivity | None:
    """Public commit days from GitHub's contribution data, or None when GitHub
    can't produce them; the caller then falls back to the commit sample. A rate
    limit or the call cap still fails the analysis."""
    try:
        data = await gh.graphql(COMMIT_ACTIVITY, {"login": login, **windows})
    except (GitHubRateLimited, GitHubCallCapExceeded):
        raise
    except Exception:
        logger.warning(
            "Commit activity unavailable for %s; using the commit sample", login, exc_info=True
        )
        return None
    user = (data or {}).get("user") or {}
    last_year = user.get("lastYear")
    if not last_year:
        logger.warning("Commit activity for %s came back empty; using the commit sample", login)
        return None

    days: set[datetime] = set()
    complete_since: datetime | None = None
    substantial = 0
    for entry in _public(last_year.get("commitContributionsByRepository")):
        connection = entry.get("contributions") or {}
        repo_days = _days(connection)
        days.update(repo_days)
        if (connection.get("totalCount") or 0) >= SUBSTANTIAL_COMMITS:
            substantial += 1
        # A further page holds older days that were not read.
        if (connection.get("pageInfo") or {}).get("hasNextPage") and repo_days:
            oldest = min(repo_days)
            complete_since = oldest if complete_since is None else max(complete_since, oldest)
    for entry in _public((user.get("priorYear") or {}).get("commitContributionsByRepository")):
        days.update(_days(entry.get("contributions") or {}))
    return CommitActivity(frozenset(days), complete_since, substantial, "all_public_repos")
