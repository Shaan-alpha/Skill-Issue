"""Tests for RequestIDMiddleware — header propagation + structlog binding."""
from __future__ import annotations

import uuid
from io import StringIO

import pytest
import structlog
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.observability.logging import get_request_id, init_logging
from app.observability.middleware import RequestIDMiddleware


@pytest.fixture
def app() -> FastAPI:
    buf = StringIO()
    init_logging(level="INFO", log_format="json", stream=buf)
    application = FastAPI()
    application.add_middleware(RequestIDMiddleware)

    @application.get("/ping")
    async def _ping() -> dict[str, str | None]:
        # Read the bound request_id from inside the handler.
        return {"rid": get_request_id()}

    application.state._log_buf = buf  # for tests to inspect
    return application


def test_response_carries_x_request_id_header(app: FastAPI):
    client = TestClient(app)
    response = client.get("/ping")
    assert response.status_code == 200
    rid = response.headers.get("x-request-id")
    assert rid is not None
    uuid.UUID(rid)  # raises if malformed


def test_handler_sees_same_request_id_as_response_header(app: FastAPI):
    client = TestClient(app)
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.headers["x-request-id"] == response.json()["rid"]


def test_each_request_gets_a_fresh_id(app: FastAPI):
    client = TestClient(app)
    r1 = client.get("/ping")
    r2 = client.get("/ping")
    assert r1.headers["x-request-id"] != r2.headers["x-request-id"]


def test_contextvar_is_cleared_between_requests(app: FastAPI):
    structlog.contextvars.clear_contextvars()
    assert get_request_id() is None
    client = TestClient(app)
    client.get("/ping")
    # After the request completes, the middleware should have cleared it.
    assert get_request_id() is None


def test_incoming_x_request_id_is_preserved_when_valid(app: FastAPI):
    client = TestClient(app)
    incoming = "11111111-2222-3333-4444-555555555555"
    response = client.get("/ping", headers={"X-Request-ID": incoming})
    assert response.headers["x-request-id"] == incoming
    assert response.json()["rid"] == incoming


def test_incoming_x_request_id_is_replaced_when_malformed(app: FastAPI):
    client = TestClient(app)
    response = client.get("/ping", headers={"X-Request-ID": "not-a-uuid"})
    rid = response.headers["x-request-id"]
    assert rid != "not-a-uuid"
    uuid.UUID(rid)  # the replacement is a valid UUID


def test_incoming_x_request_id_strips_whitespace(app: FastAPI):
    client = TestClient(app)
    incoming = "11111111-2222-3333-4444-555555555555"
    response = client.get("/ping", headers={"X-Request-ID": f"  {incoming}  "})
    assert response.headers["x-request-id"] == incoming
    assert response.json()["rid"] == incoming
