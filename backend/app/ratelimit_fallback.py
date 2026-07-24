"""In-process, per-instance rate-limit fallback for when Upstash Redis is
unreachable or unconfigured (v1.0.4 SI-01).

Fail-CLOSED-to-conservative: a Redis outage degrades to this bounded counter
rather than removing all limiting. Per-instance only, so under horizontal
scale-out the effective ceiling is limit x instances (audit SI-10) — still
strictly better than unlimited, and the degraded path is logged by the caller.
"""

from __future__ import annotations

import threading

# Bounded to keep memory flat during a sustained outage; on overflow we clear
# (the worst case is a one-bucket accounting reset, acceptable in degraded mode).
_MAX_ENTRIES = 50_000


class InProcessRateLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counts: dict[tuple[str, str, str], int] = {}

    def check(self, *, name: str, subject: str, limit: int, bucket: str) -> bool:
        key = (name, subject, bucket)
        with self._lock:
            if len(self._counts) > _MAX_ENTRIES:
                self._counts.clear()
            current = self._counts.get(key, 0) + 1
            self._counts[key] = current
            return current <= limit


# Process-wide singleton.
in_process_limiter = InProcessRateLimiter()
