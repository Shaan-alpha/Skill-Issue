from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.cache.keys import NAMESPACE_RATE_LIMIT, rate_limit_key

if TYPE_CHECKING:
    from app.cache.client import RedisCache


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    current: int  # post-increment value (so first call -> 1)
    limit: int


async def try_increment_counter(
    cache: RedisCache,
    *,
    name: str,
    subject: str,
    limit: int,
    hour_bucket: str,
    ttl_seconds: int = 3700,
) -> RateLimitResult:
    """Atomically increment a per-subject-per-bucket counter and return whether
    the caller is under the limit.

    `subject` is the caller-scoped identity (`user:<id>` or `ip:<addr>`).
    `hour_bucket` is whatever the caller wants to scope by — typically the
    current UTC hour, formatted as 'YYYY-MM-DD-HH'. We set EXPIRE on first
    observation so the key cleans up after the bucket rolls over.

    Fail-open: if Redis errors, INCR returns 0 (per RedisCache), which we
    treat as `allowed=True, current=0`. A flaky Redis shouldn't block users.
    """
    key = rate_limit_key(name, subject=subject, hour_bucket=hour_bucket)
    current = await cache.incr(NAMESPACE_RATE_LIMIT, key)
    if current == 1:
        # First write into this bucket — pin a TTL so we don't leak keys.
        await cache.expire(NAMESPACE_RATE_LIMIT, key, ttl_seconds)
    if current == 0:
        # Redis failed (RedisCache returned 0). Fail open — let the request
        # through rather than blocking everyone when the cache is sick.
        return RateLimitResult(allowed=True, current=0, limit=limit)
    return RateLimitResult(allowed=current <= limit, current=current, limit=limit)
