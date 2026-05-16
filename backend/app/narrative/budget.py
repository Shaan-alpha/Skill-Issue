import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta


class DailyBudget:
    """In-process thread-safe daily quota counter.

    Tracks remaining calls for the current UTC day. Resets automatically on the
    first call after UTC midnight.
    """

    def __init__(
        self,
        limit: int = 50,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._limit = limit
        self._clock = clock
        self._lock = threading.Lock()
        self._current_day: str | None = None
        self._remaining = limit

    def _get_utc_day(self, now: datetime) -> str:
        return now.strftime("%Y-%m-%d")

    def _get_resets_at(self, now: datetime) -> str:
        tomorrow = now.replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
        return tomorrow.isoformat()

    def try_consume(self) -> tuple[bool, int, str]:
        """Returns (allowed, remaining_after_call, resets_at_iso)."""
        now = self._clock()
        day = self._get_utc_day(now)
        resets = self._get_resets_at(now)

        with self._lock:
            if self._current_day != day:
                self._current_day = day
                self._remaining = self._limit

            if self._remaining <= 0:
                return False, 0, resets

            self._remaining -= 1
            return True, self._remaining, resets
