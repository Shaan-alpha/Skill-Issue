"""Singleflight lock — coalesces concurrent same-key cache misses so the
underlying expensive work runs at most once.

Pattern:

    async with singleflight(cache, "report", username) as got_lock:
        if got_lock:
            # We're the elected runner. Do the expensive work, populate the
            # cache, return.
            ...
        else:
            # Someone else is running (or Redis is unreachable). Check the
            # cache one more time; if still empty, fall through to live work.
            ...

`got_lock=False` covers three cases the caller treats the same way (try the
cache once more, otherwise run live):
  1. Another caller is holding the lock RIGHT NOW (we waited, they finished).
  2. We waited the full timeout and the holder never released.
  3. Redis itself is unreachable (fail-open).
"""

from __future__ import annotations

import asyncio
import logging
import secrets
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from app.cache.keys import NAMESPACE_LOCK, TTL_LOCK_SECONDS

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from app.cache.client import RedisCache

logger = logging.getLogger(__name__)


@asynccontextmanager
async def singleflight(
    cache: RedisCache,
    namespace: str,
    key: str,
    *,
    ttl_seconds: int = TTL_LOCK_SECONDS,
    poll_interval_seconds: float = 0.2,
    max_wait_seconds: float = 25.0,
) -> AsyncIterator[bool]:
    """Try to take a SET-NX lock on (namespace, key).

    Yields True if we acquired the lock (caller should do the work).
    Yields False if another holder is running, we waited and timed out,
    or Redis is unreachable (caller should fall through to live work).
    """
    lock_key = f"{namespace}:{key}"
    holder_id = secrets.token_hex(8)

    got = await cache.set_nx(NAMESPACE_LOCK, lock_key, holder_id, ttl_seconds=ttl_seconds)
    if got:
        try:
            yield True
        finally:
            # Best-effort release. Even if delete fails (Redis unreachable),
            # the TTL guarantees the lock eventually clears.
            await cache.delete_if_equals(NAMESPACE_LOCK, lock_key, holder_id)
        return

    # Someone else holds the lock — wait for them.
    waited = 0.0
    while waited < max_wait_seconds:
        await asyncio.sleep(poll_interval_seconds)
        waited += poll_interval_seconds
        # Try the lock once more in case the holder finished.
        if await cache.set_nx(NAMESPACE_LOCK, lock_key, holder_id, ttl_seconds=ttl_seconds):
            try:
                yield True
            finally:
                await cache.delete_if_equals(NAMESPACE_LOCK, lock_key, holder_id)
            return

    logger.warning(
        "singleflight: waited %ss for lock %s:%s and timed out; falling through",
        max_wait_seconds,
        namespace,
        key,
    )
    yield False
