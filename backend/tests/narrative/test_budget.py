from datetime import UTC, datetime, timedelta

from app.narrative.budget import DailyBudget


def test_try_consume_allows_calls_within_limit() -> None:
    b = DailyBudget(limit=2)
    allowed, remaining, _ = b.try_consume()
    assert allowed is True
    assert remaining == 1


def test_try_consume_blocks_calls_once_exhausted() -> None:
    b = DailyBudget(limit=1)
    b.try_consume()  # 1 -> 0
    allowed, remaining, _ = b.try_consume()
    assert allowed is False
    assert remaining == 0


def test_limit_zero_blocks_immediately() -> None:
    b = DailyBudget(limit=0)
    allowed, _, _ = b.try_consume()
    assert allowed is False


def test_resets_at_utc_midnight() -> None:
    now = datetime(2026, 5, 16, 12, 0, tzinfo=UTC)
    b = DailyBudget(limit=1, clock=lambda: now)

    b.try_consume()
    assert b.try_consume()[0] is False

    # Move clock past midnight
    now += timedelta(hours=13)
    allowed, remaining, _ = b.try_consume()
    assert allowed is True
    assert remaining == 0
