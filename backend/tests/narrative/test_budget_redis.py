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
async def test_per_subject_cap_blocks_before_global(fake_cache: RedisCache) -> None:
    # SI-02: the caller's per-subject cap blocks even when the global has room.
    b = DailyBudget(limit=100, redis=fake_cache)
    assert (await b.atry_consume(subject="ip:1.2.3.4", subject_limit=2))[0] is True
    assert (await b.atry_consume(subject="ip:1.2.3.4", subject_limit=2))[0] is True
    allowed, _remaining, _resets = await b.atry_consume(subject="ip:1.2.3.4", subject_limit=2)
    assert allowed is False


@pytest.mark.asyncio
async def test_subject_block_releases_global(fake_cache: RedisCache) -> None:
    # SI-02 reserve-then-release: a subject-blocked call must give its global
    # reservation back, so a blocked request never permanently spends the global.
    b = DailyBudget(limit=100, redis=fake_cache)
    await b.atry_consume(subject="ip:x", subject_limit=1)  # global -> 1
    await b.atry_consume(subject="ip:x", subject_limit=1)  # blocked -> global released to 1
    allowed, remaining, _resets = await b.atry_consume(subject="ip:y", subject_limit=100)
    assert allowed is True
    # global consumed = x(1) + y(1) = 2, not 3 -> the blocked call released.
    assert remaining == 98


@pytest.mark.asyncio
async def test_redis_error_falls_back_to_in_process(fake_cache: RedisCache, fake_redis) -> None:
    # SI-01: a Redis error degrades to the in-process global budget instead of
    # failing open (previously any Redis failure allowed the call unconditionally).
    b = DailyBudget(limit=2, redis=fake_cache)
    fake_redis.fail_next = 100  # every op raises -> incr returns 0 -> in-process
    assert (await b.atry_consume(subject="ip:z", subject_limit=1))[0] is True  # in-process 1/2
    assert (await b.atry_consume(subject="ip:z", subject_limit=1))[0] is True  # in-process 2/2
    assert (await b.atry_consume(subject="ip:z", subject_limit=1))[0] is False  # 3 > 2
