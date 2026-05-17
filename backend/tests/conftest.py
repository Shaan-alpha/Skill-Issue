"""Shared pytest fixtures for the Skill Issue backend test suite.

Fixtures defined here are available to every test under backend/tests/ without
needing to be imported. Task 2 will add domain-model fixtures (sample_profile,
score_breakdown, etc.); Task 1 only needs the file to exist so the structure
matches the plan.
"""

import os

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Base


@pytest_asyncio.fixture(scope="session")
def test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        raise RuntimeError(
            "TEST_DATABASE_URL must be set. Use a Neon branch or local Postgres. "
            "Example: postgresql+asyncpg://postgres:postgres@localhost:5432/skill_issue_test"
        )
    return url


async def _reset_schema(conn) -> None:
    """Drop and recreate the public schema to give each test a clean slate.

    Using raw SQL avoids SQLAlchemy's use_alter FK teardown issue where
    DROP CONSTRAINT fails if the tables were already absent.
    """
    await conn.execute(text("DROP SCHEMA public CASCADE"))
    await conn.execute(text("CREATE SCHEMA public"))


@pytest_asyncio.fixture
async def db(test_database_url) -> AsyncSession:
    engine = create_async_engine(test_database_url, connect_args={"statement_cache_size": 0})
    async with engine.begin() as conn:
        await _reset_schema(conn)
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
    async with engine.begin() as conn:
        await _reset_schema(conn)
    await engine.dispose()
