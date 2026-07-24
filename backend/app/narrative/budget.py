import logging
import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from app.cache.keys import NAMESPACE_BUDGET, TTL_BUDGET_KEY_SECONDS, budget_day_key

if TYPE_CHECKING:
    from app.cache.client import RedisCache

logger = logging.getLogger(__name__)


class DailyBudget:
    """Thread-safe daily quota counter, optionally shared across instances
    via Upstash Redis."""

    def __init__(
        self,
        limit: int = 50,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        *,
        redis: "RedisCache | None" = None,
    ) -> None:
        self._limit = limit
        self._clock = clock
        self._lock = threading.Lock()
        self._current_day: str | None = None
        self._remaining = limit
        self._redis = redis

    def _utc_day(self, now: datetime) -> str:
        return now.strftime("%Y-%m-%d")

    def _resets_at(self, now: datetime) -> str:
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        return tomorrow.isoformat()

    # --- Sync API (in-process, preserved for backwards compat) ---

    def try_consume(self) -> tuple[bool, int, str]:
        now = self._clock()
        day = self._utc_day(now)
        resets = self._resets_at(now)
        with self._lock:
            if self._current_day != day:
                self._current_day = day
                self._remaining = self._limit
            if self._remaining <= 0:
                return False, 0, resets
            self._remaining -= 1
            return True, self._remaining, resets

    # --- Async API (Redis when configured, in-process otherwise) ---

    async def atry_consume(
        self,
        *,
        subject: str | None = None,
        subject_limit: int | None = None,
    ) -> tuple[bool, int, str]:
        now = self._clock()
        resets = self._resets_at(now)
        if self._redis is None:
            # SI-01: no Redis configured -> conservative in-process global budget.
            return self.try_consume()

        gkey = budget_day_key("narrative", now)
        gcount = await self._redis.incr(NAMESPACE_BUDGET, gkey)
        if gcount == 0:
            # Redis error sentinel. Degrade to the in-process global budget
            # instead of failing open (SI-01).
            logger.warning("narrative.budget.degraded_local reason=redis_error")
            return self.try_consume()
        if gcount == 1:
            # First INCR of the day — set the expiry so the key self-cleans.
            await self._redis.expire(NAMESPACE_BUDGET, gkey, TTL_BUDGET_KEY_SECONDS)
        if gcount > self._limit:
            await self._redis.decr(NAMESPACE_BUDGET, gkey)  # release the reservation
            return False, 0, resets

        # Per-subject dimension (SI-02). Reserve-then-release: if the subject is
        # over its cap, give the global reservation back so a blocked request
        # never permanently consumes the global budget.
        if subject is not None and subject_limit is not None:
            skey = budget_day_key(f"narrative:{subject}", now)
            scount = await self._redis.incr(NAMESPACE_BUDGET, skey)
            if scount == 1:
                await self._redis.expire(NAMESPACE_BUDGET, skey, TTL_BUDGET_KEY_SECONDS)
            if scount > subject_limit:
                await self._redis.decr(NAMESPACE_BUDGET, gkey)
                await self._redis.decr(NAMESPACE_BUDGET, skey)
                return False, 0, resets

        remaining = max(self._limit - gcount, 0)
        return True, remaining, resets
