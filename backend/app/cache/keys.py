"""Cache key namespaces, TTL constants, and key-building helpers.

Single source of truth for every Redis key the codebase reads or writes.
Bumping `KEY_PREFIX` in `app/cache/client.py` invalidates every namespace at
once on schema changes.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any

# --- Namespaces (the first segment after the version prefix) ---

NAMESPACE_REPORT = "report"
NAMESPACE_LOCK = "lock"
NAMESPACE_GH = "gh"
NAMESPACE_NARRATIVE = "narrative"
NAMESPACE_BUDGET = "budget"

# --- TTLs (seconds) ---

TTL_REPORT_SECONDS = 21_600        # 6 hours
TTL_LOCK_SECONDS = 30              # singleflight lock — outlives a real ingest
TTL_NARRATIVE_SECONDS = 86_400     # 24 hours
TTL_BUDGET_KEY_SECONDS = 90_000    # 25 hours — outlives the UTC day rollover


# --- Per-endpoint GitHub TTLs ---
# Matched in order; first hit wins.
_GH_TTL_RULES: tuple[tuple[re.Pattern[str], int], ...] = (
    (re.compile(r"/repos/[^/]+/[^/]+/commits"), 300),       # commits — hottest
    (re.compile(r"/repos/[^/]+/[^/]+/languages"), 3600),
    (re.compile(r"/repos/[^/]+/[^/]+/contents"), 1800),
    (re.compile(r"/users/[^/]+/repos$"), 900),              # repo list
    (re.compile(r"/users/[^/]+$"), 3600),                   # user profile
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
    return username.lower()


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
