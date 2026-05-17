from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.settings import settings


def _build_engine(url: str) -> AsyncEngine:
    return create_async_engine(
        url,
        # asyncpg + pgBouncer transaction pooling: must disable prepared statements.
        connect_args={"statement_cache_size": 0},
        pool_size=5,
        max_overflow=5,
        pool_pre_ping=True,
        pool_recycle=1800,
    )


engine: AsyncEngine = _build_engine(
    settings.database_url
    or "postgresql+asyncpg://placeholder:placeholder@localhost:5432/placeholder"
)

SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine, expire_on_commit=False, autoflush=False
)


async def dispose_engine() -> None:
    await engine.dispose()
