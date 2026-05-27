"""Cache key namespaces, TTL constants, and key-building helpers.

Single source of truth for every Redis key the codebase reads or writes.
Bumping `KEY_PREFIX` in `app/cache/client.py` invalidates every namespace at
once on schema changes.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime

# --- Namespaces (the first segment after the version prefix) ---

NAMESPACE_REPORT = "report"
NAMESPACE_LOCK = "lock"
NAMESPACE_GH = "gh"
NAMESPACE_NARRATIVE = "narrative"
NAMESPACE_BUDGET = "budget"
NAMESPACE_RATE_LIMIT = "rate_limit"

# --- Per-namespace schema versions ---
# Bump on Report-shape changes (e.g. new tier band, badge schema rev, etc.).
# Only the report namespace gets versioned today — GH responses are GitHub's
# contract, narrative/lock/budget/rate_limit are scalars or opaque text.
REPORT_SCHEMA_VERSION = 1

# --- TTLs (seconds) ---

TTL_REPORT_SECONDS = 21_600  # 6 hours
TTL_LOCK_SECONDS = 30  # singleflight lock — outlives a real ingest
TTL_NARRATIVE_SECONDS = 86_400  # 24 hours
TTL_BUDGET_KEY_SECONDS = 90_000  # 25 hours — outlives the UTC day rollover


# --- Per-endpoint GitHub TTLs ---
# Matched in order; first hit wins.
_GH_TTL_RULES: tuple[tuple[re.Pattern[str], int], ...] = (
    (re.compile(r"/repos/[^/]+/[^/]+/commits"), 300),  # commits — hottest
    (re.compile(r"/repos/[^/]+/[^/]+/languages"), 3600),
    (re.compile(r"/repos/[^/]+/[^/]+/contents"), 1800),
    (re.compile(r"/users/[^/]+/repos$"), 900),  # repo list
    (re.compile(r"/users/[^/]+$"), 3600),  # user profile
    (re.compile(r"/graphql$"), 900),
)


def ttl_for_gh_endpoint(url: str) -> int | None:
    """Returns TTL in seconds for a known GitHub endpoint, or None if unknown.

    None means: do not cache (or let the caller fall back to a default TTL).
    """
    for pat, ttl in _GH_TTL_RULES:
        if pat.search(url):
            return ttl
    return None


# --- Key builders ---


def report_key(username: str) -> str:
    """Layer A Report cache key, namespaced by REPORT_SCHEMA_VERSION so a
    future Report-shape change can invalidate the report namespace cleanly.
    Composed final key under RedisCache._build_key:
        si:v1:report:v{REPORT_SCHEMA_VERSION}:<lowercased-username>
    """
    return f"v{REPORT_SCHEMA_VERSION}:{username.lower()}"


def rate_limit_key(name: str, *, user_id: int, hour_bucket: str) -> str:
    """Compose a rate-limit counter key. `name` namespaces the counter so a
    single user can have separate caps per feature (force_refresh, analyze, ...).
    `hour_bucket` is the bucket label (e.g. UTC hour) the caller chose."""
    return f"{name}:{user_id}:{hour_bucket}"


def narrative_key(username: str, scores_hash: str, mode: str) -> str:
    return f"{username}:{scores_hash}:{mode}"


def budget_day_key(name: str, now: datetime) -> str:
    return f"{name}:{now.strftime('%Y-%m-%d')}"


def gh_request_key(
    method: str,
    url: str,
    params: dict[str, Any] | None,
    body: Any | None,
) -> str:
    """Hash-stable cache key for a GitHub request.

    Key order independence is critical — two requests that differ only in
    URL-param ordering must hit the same cache entry. JSON `sort_keys=True`
    handles params + body.
    """
    payload = {
        "method": method.upper(),
        "url": url,
        "params": params or {},
        "body": body or {},
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    return f"{method.upper()}:{digest}"
