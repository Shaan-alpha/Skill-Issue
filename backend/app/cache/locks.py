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

A waiter that outlasts the holder acquires the lock itself (True), so callers
must re-check their cache after entering: the previous holder has usually just
filled it (double-checked locking). `got_lock=False` means only that we waited
the full timeout and the holder never released. When Redis is unreachable
there is no lock to wait for, and the caller proceeds at once (True).
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
    if got is None:
        # Redis is unreachable, so there is no lock to wait for. Polling it would
        # stall every cold request for max_wait_seconds during an outage.
        yield True
        return
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
        acquired = await cache.set_nx(NAMESPACE_LOCK, lock_key, holder_id, ttl_seconds=ttl_seconds)
        if acquired is None:
            yield True
            return
        if acquired:
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
