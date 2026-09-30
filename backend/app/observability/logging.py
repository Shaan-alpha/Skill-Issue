"""structlog config + request_id contextvar helpers.

JSON renderer in prod (one JSON object per line, parseable by every log
aggregator). ConsoleRenderer in dev (coloured, single-line, human readable).

The `request_id` field is bound by RequestIDMiddleware (see `middleware.py`)
and propagates via `structlog.contextvars` into every line logged within the
request: structlog calls and stdlib `logging` records alike, since the root
handler renders stdlib records through the same processors.
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

    # Every application module (and every library) logs through the stdlib.
    # Render those records with the same renderer, so each line carries the
    # level, logger name, timestamp and the request's request_id -- the
    # correlation OBSERVABILITY.md documents. A bare "%(message)s" format
    # (before v1.0.13) dropped all four.
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            timestamper,
        ],
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            renderer,
        ],
    )
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(formatter)
    root = logging.getLogger()
    for existing in list(root.handlers):  # same effect as basicConfig(force=True)
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # httpx logs every outbound request at INFO: hundreds of lines per cron run,
    # each mirrored as a Sentry breadcrumb beside the HttpxIntegration's own.
    for noisy in ("httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_request_id() -> str | None:
    """Return the current request_id from structlog's contextvars, or None."""
    return structlog.contextvars.get_contextvars().get("request_id")
