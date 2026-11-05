"""Run validated SQL on Postgres as the read-only role, inside a read-only transaction."""

import asyncio
from typing import Any

import asyncpg


class QueryError(Exception):
    """The database rejected the query; the message is raw detail for logs, not for users."""


class DatabaseUnavailable(Exception):
    """Cannot reach or log in to the database; an outage, not a problem with the question."""


class PgExecutor:
    def __init__(self, dsn: str, *, statement_timeout_ms: int = 5000):
        # Postgres treats 0 as "no timeout"; refuse it rather than silently lift the limit.
        if statement_timeout_ms <= 0:
            raise ValueError(f"statement_timeout_ms must be positive, got {statement_timeout_ms}")
        self._dsn = dsn
        self._statement_timeout_ms = statement_timeout_ms
        self._pool: asyncpg.Pool | None = None
        self._lock = asyncio.Lock()

    async def _get_pool(self) -> asyncpg.Pool:
        # Created on first query so the app (and tests) can start without a database.
        async with self._lock:
            if self._pool is None:
                try:
                    self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=5)
                except (OSError, TimeoutError, asyncpg.PostgresError, asyncpg.InterfaceError) as e:
                    # Pool stays None, so the next question retries the connection.
                    raise DatabaseUnavailable(f"{type(e).__name__}: {e}") from e
        return self._pool

    async def run(self, sql: str) -> tuple[list[str], list[list[Any]]]:
        pool = await self._get_pool()
        try:
            # Read-only transaction is a second barrier on top of the role's grants.
            async with pool.acquire() as conn, conn.transaction(readonly=True):
                # SET LOCAL ends with the transaction, so pooled connections never keep it.
                # SET takes no bind parameters; the value is an int checked in __init__.
                await conn.execute(f"SET LOCAL statement_timeout = {int(self._statement_timeout_ms)}")
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
