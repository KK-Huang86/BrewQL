"""Real cafes mostly do not say whether pets are welcome; the schema must keep that unknown (import-real-cafes D8)."""

import asyncpg


async def test_pet_columns_accept_unknown(owner_dsn):
    conn = await asyncpg.connect(owner_dsn)
    try:
        async with conn.transaction():
            row = await conn.fetchrow(
                "INSERT INTO cafes (place_id, name, address, pet_friendly, has_pet) "
                "VALUES ('test-unknown-pets', '測試咖啡', '台北市大安區測試路 1 號', NULL, NULL) "
                "RETURNING pet_friendly, has_pet"
            )
            assert (row["pet_friendly"], row["has_pet"]) == (None, None)
            raise _Rollback
    except _Rollback:
        pass
    finally:
        await conn.close()


async def test_demo_cafes_still_say_yes_or_no(reader_dsn):
    conn = await asyncpg.connect(reader_dsn)
    try:
        unknown = await conn.fetchval("SELECT count(*) FROM cafes WHERE pet_friendly IS NULL OR has_pet IS NULL")
    finally:
        await conn.close()
    assert unknown == 0


class _Rollback(Exception):
    """Raised inside the transaction so the test row is never kept."""
