import pytest

from app.cache.client import RedisCache
from app.narrative.budget import DailyBudget


@pytest.mark.asyncio
async def test_aconsume_decrements_via_redis(fake_cache: RedisCache) -> None:
    b = DailyBudget(limit=3, redis=fake_cache)
    for _ in range(3):
        allowed, _, _ = await b.atry_consume()
        assert allowed is True


@pytest.mark.asyncio
async def test_aconsume_returns_false_when_exhausted(fake_cache: RedisCache) -> None:
    b = DailyBudget(limit=2, redis=fake_cache)
    await b.atry_consume()
    await b.atry_consume()
    allowed, remaining, _ = await b.atry_consume()
    assert allowed is False
    assert remaining == 0


@pytest.mark.asyncio
async def test_in_process_fallback_without_redis() -> None:
    b = DailyBudget(limit=1)
    a1, _, _ = await b.atry_consume()
    a2, _, _ = await b.atry_consume()
    assert a1 is True
    assert a2 is False


@pytest.mark.asyncio
async def test_redis_failure_falls_through_to_allow(fake_cache: RedisCache, fake_redis) -> None:
    """Even with a Redis failure on the INCR, allow the call (fail-open:
    better to over-spend than block users)."""
    b = DailyBudget(limit=2, redis=fake_cache)
    fake_redis.fail_next = 1
    allowed, _, _ = await b.atry_consume()
    assert allowed is True
