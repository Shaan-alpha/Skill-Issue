from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import app.settings as settings_module


def _normalize_async_url(url: str) -> tuple[str, bool]:
    """Coerce common Neon/Postgres URL schemes to the SQLAlchemy asyncpg dialect.

    Neon's Vercel integration emits `postgres://...` and `postgresql://...`;
    neither resolves to the asyncpg driver. Strip any sync `psycopg2`/`psycopg`
    suffix and ensure the `+asyncpg` driver is present.

    Returns (normalized_url, ssl_required). `ssl_required` is True when the
    original URL signalled TLS (`sslmode=require|verify-*`) — asyncpg uses
    its own `ssl` connect arg rather than libpq's `sslmode` query param.
    """
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]
    elif url.startswith("postgresql+psycopg2://"):
        url = "postgresql+asyncpg://" + url[len("postgresql+psycopg2://") :]
    elif url.startswith("postgresql+psycopg://"):
        url = "postgresql+asyncpg://" + url[len("postgresql+psycopg://") :]

    # libpq-only query params that asyncpg does NOT accept. Strip them so the
    # connect call doesn't raise TypeError("unexpected keyword argument …").
    libpq_only_keys = {
        "sslmode",
        "sslcompression",
        "sslcert",
        "sslkey",
        "sslrootcert",
        "sslcrl",
        "sslcrldir",
        "sslpassword",
        "channel_binding",
        "gssencmode",
        "target_session_attrs",
        "krbsrvname",
        "service",
        "options",
    }

    ssl_required = False
    if "?" in url:
        base, qs = url.split("?", 1)
        kept: list[str] = []
        for kv in qs.split("&"):
            if "=" in kv:
                key, value = kv.split("=", 1)
            else:
                key, value = kv, ""
            key_lower = key.lower()
            if key_lower == "sslmode" and value.lower() in {
                "require",
                "verify-ca",
                "verify-full",
                "prefer",
            }:
                ssl_required = True
            if key_lower in libpq_only_keys:
                continue
            kept.append(kv)
        url = base + (f"?{'&'.join(kept)}" if kept else "")
    return url, ssl_required


def _build_engine(url: str) -> AsyncEngine:
    normalized, ssl_required = _normalize_async_url(url)
    connect_args: dict[str, object] = {"statement_cache_size": 0}
    if ssl_required:
        connect_args["ssl"] = True
    return create_async_engine(
        normalized,
        connect_args=connect_args,
        pool_size=settings_module.settings.db_pool_size,
        max_overflow=settings_module.settings.db_max_overflow,
        pool_pre_ping=True,
        pool_recycle=1800,
    )


engine: AsyncEngine = _build_engine(
    settings_module.settings.database_url
    or "postgresql+asyncpg://placeholder:placeholder@localhost:5432/placeholder"
)

SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine, expire_on_commit=False, autoflush=False
)


async def dispose_engine() -> None:
    await engine.dispose()
