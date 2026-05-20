import pytest

from app.cache.client import RedisCache
from app.narrative.cache import NarrativeCache


@pytest.mark.asyncio
async def test_put_then_get_via_redis(fake_cache: RedisCache) -> None:
    c = NarrativeCache(redis=fake_cache)
    await c.aput("octocat:abc123:roast", "narrative text")
    assert await c.aget("octocat:abc123:roast") == "narrative text"


@pytest.mark.asyncio
async def test_miss_returns_none_via_redis(fake_cache: RedisCache) -> None:
    c = NarrativeCache(redis=fake_cache)
    assert await c.aget("missing") is None


@pytest.mark.asyncio
async def test_in_process_fallback_when_no_redis() -> None:
    c = NarrativeCache()
    await c.aput("k", "v")
    assert await c.aget("k") == "v"


@pytest.mark.asyncio
async def test_redis_failure_falls_through_to_none(fake_cache: RedisCache, fake_redis) -> None:
    c = NarrativeCache(redis=fake_cache)
    await c.aput("k", "v")
    fake_redis.fail_next = 1
    assert await c.aget("k") is None
