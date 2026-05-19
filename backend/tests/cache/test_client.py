import pytest


@pytest.mark.asyncio
async def test_set_then_get_round_trip(fake_cache) -> None:
    await fake_cache.set_json("report", "octocat", {"score": 78})
    got = await fake_cache.get_json("report", "octocat")
    assert got == {"score": 78}


@pytest.mark.asyncio
async def test_get_missing_returns_none(fake_cache) -> None:
    assert await fake_cache.get_json("report", "ghost") is None


@pytest.mark.asyncio
async def test_namespacing_does_not_bleed(fake_cache) -> None:
    await fake_cache.set_json("report", "octocat", {"a": 1})
    await fake_cache.set_json("gh", "octocat", {"b": 2})
    assert await fake_cache.get_json("report", "octocat") == {"a": 1}
    assert await fake_cache.get_json("gh", "octocat") == {"b": 2}


@pytest.mark.asyncio
async def test_set_with_ttl_expires(fake_cache, fake_redis) -> None:
    await fake_cache.set_json("report", "octocat", {"x": 1}, ttl_seconds=60)
    fake_redis._force_expire("si:v1:report:octocat")
    assert await fake_cache.get_json("report", "octocat") is None


@pytest.mark.asyncio
async def test_delete_removes_value(fake_cache) -> None:
    await fake_cache.set_json("report", "octocat", {"x": 1})
    assert await fake_cache.delete("report", "octocat") == 1
    assert await fake_cache.get_json("report", "octocat") is None


@pytest.mark.asyncio
async def test_get_returns_none_when_redis_raises(fake_cache, fake_redis) -> None:
    """Fail-open: a Redis exception must NOT propagate; cache miss is the result."""
    await fake_cache.set_json("report", "octocat", {"x": 1})
    fake_redis.fail_next = 1
    assert await fake_cache.get_json("report", "octocat") is None


@pytest.mark.asyncio
async def test_set_swallows_redis_exception(fake_cache, fake_redis) -> None:
    fake_redis.fail_next = 1
    # Should not raise.
    await fake_cache.set_json("report", "octocat", {"x": 1})


@pytest.mark.asyncio
async def test_corrupt_cached_value_returns_none(fake_cache, fake_redis) -> None:
    """A non-JSON string in Redis must be ignored, not crash."""
    await fake_redis.set("si:v1:report:octocat", "this is not json")
    assert await fake_cache.get_json("report", "octocat") is None


@pytest.mark.asyncio
async def test_set_nx_only_sets_when_absent(fake_cache) -> None:
    ok1 = await fake_cache.set_nx("lock", "octocat", "holder-a", ttl_seconds=30)
    ok2 = await fake_cache.set_nx("lock", "octocat", "holder-b", ttl_seconds=30)
    assert ok1 is True
    assert ok2 is False


@pytest.mark.asyncio
async def test_incr_increments(fake_cache) -> None:
    assert await fake_cache.incr("budget", "today") == 1
    assert await fake_cache.incr("budget", "today") == 2


@pytest.mark.asyncio
async def test_incr_returns_zero_on_failure(fake_cache, fake_redis) -> None:
    fake_redis.fail_next = 1
    assert await fake_cache.incr("budget", "today") == 0


@pytest.mark.asyncio
async def test_ping_returns_true_on_pong(fake_cache) -> None:
    assert await fake_cache.ping() is True


@pytest.mark.asyncio
async def test_ping_returns_false_on_failure(fake_cache, fake_redis) -> None:
    fake_redis.fail_next = 1
    assert await fake_cache.ping() is False
