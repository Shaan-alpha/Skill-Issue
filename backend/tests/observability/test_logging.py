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


def test_stdlib_records_render_as_json_with_request_id():
    """Every app module logs through the stdlib. Those lines must carry the
    level, logger, timestamp and request_id that OBSERVABILITY.md promises."""
    buf = StringIO()
    init_logging(level="INFO", log_format="json", stream=buf)
    structlog.contextvars.bind_contextvars(request_id="3f2c6a8e-0000-4000-8000-000000000000")
    try:
        logging.getLogger("app.ratelimit").warning("rate_limit.throttled name=%s", "analyze")
    finally:
        structlog.contextvars.clear_contextvars()
    payload = json.loads(buf.getvalue().strip().splitlines()[-1])
    assert payload["event"] == "rate_limit.throttled name=analyze"
    assert payload["level"] == "warning"
    assert payload["logger"] == "app.ratelimit"
    assert payload["request_id"] == "3f2c6a8e-0000-4000-8000-000000000000"
    assert "timestamp" in payload


def test_stdlib_exceptions_keep_their_traceback():
    buf = StringIO()
    init_logging(level="INFO", log_format="json", stream=buf)
    try:
        raise ValueError("boom")
    except ValueError:
        logging.getLogger("app.cron.refresh").exception("cron record_run failed")
    payload = json.loads(buf.getvalue().strip().splitlines()[-1])
    assert payload["level"] == "error"
    assert "ValueError: boom" in payload["exception"]


def test_httpx_request_lines_are_not_logged_at_info():
    buf = StringIO()
    init_logging(level="INFO", log_format="json", stream=buf)
    logging.getLogger("httpx").info(
        'HTTP Request: GET https://api.github.com/users/x "HTTP/2 200 OK"'
    )
    logging.getLogger("httpcore.http2").info("send_request_headers.started")
    assert buf.getvalue() == ""
