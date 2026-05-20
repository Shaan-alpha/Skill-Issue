"""Shared pytest fixtures for the Skill Issue backend test suite.

Fixtures defined here are available to every test under backend/tests/ without
needing to be imported.
"""

import os
import time

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Base


class FakeRedis:
    """In-memory async stub matching the surface of upstash_redis.asyncio.Redis
    that this codebase consumes. Tracks per-key TTL deadlines.

    Not thread-safe (tests run single-threaded). Optionally injects faults
    via `fail_next` to exercise fail-open paths.
    """

    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._deadlines: dict[str, float] = {}
        self.fail_next: int = 0

    def _maybe_fail(self) -> None:
        if self.fail_next > 0:
            self.fail_next -= 1
            raise RuntimeError("FakeRedis injected failure")

    def _expire_if_due(self, key: str) -> None:
        deadline = self._deadlines.get(key)
        if deadline is not None and time.monotonic() > deadline:
            self._store.pop(key, None)
            self._deadlines.pop(key, None)

    async def get(self, key: str) -> str | None:
        self._maybe_fail()
        self._expire_if_due(key)
        return self._store.get(key)

    async def set(
        self,
        key: str,
        value: str,
        *,
        ex: int | None = None,
        nx: bool = False,
    ) -> bool | str | None:
        self._maybe_fail()
        self._expire_if_due(key)
        if nx and key in self._store:
            return None
        self._store[key] = value
        if ex is not None:
            self._deadlines[key] = time.monotonic() + ex
        else:
            self._deadlines.pop(key, None)
        return True

    async def delete(self, *keys: str) -> int:
        self._maybe_fail()
        removed = 0
        for k in keys:
            if k in self._store:
                self._store.pop(k, None)
                self._deadlines.pop(k, None)
                removed += 1
        return removed

    async def incr(self, key: str) -> int:
        self._maybe_fail()
        self._expire_if_due(key)
        current = int(self._store.get(key, "0"))
        current += 1
        self._store[key] = str(current)
        return current

    async def expire(self, key: str, seconds: int) -> bool:
        self._maybe_fail()
        if key not in self._store:
            return False
        self._deadlines[key] = time.monotonic() + seconds
        return True

    async def ping(self) -> str:
        self._maybe_fail()
        return "PONG"

    def _force_expire(self, key: str) -> None:
        self._deadlines[key] = 0.0


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture
def fake_cache(fake_redis: FakeRedis):
    from app.cache.client import RedisCache

    return RedisCache(redis=fake_redis)


@pytest.fixture(autouse=True)
def _clear_cache_lru_between_tests():
    """The get_cache() / get_narrative_cache() / get_daily_budget() singletons
    are @lru_cache-cached. Tests that monkey-patch get_cache need the cache
    cleared so the override actually fires. Cleared before AND after each
    test so a singleton built in test A doesn't leak into test B."""
    from app.dependencies import (
        get_cache,
        get_daily_budget,
        get_narrative_cache,
        get_narrative_service,
    )

    for fn in (get_cache, get_daily_budget, get_narrative_cache, get_narrative_service):
        fn.cache_clear()
    yield
    for fn in (get_cache, get_daily_budget, get_narrative_cache, get_narrative_service):
        fn.cache_clear()


@pytest_asyncio.fixture(scope="session")
def test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        raise RuntimeError(
            "TEST_DATABASE_URL must be set. Use a Neon branch or local Postgres. "
            "Example: postgresql+asyncpg://postgres:postgres@localhost:5432/skill_issue_test"
        )
    return url


async def _reset_schema(conn) -> None:
    """Drop and recreate the public schema to give each test a clean slate.

    Using raw SQL avoids SQLAlchemy's use_alter FK teardown issue where
    DROP CONSTRAINT fails if the tables were already absent.
    """
    await conn.execute(text("DROP SCHEMA public CASCADE"))
    await conn.execute(text("CREATE SCHEMA public"))


@pytest_asyncio.fixture
async def db(test_database_url) -> AsyncSession:
    engine = create_async_engine(test_database_url, connect_args={"statement_cache_size": 0})
    async with engine.begin() as conn:
        await _reset_schema(conn)
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
    async with engine.begin() as conn:
        await _reset_schema(conn)
    await engine.dispose()
