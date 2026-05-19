from __future__ import annotations

import json
import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)

KEY_PREFIX = "si:v1:"


class _AsyncRedisProtocol(Protocol):
    """Minimum surface of upstash_redis.asyncio.Redis that RedisCache consumes."""

    async def get(self, key: str) -> str | None: ...
    async def set(
        self,
        key: str,
        value: str,
        *,
        ex: int | None = ...,
        nx: bool = ...,
    ) -> bool | str | None: ...
    async def delete(self, *keys: str) -> int: ...
    async def incr(self, key: str) -> int: ...
    async def expire(self, key: str, seconds: int) -> bool: ...
    async def ping(self) -> str: ...


class RedisCache:
    """Fail-open JSON cache layered on top of an async Redis client.

    Every operation swallows Redis-side exceptions and returns a conservative
    result (None / False / 0) so the cache can never block the live path.
    """

    def __init__(self, redis: _AsyncRedisProtocol) -> None:
        self._redis = redis

    @staticmethod
    def _build_key(namespace: str, key: str) -> str:
        return f"{KEY_PREFIX}{namespace}:{key}"

    async def get_json(self, namespace: str, key: str) -> Any | None:
        full = self._build_key(namespace, key)
        try:
            raw = await self._redis.get(full)
        except Exception:
            logger.warning("cache GET failed for %s", full, exc_info=True)
            return None
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            logger.warning("cache value at %s is not JSON; ignoring", full)
            return None

    async def set_json(
        self,
        namespace: str,
        key: str,
        value: Any,
        *,
        ttl_seconds: int | None = None,
    ) -> None:
        full = self._build_key(namespace, key)
        try:
            await self._redis.set(full, json.dumps(value), ex=ttl_seconds)
        except Exception:
            logger.warning("cache SET failed for %s", full, exc_info=True)

    async def set_nx(
        self,
        namespace: str,
        key: str,
        value: str,
        *,
        ttl_seconds: int,
    ) -> bool:
        """SET NX with TTL — used by singleflight locks. Returns True if
        the caller acquired the key, False if someone else already holds it."""
        full = self._build_key(namespace, key)
        try:
            result = await self._redis.set(full, value, ex=ttl_seconds, nx=True)
        except Exception:
            logger.warning("cache SETNX failed for %s", full, exc_info=True)
            return False
        # upstash-redis returns True/"OK" on success, None on NX-failure.
        return result is True or result == "OK"

    async def delete(self, namespace: str, key: str) -> int:
        full = self._build_key(namespace, key)
        try:
            return await self._redis.delete(full)
        except Exception:
            logger.warning("cache DEL failed for %s", full, exc_info=True)
            return 0

    async def incr(self, namespace: str, key: str) -> int:
        """Atomic INCR. Returns 0 on Redis failure (conservative — treat as
        not-incremented so callers don't double-count)."""
        full = self._build_key(namespace, key)
        try:
            return await self._redis.incr(full)
        except Exception:
            logger.warning("cache INCR failed for %s", full, exc_info=True)
            return 0

    async def expire(self, namespace: str, key: str, seconds: int) -> bool:
        full = self._build_key(namespace, key)
        try:
            return await self._redis.expire(full, seconds)
        except Exception:
            logger.warning("cache EXPIRE failed for %s", full, exc_info=True)
            return False

    async def ping(self) -> bool:
        try:
            result = await self._redis.ping()
        except Exception:
            return False
        return result == "PONG"
