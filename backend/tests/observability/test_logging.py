"""Tests for structlog config + request_id contextvar propagation."""

from __future__ import annotations

import json
import logging
from io import StringIO

import pytest
import structlog

from app.observability.logging import get_request_id, init_logging


def _capture_structlog(log_format: str = "json") -> StringIO:
    """Reset structlog + stdlib logging to a StringIO sink for assertions."""
    buf = StringIO()
    handler = logging.StreamHandler(buf)
    init_logging(level="INFO", log_format=log_format, stream=buf)
    # Replace any existing handlers — init_logging adds one; we want only ours.
    root = logging.getLogger()
    root.handlers = [handler]
    return buf


def test_json_format_emits_one_json_object_per_line():
    buf = _capture_structlog("json")
    log = structlog.get_logger()
    log.info("test_event", foo="bar", count=3)
    line = buf.getvalue().strip().splitlines()[-1]
    payload = json.loads(line)
    assert payload["event"] == "test_event"
    assert payload["foo"] == "bar"
    assert payload["count"] == 3


def test_console_format_is_human_readable_not_json():
    buf = _capture_structlog("console")
    log = structlog.get_logger()
    log.info("test_event", foo="bar")
    line = buf.getvalue().strip().splitlines()[-1]
    with pytest.raises(json.JSONDecodeError):
        json.loads(line)
    assert "test_event" in line
    assert "foo" in line


def test_request_id_propagates_via_contextvars():
    buf = _capture_structlog("json")
    log = structlog.get_logger()

    structlog.contextvars.clear_contextvars()
    assert get_request_id() is None

    structlog.contextvars.bind_contextvars(request_id="abc-123")
    try:
        assert get_request_id() == "abc-123"
        log.info("inside_request")
    finally:
        structlog.contextvars.clear_contextvars()

    payload = json.loads(buf.getvalue().strip().splitlines()[-1])
    assert payload["request_id"] == "abc-123"
    assert get_request_id() is None  # cleared on the way out


def test_nested_call_inherits_request_id():
    buf = _capture_structlog("json")
    log = structlog.get_logger()

    def inner():
        log.info("inner_event")

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id="nested-456")
    try:
        inner()
    finally:
        structlog.contextvars.clear_contextvars()

    payload = json.loads(buf.getvalue().strip().splitlines()[-1])
    assert payload["request_id"] == "nested-456"
