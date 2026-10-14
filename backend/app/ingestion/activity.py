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

import sentry_sdk

from app.github.client import GitHubCallCapExceeded, GitHubRateLimited
from app.github.queries import COMMIT_ACTIVITY

if TYPE_CHECKING:
    from app.github.client import GitHubClient
    from app.models import CommitActivityScope

logger = logging.getLogger(__name__)

# Commits in a repository for it to count toward cross-repo breadth (Staff+).
SUBSTANTIAL_COMMITS = 10
# Every fallback groups into one Sentry issue, so one alert rule covers it.
_FALLBACK_FINGERPRINT = ["commit-activity-fallback"]


class CommitActivity(NamedTuple):
    days: frozenset[datetime]
    # Every commit day after this is visible; None when nothing was cut off.
    complete_since: datetime | None
    substantial_repo_count: int | None
    scope: CommitActivityScope


def record_activity_fallback(login: str, reason: str, exc: BaseException | None = None) -> None:
    """Record that commit days came from the commit sample instead of GitHub's
    contribution data. Right for the reader, whose evidence says so; wrong for
    the operator if it keeps happening, so it raises one alertable event.
    Telemetry fails open: reporting must never break the analysis."""
    logger.warning("commit_activity.fallback reason=%s user=%s", reason, login, exc_info=exc)
    try:
        with sentry_sdk.new_scope() as scope:
            # Low-cardinality tag; the username goes in context, not a tag.
            scope.set_tag("commit_activity.fallback_reason", reason)
            scope.set_context("commit_activity", {"username": login, "reason": reason})
            if exc is not None:
                sentry_sdk.capture_exception(exc, level="error", fingerprint=_FALLBACK_FINGERPRINT)
            else:
                sentry_sdk.capture_message(
                    "Commit activity fell back to the commit sample",
                    level="error",
                    fingerprint=_FALLBACK_FINGERPRINT,
                )
    except Exception:  # pragma: no cover - telemetry never breaks an analysis
        logger.exception("commit_activity.fallback: failed to report to Sentry")


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
    except Exception as exc:
        record_activity_fallback(login, "error", exc)
        return None
    user = (data or {}).get("user") or {}
    last_year = user.get("lastYear")
    if not last_year:
        record_activity_fallback(login, "empty")
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


# Commit messages are attacker-influenced; only a bounded prefix is examined.
_COMMIT_SUBJECT_MAX = 500
# One page of the user's commits per sampled repo. A full page means older
# ones exist that ingestion never saw.
COMMITS_PER_REPO = 100


def commit_day(commit: dict[str, Any], role: str = "author") -> datetime | None:
    """The commit's author (or committer) date as a UTC-aware day."""
    date_str = (commit.get(role) or {}).get("date")
    if not date_str:
        return None
    return datetime.strptime(date_str[:10], "%Y-%m-%d").replace(tzinfo=UTC)


def sample_activity(pages: list[list[dict[str, Any]]]) -> CommitActivity:
    """Commit days from the REST sample of the user's own repos: the stand-in
    when GitHub can't report contribution data."""
    days: set[datetime] = set()
    complete_since: datetime | None = None
    for page in pages:
        committed_days: list[datetime] = []
        for c in page:
            commit = c.get("commit") or {}
            day = commit_day(commit)
            if day is not None:
                days.add(day)
            if (committed := commit_day(commit, "committer") or day) is not None:
                committed_days.append(committed)
        # GitHub filters and orders the list by committer date, so a full
        # page's coverage ends at its oldest committer date. A rebased commit
        # keeps an older author date, which would claim coverage further back.
        if len(page) >= COMMITS_PER_REPO and committed_days:
            oldest = min(committed_days)
            complete_since = oldest if complete_since is None else max(complete_since, oldest)
    return CommitActivity(frozenset(days), complete_since, None, "own_recent_repos")


def commit_subjects(pages: list[list[dict[str, Any]]]) -> list[str]:
    """First lines of the sampled commits. Commit messages are untrusted text:
    keep a bounded first line."""
    subjects: list[str] = []
    for page in pages:
        for c in page:
            message = str((c.get("commit") or {}).get("message") or "")
            lines = message[:_COMMIT_SUBJECT_MAX].splitlines()
            if lines and lines[0].strip():
                subjects.append(lines[0].strip())
    return subjects
