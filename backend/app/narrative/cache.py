import hashlib
import json
from collections import OrderedDict

from app.models import Report


class NarrativeCache:
    """In-process LRU mapping (username, scores_hash, mode) -> narrative text.

    Keys are the *complete* narrative the LLM produced. Re-streams synthesise
    SSE events from the cached string in `service.py`.
    """

    def __init__(self, max_entries: int = 256) -> None:
        self._store: OrderedDict[str, str] = OrderedDict()
        self._max = max_entries

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
