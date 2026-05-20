import hashlib
import json
from collections import OrderedDict
from typing import TYPE_CHECKING

from app.cache.keys import NAMESPACE_NARRATIVE, TTL_NARRATIVE_SECONDS
from app.models import Report

if TYPE_CHECKING:
    from app.cache.client import RedisCache


class NarrativeCache:
    """LRU mapping (username, scores_hash, mode) -> narrative text.

    With `redis=None`, the cache is an in-process OrderedDict (256 entries).
    With a `RedisCache`, lookups go to Upstash with a 24h TTL — entries are
    shared across Fluid Compute instances.

    The synchronous get/put API is preserved for backwards compatibility with
    the existing NarrativeService tests; the async aget/aput methods are
    preferred for new call sites because they can hit Redis.
    """

    def __init__(
        self,
        max_entries: int = 256,
        *,
        redis: "RedisCache | None" = None,
    ) -> None:
        self._store: OrderedDict[str, str] = OrderedDict()
        self._max = max_entries
        self._redis = redis

    @staticmethod
    def key(username: str, scores_hash: str, mode: str) -> str:
        return f"{username}:{scores_hash}:{mode}"

    @staticmethod
    def scores_hash(report: Report) -> str:
        """Stable 16-char hex digest over the parts of the report the LLM sees.

        Equivalent reports (same total, tier, badges, per-bucket points) hash
        to the same value regardless of badge insertion order.
        """
        payload = json.dumps(
            {
                "total": report.total,
                "tier": report.tier.name,
                "badges": sorted(b.slug for b in report.badges),
                "breakdown": {
                    "repo_quality": report.breakdown.repo_quality.points,
                    "engineering_maturity": report.breakdown.engineering_maturity.points,
                    "oss_collab": report.breakdown.oss_collab.points,
                    "consistency": report.breakdown.consistency.points,
                    "recruiter_signal": report.breakdown.recruiter_signal.points,
                    "learning_trajectory": report.breakdown.learning_trajectory.points,
                },
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    # --- Async API (preferred — hits Redis when configured) ---

    async def aget(self, key: str) -> str | None:
        if self._redis is not None:
            value = await self._redis.get_json(NAMESPACE_NARRATIVE, key)
            if isinstance(value, str):
                return value
            return None
        return self.get(key)

    async def aput(self, key: str, value: str) -> None:
        if self._redis is not None:
            await self._redis.set_json(
                NAMESPACE_NARRATIVE,
                key,
                value,
                ttl_seconds=TTL_NARRATIVE_SECONDS,
            )
            return
        self.put(key, value)

    # --- Sync API (in-process fallback only) ---

    def get(self, key: str) -> str | None:
        if key not in self._store:
            return None
        self._store.move_to_end(key)
        return self._store[key]

    def put(self, key: str, value: str) -> None:
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = value
        if len(self._store) > self._max:
            self._store.popitem(last=False)
