from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from app.cron.refresh import RefreshChunkSummary, run_refresh_chunk
from app.cron.tokens import TokenSource


def _stub_analysis(analysis_id: int, target: str = "octocat", user_id: int = 1):
    return SimpleNamespace(id=analysis_id, target_login=target, user_id=user_id)


def _stub_report(target: str = "octocat", score: int = 50):
    return SimpleNamespace(
        username=target,
        total=score,
        tier=SimpleNamespace(name="Hobbyist"),
        model_dump=lambda mode="json": {"username": target, "total": score},
    )


class _FakeClock:
    def __init__(self, start: float = 0.0, step: float = 1.0):
        self.now = start
        self.step = step

    def __call__(self) -> float:
        v = self.now
        self.now += self.step
        return v


@pytest.fixture
def stub_db():
    """A no-op AsyncSession stub. Tests inject the data they need via mock returns."""
    return SimpleNamespace(
        commit=AsyncMock(return_value=None),
        flush=AsyncMock(return_value=None),
        execute=AsyncMock(),
        scalar=AsyncMock(),
        add=lambda *_args, **_kwargs: None,
        get=AsyncMock(),
    )


async def test_happy_path_three_rows_all_succeed(stub_db, monkeypatch):
    rows = [_stub_analysis(i, target=f"target-{i}") for i in (1, 2, 3)]

    monkeypatch.setattr(
        "app.cron.refresh._fetch_stale_analyses",
        AsyncMock(return_value=rows),
    )
    monkeypatch.setattr(
        "app.cron.refresh._resolve_token",
        AsyncMock(return_value=("tok", TokenSource.USER_SESSION)),
    )
    monkeypatch.setattr(
        "app.cron.refresh._fetch_report",
        AsyncMock(side_effect=lambda username, **_: _stub_report(username)),
    )
    record = AsyncMock(return_value=SimpleNamespace(id=99))
    monkeypatch.setattr("app.cron.refresh._record_run", record)

    summary: RefreshChunkSummary = await run_refresh_chunk(
        stub_db, limit=10, deadline_seconds=10, now=_FakeClock(step=0.1)
    )

    assert summary.processed == 3
    assert summary.succeeded == 3
    assert summary.skipped == 0
    assert summary.rate_limited == 0
    assert summary.deadline_reached is False
    assert {o.status for o in summary.outcomes} == {"succeeded"}
    assert record.await_count == 3


async def test_per_row_exception_is_isolated(stub_db, monkeypatch):
    rows = [_stub_analysis(i, target=f"t-{i}") for i in (1, 2, 3)]

    async def _maybe_explode(username: str, **_):
        if username == "t-2":
            raise RuntimeError("boom")
        return _stub_report(username)

    monkeypatch.setattr("app.cron.refresh._fetch_stale_analyses", AsyncMock(return_value=rows))
    monkeypatch.setattr(
        "app.cron.refresh._resolve_token",
        AsyncMock(return_value=("tok", TokenSource.APP_FALLBACK)),
    )
    monkeypatch.setattr("app.cron.refresh._fetch_report", AsyncMock(side_effect=_maybe_explode))
    monkeypatch.setattr("app.cron.refresh._record_run", AsyncMock(return_value=None))

    summary = await run_refresh_chunk(
        stub_db, limit=10, deadline_seconds=10, now=_FakeClock(step=0.1)
    )

    assert summary.processed == 3
    assert summary.succeeded == 2
    assert summary.skipped == 1
    statuses = [o.status for o in summary.outcomes]
    assert statuses == ["succeeded", "unexpected_error", "succeeded"]


async def test_rate_limit_cliff_stops_chunk(stub_db, monkeypatch):
    rows = [_stub_analysis(i, target=f"t-{i}") for i in (1, 2, 3)]

    async def _maybe_429(username: str, **_):
        if username == "t-2":
            resp = httpx.Response(403, headers={"X-RateLimit-Remaining": "0"})
            raise httpx.HTTPStatusError(
                "rate limit", request=httpx.Request("GET", "/x"), response=resp
            )
        return _stub_report(username)

    monkeypatch.setattr("app.cron.refresh._fetch_stale_analyses", AsyncMock(return_value=rows))
    monkeypatch.setattr(
        "app.cron.refresh._resolve_token",
        AsyncMock(return_value=("tok", TokenSource.APP_FALLBACK)),
    )
    monkeypatch.setattr("app.cron.refresh._fetch_report", AsyncMock(side_effect=_maybe_429))
    monkeypatch.setattr("app.cron.refresh._record_run", AsyncMock(return_value=None))

    summary = await run_refresh_chunk(
        stub_db, limit=10, deadline_seconds=10, now=_FakeClock(step=0.1)
    )

    assert summary.rate_limited == 1
    assert summary.succeeded == 1  # first row finished before the cliff
    assert summary.processed == 2  # third row never attempted
    assert summary.outcomes[-1].status == "rate_limited"


async def test_github_404_is_warn_skip(stub_db, monkeypatch):
    rows = [_stub_analysis(1, target="ghost-user")]

    async def _404(username: str, **_):
        resp = httpx.Response(404)
        raise httpx.HTTPStatusError("not found", request=httpx.Request("GET", "/x"), response=resp)

    monkeypatch.setattr("app.cron.refresh._fetch_stale_analyses", AsyncMock(return_value=rows))
    monkeypatch.setattr(
        "app.cron.refresh._resolve_token",
        AsyncMock(return_value=("tok", TokenSource.APP_FALLBACK)),
    )
    monkeypatch.setattr("app.cron.refresh._fetch_report", AsyncMock(side_effect=_404))
    monkeypatch.setattr("app.cron.refresh._record_run", AsyncMock(return_value=None))

    summary = await run_refresh_chunk(
        stub_db, limit=10, deadline_seconds=10, now=_FakeClock(step=0.1)
    )

    assert summary.skipped == 1
    assert summary.succeeded == 0
    assert summary.outcomes[0].status == "not_found"


async def test_deadline_guard_exits_cleanly(stub_db, monkeypatch):
    rows = [_stub_analysis(i, target=f"t-{i}") for i in range(1, 6)]

    monkeypatch.setattr("app.cron.refresh._fetch_stale_analyses", AsyncMock(return_value=rows))
    monkeypatch.setattr(
        "app.cron.refresh._resolve_token",
        AsyncMock(return_value=("tok", TokenSource.APP_FALLBACK)),
    )
    monkeypatch.setattr(
        "app.cron.refresh._fetch_report",
        AsyncMock(side_effect=lambda username, **_: _stub_report(username)),
    )
    monkeypatch.setattr("app.cron.refresh._record_run", AsyncMock(return_value=None))

    # Each iteration consumes 3 clock calls (budget check + iter_start +
    # duration end). step=25, deadline=240 -> 3 iters succeed using 9 calls
    # of 25 = 225s; 4th iter's budget check at t=250 trips the deadline.
    summary = await run_refresh_chunk(
        stub_db, limit=10, deadline_seconds=240, now=_FakeClock(start=0, step=25)
    )

    assert summary.deadline_reached is True
    assert summary.succeeded == 3
    assert summary.processed == 3
