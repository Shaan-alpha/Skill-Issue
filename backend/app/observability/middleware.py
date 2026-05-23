"""ASGI middleware that stamps each request with a UUID4 request_id.

The ID is:
- Honoured from the incoming `X-Request-ID` header when present and valid UUID.
- Generated fresh otherwise.
- Bound into structlog's contextvars for the duration of the request.
- Bound into Sentry's scope (the integration picks it up automatically).
- Echoed back to the client in the `X-Request-ID` response header.

Pure ASGI (no Starlette imports) so it composes cleanly under any framework
and stays cheap on the hot path.
"""

from __future__ import annotations

import uuid

import sentry_sdk
import structlog


def _coerce_uuid(value: str | None) -> str:
    if value:
        try:
            return str(uuid.UUID(value.strip()))
        except (ValueError, AttributeError):
            pass
    return str(uuid.uuid4())


class RequestIDMiddleware:
    """Pure-ASGI middleware that owns the request_id contract."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = None
        for name, value in scope.get("headers", []):
            if name == b"x-request-id":
                try:
                    incoming = value.decode("ascii", errors="ignore")
                except Exception:
                    incoming = None
                break

        request_id = _coerce_uuid(incoming)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Sentry scope per-request — automatic with the new isolation_scope API.
        with sentry_sdk.isolation_scope() as scope_:
            scope_.set_tag("request_id", request_id)

            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))
                    headers.append((b"x-request-id", request_id.encode("ascii")))
                    message["headers"] = headers
                await send(message)

            try:
                await self.app(scope, receive, send_wrapper)
            finally:
                structlog.contextvars.clear_contextvars()
