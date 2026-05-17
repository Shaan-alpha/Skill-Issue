from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig
from typing import TYPE_CHECKING

from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

from app.db.engine import _normalize_async_url
from app.db.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _resolve_url() -> tuple[str, bool]:
    # Re-read from os.environ directly so that monkeypatch.setenv / os.environ
    # mutations in tests take effect even after the settings singleton was loaded.
    url = os.environ.get("DATABASE_DIRECT_URL")
    if not url:
        raise RuntimeError("DATABASE_DIRECT_URL must be set for migrations")
    return _normalize_async_url(url)


def run_migrations_offline() -> None:
    url, _ssl = _resolve_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    url, ssl_required = _resolve_url()
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = url
    connect_args: dict[str, object] = {"statement_cache_size": 0}
    if ssl_required:
        connect_args["ssl"] = True
    connectable = async_engine_from_config(
        cfg, prefix="sqlalchemy.", future=True, connect_args=connect_args
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
