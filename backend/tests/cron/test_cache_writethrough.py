"""Verify cron's write-through contract for Layer A.

The real cache write happens inside `_fetch_report` (which calls
`_live_ingest` and then `cache.set_json`). This test stubs `_fetch_report`,
so no cache write occurs here — that's the point. The assertion documents:
"run_refresh_chunk delegates cache writes to _fetch_report; if a future
refactor moves the write back into the orchestrator, this test (and its
comment) flag it for review."

The upstream contract — that `_live_ingest`'s wrapper writes through Layer
A — is already covered by
tests/test_report_cache.py::test_second_call_hits_cache_not_live_ingest.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.cache.keys import NAMESPACE_REPORT, report_key
from app.cron import refresh as refresh_module
from app.cron.tokens import TokenSource


async def test_refresh_one_delegates_cache_write_to_fetch_report(monkeypatch, fake_cache):
    """After run_refresh_chunk runs with _fetch_report stubbed, Layer A holds
    nothing — confirming the orchestrator itself does NOT write the cache.
    """
    analysis = SimpleNamespace(id=1, target_login="octocat", user_id=1)

    monkeypatch.setattr(refresh_module, "_fetch_stale_analyses", AsyncMock(return_value=[analysis]))
    monkeypatch.setattr(
        refresh_module,
        "_resolve_token",
        AsyncMock(return_value=("tok", TokenSource.APP_FALLBACK)),
    )

    canned_report = SimpleNamespace(
        username="octocat",
        total=42,
        tier=SimpleNamespace(name="Hobbyist"),
        model_dump=lambda mode="json": {
            "username": "octocat",
            "total": 42,
            "tier": {"name": "Hobbyist"},
        },
        model_dump_json=lambda: '{"username":"octocat","total":42,"tier":{"name":"Hobbyist"}}',
    )
    monkeypatch.setattr(refresh_module, "_fetch_report", AsyncMock(return_value=canned_report))
    monkeypatch.setattr(refresh_module, "_record_run", AsyncMock(return_value=None))

    db = SimpleNamespace(commit=AsyncMock(return_value=None))

    summary = await refresh_module.run_refresh_chunk(db, limit=5, deadline_seconds=10)
    assert summary.succeeded == 1

    # Stubbed _fetch_report doesn't write — confirms the orchestrator itself
    # does no caching. If the real _fetch_report changes to skip the cache,
    # tests/test_report_cache.py will catch it.
    cached = await fake_cache.get_json(NAMESPACE_REPORT, report_key("octocat"))
    assert cached is None
