"""Write a real cafe batch into an empty real-mode database (import-real-cafes D3).

Runs only in the one-shot cafe-import container as the database owner; the API never imports it.
"""

import asyncio
from pathlib import Path

import asyncpg

from app.real_cafes import RealBatch

# Simulated members and behaviour, written in the same transaction (D9).
REAL_BEHAVIOR_SQL = (Path(__file__).parent / "real_behavior.sql").read_text(encoding="utf-8")

_HAS_CAFES = "SELECT EXISTS (SELECT 1 FROM cafes)"

_INSERT_CAFE = """
INSERT INTO cafes (place_id, name, address, city, district, rating, user_ratings_total,
                   has_socket, limited_time, pet_friendly, has_pet, created_at, lat, lng)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
"""
_INSERT_VOTE = """
INSERT INTO cafe_attribute_votes (cafe_id, attribute, value, source, created_at)
VALUES ($1, $2, $3, $4, $5)
"""
_INSERT_NOMAD = """
INSERT INTO cafe_nomad_cache (cafe_id, cafenomad_id, name, wifi, seat, quiet, tasty, cheap, music,
                              socket, limited_time, standing_desk, mrt, synced_at)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
"""


class PgRealCafeStore:
    def __init__(self, dsn: str, *, statement_timeout_ms: int = 120_000):
        if statement_timeout_ms <= 0:
            raise ValueError(f"statement_timeout_ms must be positive, got {statement_timeout_ms}")
        self._dsn = dsn
        self._statement_timeout_ms = statement_timeout_ms
        self._pool: asyncpg.Pool | None = None
        self._lock = asyncio.Lock()

    async def _get_pool(self) -> asyncpg.Pool:
        async with self._lock:
            if self._pool is None:
                # Created on first use: demo mode never connects.
                self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=1, timeout=10)
        return self._pool

    async def has_cafes(self) -> bool:
        pool = await self._get_pool()
        return bool(await pool.fetchval(_HAS_CAFES))

    async def write(self, batch: RealBatch) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn, conn.transaction():
            await conn.execute(f"SET LOCAL statement_timeout = {int(self._statement_timeout_ms)}")
            # Two imports at once: the second waits here, then finds cafes and fails the check below.
            await conn.execute("LOCK TABLE cafes IN EXCLUSIVE MODE")
            if await conn.fetchval(_HAS_CAFES):
                raise RuntimeError("cafes appeared during the import; nothing written")
            await conn.executemany(
                _INSERT_CAFE,
                [
                    (c.place_id, c.name, c.address, *loc, c.rating, c.user_ratings_total,
                     c.has_socket, c.limited_time, c.pet_friendly, c.has_pet, c.created_at, c.lat, c.lng)
                    for c, loc in batch.cafes
                ],
            )  # fmt: skip
            # The database numbers cafes itself; place_id (unique) links the export's ids to the new ones.
            ids_by_place = {r["place_id"]: r["id"] for r in await conn.fetch("SELECT id, place_id FROM cafes")}
            new_id = {c.source_id: ids_by_place[c.place_id] for c, _ in batch.cafes}
            await conn.executemany(
                _INSERT_VOTE,
                [(new_id[v.cafe_source_id], v.attribute, v.value, v.source, v.created_at) for v in batch.votes],
            )
            await conn.executemany(
                _INSERT_NOMAD,
                [
                    (new_id[n.cafe_source_id], n.cafenomad_id, n.name, n.wifi, n.seat, n.quiet, n.tasty,
                     n.cheap, n.music, n.socket, n.limited_time, n.standing_desk, n.mrt, n.synced_at)
                    for n in batch.nomad
                ],
            )  # fmt: skip
            await conn.execute(REAL_BEHAVIOR_SQL)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
