"""Run validated SQL on Postgres as the read-only role, inside a read-only transaction."""

import asyncio
from typing import Any

import asyncpg


class QueryError(Exception):
    """The database rejected or failed the query; the message is safe to show."""


class PgExecutor:
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None
        self._lock = asyncio.Lock()

    async def _get_pool(self) -> asyncpg.Pool:
        # Created on first query so the app (and tests) can start without a database.
        async with self._lock:
            if self._pool is None:
                self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=5)
        return self._pool

    async def run(self, sql: str) -> tuple[list[str], list[list[Any]]]:
        pool = await self._get_pool()
        try:
            # Read-only transaction is a second barrier on top of the role's grants.
            async with pool.acquire() as conn, conn.transaction(readonly=True):
                # A prepared statement exposes column names even when no rows match.
                stmt = await conn.prepare(sql)
                columns = [a.name for a in stmt.get_attributes()]
                records = await stmt.fetch()
        except asyncpg.PostgresError as e:
            raise QueryError(f"{type(e).__name__}: {e}") from e
        return columns, [list(r.values()) for r in records]

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
