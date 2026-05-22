"""structlog config + request_id contextvar helpers.

JSON renderer in prod (one JSON object per line, parseable by every log
aggregator). ConsoleRenderer in dev (coloured, single-line, human readable).

The `request_id` field is bound by RequestIDMiddleware (see `middleware.py`)
and propagates into every structlog call within the request scope via
`structlog.contextvars`.
"""
from __future__ import annotations

import logging
import sys
from typing import IO, Literal

import structlog


def init_logging(
    *,
    level: str = "INFO",
    log_format: Literal["json", "console"] = "json",
    stream: IO[str] | None = None,
) -> None:
    """Configure structlog + the stdlib root logger.

    Call once at process startup. Idempotent — repeated calls reconfigure.
    """
    timestamper = structlog.processors.TimeStamper(fmt="iso")
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if log_format == "json":
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=False)

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=stream or sys.stdout),
        cache_logger_on_first_use=False,
    )

    # Mirror stdlib logging into structlog so libraries (httpx, uvicorn,
    # asyncpg, etc.) end up in the same JSON stream.
    logging.basicConfig(
        format="%(message)s",
        stream=stream or sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
        force=True,
    )


def get_request_id() -> str | None:
    """Return the current request_id from structlog's contextvars, or None."""
    return structlog.contextvars.get_contextvars().get("request_id")
