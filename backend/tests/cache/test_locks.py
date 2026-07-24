import asyncio

import pytest

from app.cache.client import RedisCache
from app.cache.locks import singleflight


@pytest.mark.asyncio
async def test_first_caller_acquires_and_releases_lock(fake_cache: RedisCache) -> None:
    acquired: list[bool] = []
    async with singleflight(fake_cache, "report", "octocat") as got:
        acquired.append(got)
    assert acquired == [True]
    # After release, a fresh caller acquires again.
    async with singleflight(fake_cache, "report", "octocat") as got2:
        acquired.append(got2)
    assert acquired == [True, True]


async def _delayed_caller(fake_cache: RedisCache, results: list[bool]) -> None:
    await asyncio.sleep(0.005)
    async with singleflight(
        fake_cache,
        "report",
        "octocat",
        poll_interval_seconds=0.005,
        max_wait_seconds=0.02,
    ) as got:
        results.append(got)


@pytest.mark.asyncio
async def test_second_caller_times_out_while_holder_runs(fake_cache: RedisCache) -> None:
    """When the holder runs longer than the waiter's max_wait, the waiter
    times out with got=False so it can fall through to live work."""
    results: list[bool] = []

    async def caller(hold_for: float) -> None:
        async with singleflight(
            fake_cache,
            "report",
            "octocat",
            poll_interval_seconds=0.005,
            max_wait_seconds=0.02,
        ) as got:
            results.append(got)
            await asyncio.sleep(hold_for)

    # Holder takes the lock and keeps it for 100ms.
    # Delayed waiter starts 5ms later with a 20ms timeout → must time out.
    await asyncio.gather(caller(0.1), _delayed_caller(fake_cache, results))
    assert results == [True, False]


@pytest.mark.asyncio
async def test_waiter_acquires_after_holder_releases(fake_cache: RedisCache) -> None:
    """When the holder finishes within the waiter's max_wait, the waiter
    successfully acquires (got=True) after the holder releases."""
    results: list[bool] = []

    async def caller(hold_for: float) -> None:
        async with singleflight(
            fake_cache,
            "report",
            "octocat",
            poll_interval_seconds=0.005,
            max_wait_seconds=0.2,
        ) as got:
            results.append(got)
            await asyncio.sleep(hold_for)

    async def patient_waiter() -> None:
        await asyncio.sleep(0.005)
        async with singleflight(
            fake_cache,
            "report",
            "octocat",
            poll_interval_seconds=0.005,
            max_wait_seconds=0.2,
        ) as got:
            results.append(got)

    # Holder takes the lock for 30ms; waiter has 200ms — should acquire.
    await asyncio.gather(caller(0.03), patient_waiter())
    assert results == [True, True]


@pytest.mark.asyncio
async def test_lock_release_makes_next_caller_acquire(fake_cache: RedisCache) -> None:
    async with singleflight(fake_cache, "report", "octocat"):
        pass
    async with singleflight(fake_cache, "report", "octocat") as got:
        assert got is True


@pytest.mark.asyncio
async def test_caller_proceeds_when_redis_fails(fake_cache: RedisCache, fake_redis) -> None:
    """If Redis is unreachable, the lock acquisition silently falls through
    (got=False signals 'no lock held'); caller proceeds with live work."""
    fake_redis.fail_next = 100  # every redis call raises for this test
    async with singleflight(
        fake_cache,
        "report",
        "octocat",
        poll_interval_seconds=0.005,
        max_wait_seconds=0.02,
    ) as got:
        assert got is False


async def test_lock_ttl_is_sixty() -> None:
    # v1.0.5 SI-09: TTL must outlive a worst-case (deadline-bounded) cold ingest.
    from app.cache.keys import TTL_LOCK_SECONDS

    assert TTL_LOCK_SECONDS == 60


@pytest.mark.asyncio
async def test_holder_release_is_holder_checked(fake_cache: RedisCache, fake_redis) -> None:
    """v1.0.5 SI-09: a holder must only delete the lock IT owns. If its TTL
    expires mid-ingest and a successor re-acquires, the original holder's
    release must NOT delete the successor's lock."""
    full = "si:v1:lock:report:octocat"
    async with singleflight(fake_cache, "report", "octocat") as got:
        assert got is True
        # Simulate: holder A's TTL fired and successor B re-acquired the key.
        await fake_redis.set(full, "holderB")
    # A's release (holder-checked) must have left B's lock intact.
    assert await fake_redis.get(full) == "holderB"


@pytest.mark.asyncio
async def test_waiter_breaks_out_on_timeout(fake_cache: RedisCache) -> None:
    """If the lock holder never releases within max_wait, the waiter falls
    through with got=False so the caller does its own live work."""
    # Manually take the lock and never release.
    assert await fake_cache.set_nx("lock", "report:octocat", "holder", ttl_seconds=30)

    async with singleflight(
        fake_cache,
        "report",
        "octocat",
        poll_interval_seconds=0.005,
        max_wait_seconds=0.02,
    ) as got:
        assert got is False
