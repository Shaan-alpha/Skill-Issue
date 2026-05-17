import asyncio
import os
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine


def _run_alembic(command_name: str, target: str) -> None:
    """Run an alembic command in a thread-isolated call.

    asyncio.run() inside env.py requires a fresh thread with no running event
    loop — calling it from an async test directly raises RuntimeError.  We
    run alembic in a ThreadPoolExecutor thread where the event loop is absent.
    DATABASE_DIRECT_URL is set on the main process env before the thread starts.
    """
    from alembic import command as alembic_command
    from alembic.config import Config

    cfg = Config("alembic.ini")
    if command_name == "upgrade":
        alembic_command.upgrade(cfg, target)
    elif command_name == "downgrade":
        alembic_command.downgrade(cfg, target)
    else:
        raise ValueError(f"Unknown alembic command: {command_name}")


@pytest.mark.asyncio
async def test_migration_creates_all_tables(test_database_url, monkeypatch):
    # Set DATABASE_DIRECT_URL so env.py reads it via os.environ directly.
    monkeypatch.setenv("DATABASE_DIRECT_URL", test_database_url)
    # Ensure it is set before spawning threads.
    os.environ["DATABASE_DIRECT_URL"] = test_database_url

    loop = asyncio.get_event_loop()

    # Wipe the schema to a clean slate before running alembic — prior test runs
    # (or the db fixture) may have left tables behind.
    engine = create_async_engine(test_database_url, connect_args={"statement_cache_size": 0})
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
    await engine.dispose()

    # --- upgrade ---
    with ThreadPoolExecutor(max_workers=1) as pool:
        await loop.run_in_executor(pool, _run_alembic, "upgrade", "head")

    engine = create_async_engine(test_database_url, connect_args={"statement_cache_size": 0})
    async with engine.connect() as conn:
        tables = await conn.run_sync(lambda c: set(inspect(c).get_table_names()))
    await engine.dispose()
    assert tables >= {"users", "sessions", "analyses", "analysis_runs", "narratives"}

    # --- downgrade ---
    with ThreadPoolExecutor(max_workers=1) as pool:
        await loop.run_in_executor(pool, _run_alembic, "downgrade", "base")

    engine = create_async_engine(test_database_url, connect_args={"statement_cache_size": 0})
    async with engine.connect() as conn:
        tables = await conn.run_sync(lambda c: set(inspect(c).get_table_names()))
    await engine.dispose()
    # alembic_version table may remain after downgrade — that's fine
    assert (
        tables.intersection({"users", "sessions", "analyses", "analysis_runs", "narratives"})
        == set()
    )
