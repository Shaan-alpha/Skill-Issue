import pytest
import respx
from httpx import HTTPStatusError, Response

from app.cache.client import RedisCache
from app.github.client import GitHubClient


@pytest.mark.asyncio
async def test_uncached_get_user_hits_github(fake_cache: RedisCache) -> None:
    with respx.mock:
        respx.get("https://api.github.com/users/octocat").mock(
            return_value=Response(200, json={"login": "octocat", "id": 583231})
        )
        async with GitHubClient(token="t", cache=fake_cache) as gh:
            got = await gh.get_user("octocat")
        assert got["login"] == "octocat"


@pytest.mark.asyncio
async def test_second_get_user_hits_cache_not_github(fake_cache: RedisCache) -> None:
    with respx.mock:
        route = respx.get("https://api.github.com/users/octocat").mock(
            return_value=Response(200, json={"login": "octocat", "id": 583231})
        )
        async with GitHubClient(token="t", cache=fake_cache) as gh:
            await gh.get_user("octocat")
            await gh.get_user("octocat")
        # Second call MUST be a cache hit.
        assert route.call_count == 1


@pytest.mark.asyncio
async def test_404_responses_are_cached_too(fake_cache: RedisCache) -> None:
    """Re-fetching a known-missing user shouldn't burn a fresh GH call."""
    with respx.mock:
        route = respx.get("https://api.github.com/users/ghost").mock(
            return_value=Response(404, json={"message": "Not Found"})
        )
        async with GitHubClient(token="t", cache=fake_cache) as gh:
            with pytest.raises(HTTPStatusError):
                await gh.get_user("ghost")
            with pytest.raises(HTTPStatusError):
                await gh.get_user("ghost")
        assert route.call_count == 1


@pytest.mark.asyncio
async def test_5xx_responses_are_NOT_cached(fake_cache: RedisCache) -> None:
    """A transient GitHub 502 should not poison the cache."""
    with respx.mock:
        route = respx.get("https://api.github.com/users/octocat").mock(
            side_effect=[
                Response(502, json={"message": "Bad Gateway"}),
                Response(200, json={"login": "octocat"}),
            ]
        )
        async with GitHubClient(token="t", cache=fake_cache) as gh:
            with pytest.raises(HTTPStatusError):
                await gh.get_user("octocat")
            # Second call should retry GitHub, not return a cached 502.
            got = await gh.get_user("octocat")
        assert route.call_count == 2
        assert got["login"] == "octocat"


@pytest.mark.asyncio
async def test_cache_failure_falls_through_to_github(fake_cache: RedisCache, fake_redis) -> None:
    """If Redis is broken on the read, we still get a valid GitHub response."""
    fake_redis.fail_next = 1
    with respx.mock:
        respx.get("https://api.github.com/users/octocat").mock(
            return_value=Response(200, json={"login": "octocat"})
        )
        async with GitHubClient(token="t", cache=fake_cache) as gh:
            got = await gh.get_user("octocat")
        assert got["login"] == "octocat"


@pytest.mark.asyncio
async def test_no_cache_param_means_no_caching(fake_cache: RedisCache) -> None:
    """Backwards compat: callers that don't pass cache still work as before."""
    with respx.mock:
        route = respx.get("https://api.github.com/users/octocat").mock(
            return_value=Response(200, json={"login": "octocat"})
        )
        async with GitHubClient(token="t") as gh:
            await gh.get_user("octocat")
            await gh.get_user("octocat")
        # No cache → every call hits GitHub.
        assert route.call_count == 2
