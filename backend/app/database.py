import asyncpg
from typing import AsyncGenerator
from app.config import settings

# Global connection pool — created once at startup, reused across requests
_pool: asyncpg.Pool | None = None


async def init_pool() -> asyncpg.Pool:
    global _pool
    _pool = await asyncpg.create_pool(
        settings.DATABASE_URL,
        min_size=2,
        max_size=10,
        command_timeout=30,
        statement_cache_size=0,
    )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def get_db() -> AsyncGenerator[asyncpg.Connection, None]:
    """
    FastAPI dependency. Acquires a connection from the pool per request.
    Automatically returns it when the request finishes.
    """
    if _pool is None:
        raise RuntimeError("Database pool not initialised. Call init_pool() at startup.")

    async with _pool.acquire() as connection:
        # Set workspace context for RLS before any query runs
        # This is overridden per-request in the auth dependency
        yield connection