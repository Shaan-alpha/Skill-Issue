import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from app.cache.keys import NAMESPACE_BUDGET, TTL_BUDGET_KEY_SECONDS, budget_day_key

if TYPE_CHECKING:
    from app.cache.client import RedisCache


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

    async def atry_consume(self) -> tuple[bool, int, str]:
        now = self._clock()
        resets = self._resets_at(now)
        if self._redis is None:
            return self.try_consume()

        day_key = budget_day_key("narrative", now)
        new_count = await self._redis.incr(NAMESPACE_BUDGET, day_key)
        # Fail-open: incr returning 0 means Redis was unreachable; allow.
        if new_count == 0:
            return True, self._limit - 1, resets

        # First INCR of the day — set the expiry so the key cleans itself up
        # after the rollover.
        if new_count == 1:
            await self._redis.expire(NAMESPACE_BUDGET, day_key, TTL_BUDGET_KEY_SECONDS)

        remaining = max(self._limit - new_count, 0)
        if new_count > self._limit:
            return False, 0, resets
        return True, remaining, resets
