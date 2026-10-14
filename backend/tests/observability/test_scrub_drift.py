"""The frontend and backend scrubbers enforce one PII contract.

docs/OBSERVABILITY.md says both change together; this test holds them to it
by reading the frontend's lists out of scrub.ts.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.observability import sentry as backend

_SCRUB_TS = (
    Path(__file__).resolve().parents[3] / "frontend" / "src" / "observability" / "scrub.ts"
)


def _frontend_list(name: str) -> list[str]:
    text = _SCRUB_TS.read_text(encoding="utf-8")
    match = re.search(rf"export const {name}\s*=\s*\[(.*?)\];", text, re.S)
    if match is None:
        pytest.fail(f"{name} is missing from {_SCRUB_TS}, or is no longer a flat array literal")
    return re.findall(r'"([^"]*)"', match.group(1))


def test_the_header_allowlist_matches_the_frontend() -> None:
    assert _frontend_list("HEADER_ALLOWLIST") == backend._HEADER_ALLOWLIST


def test_the_query_terms_match_the_frontend() -> None:
    assert _frontend_list("QUERY_DENY_TERMS") == backend._QUERY_DENY_TERMS


def test_the_extra_keys_match_the_frontend() -> None:
    assert set(_frontend_list("SCRUB_EXTRA_KEYS")) == backend._SCRUB_EXTRA_KEYS


def test_the_filtered_marker_matches_the_frontend() -> None:
    text = _SCRUB_TS.read_text(encoding="utf-8")
    assert f'export const FILTERED = "{backend._FILTERED}";' in text
