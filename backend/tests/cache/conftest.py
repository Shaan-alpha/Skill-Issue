from __future__ import annotations

import time

import pytest


class FakeRedis:
    """In-memory async stub matching the surface of upstash_redis.asyncio.Redis
    that this codebase consumes. Tracks per-key TTL deadlines.

    Not thread-safe (tests run single-threaded). Optionally injects faults
    via `fail_next` to exercise fail-open paths.
    """

    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._deadlines: dict[str, float] = {}
        self.fail_next: int = 0  # number of upcoming calls that should raise

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

    # Helper for tests — force TTL expiry without sleeping.
    def _force_expire(self, key: str) -> None:
        self._deadlines[key] = 0.0


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture
def fake_cache(fake_redis: FakeRedis):
    from app.cache.client import RedisCache

    return RedisCache(redis=fake_redis)
