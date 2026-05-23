from __future__ import annotations

import pytest

from app.cache.rate_limit import RateLimitResult, try_increment_counter


@pytest.fixture
def hour_bucket() -> str:
    # Deterministic — tests don't depend on real time.
    return "2026-05-22-14"


async def test_under_limit_returns_allowed(fake_cache, hour_bucket):
    res: RateLimitResult = await try_increment_counter(
        fake_cache,
        name="force_refresh",
        user_id=1,
        limit=10,
        hour_bucket=hour_bucket,
    )
    assert res.allowed is True
    assert res.current == 1
    assert res.limit == 10


async def test_at_limit_still_returns_allowed_on_the_nth_call(fake_cache, hour_bucket):
    for _ in range(9):
        await try_increment_counter(
            fake_cache, name="force_refresh", user_id=1, limit=10, hour_bucket=hour_bucket
        )
    res = await try_increment_counter(
        fake_cache, name="force_refresh", user_id=1, limit=10, hour_bucket=hour_bucket
    )
    assert res.allowed is True
    assert res.current == 10


async def test_over_limit_returns_denied(fake_cache, hour_bucket):
    for _ in range(10):
        await try_increment_counter(
            fake_cache, name="force_refresh", user_id=1, limit=10, hour_bucket=hour_bucket
        )
    res = await try_increment_counter(
        fake_cache, name="force_refresh", user_id=1, limit=10, hour_bucket=hour_bucket
    )
    assert res.allowed is False
    assert res.current == 11


async def test_first_increment_sets_expiration(fake_cache, hour_bucket):
    """First call must EXPIRE the key so it auto-cleans after the bucket rolls
    over. Without this, the key lives forever."""
    await try_increment_counter(
        fake_cache,
        name="force_refresh",
        user_id=1,
        limit=10,
        hour_bucket=hour_bucket,
        ttl_seconds=3700,
    )
    from app.cache.keys import NAMESPACE_RATE_LIMIT, rate_limit_key

    full = f"si:v1:{NAMESPACE_RATE_LIMIT}:" + rate_limit_key(
        "force_refresh", user_id=1, hour_bucket=hour_bucket
    )
    # FakeRedis tracks deadlines internally
    assert full in fake_cache._redis._deadlines
