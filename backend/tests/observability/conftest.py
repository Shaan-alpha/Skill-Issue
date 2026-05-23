"""Test fixtures for the observability suite."""

from __future__ import annotations

import pytest
import structlog


@pytest.fixture(autouse=True)
def _clear_structlog_contextvars():
    """Guarantee a clean contextvars state before AND after each test.

    Without this, a mid-flight assertion failure inside a test would leak
    its bound request_id into the next test's setup, producing flaky
    inter-test contamination.
    """
    structlog.contextvars.clear_contextvars()
    yield
    structlog.contextvars.clear_contextvars()
