import pytest

from app.db import QueryError


async def test_select_returns_columns_and_rows(executor):
    columns, rows = await executor.run("SELECT city, count(*) AS n FROM cafes GROUP BY city ORDER BY city")
    assert columns == ["city", "n"]
    assert rows == [["台北市", 160], ["新北市", 40]]


async def test_empty_result_still_has_column_names(executor):
    columns, rows = await executor.run("SELECT name, rating FROM cafes WHERE city = '高雄市'")
    assert columns == ["name", "rating"]
    assert rows == []


@pytest.mark.parametrize("sql", ["DELETE FROM cafes", "UPDATE cafes SET rating = 1", "CREATE TABLE t (i int)"])
async def test_database_refuses_writes_even_without_the_sql_guard(executor, sql):
    with pytest.raises(QueryError):
        await executor.run(sql)
    _, rows = await executor.run("SELECT count(*) FROM cafes")
    assert rows == [[200]]


async def test_database_error_becomes_query_error(executor):
    with pytest.raises(QueryError, match="no_such_column"):
        await executor.run("SELECT no_such_column FROM cafes")


async def test_lazy_pool_lets_executor_start_without_a_database():
    from app.db import PgExecutor

    ex = PgExecutor("postgresql://nobody:x@127.0.0.1:1/none")
    await ex.close()


@pytest.mark.parametrize(
    "sql",
    ["DELETE FROM cafes", "INSERT INTO cafes (name) VALUES ('x')", "CREATE TABLE t (i int)"],
)
async def test_reader_role_itself_cannot_write_even_outside_read_only_transaction(reader_dsn, sql):
    # Bypass PgExecutor and lift the read-only default, so only the role's grants are left.
    import asyncpg

    conn = await asyncpg.connect(reader_dsn)
    try:
        # READ WRITE overrides the role's read-only default; rollback keeps the seed data
        # intact even if a regressed grant lets the write through.
        await conn.execute("BEGIN READ WRITE")
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.execute(sql)
    finally:
        await conn.execute("ROLLBACK")
        await conn.close()


async def test_reader_role_has_a_default_statement_timeout(reader_dsn):
    # Protects direct connections that bypass the API's per-query SET LOCAL.
    import asyncpg

    conn = await asyncpg.connect(reader_dsn)
    try:
        assert await conn.fetchval("SHOW statement_timeout") == "5s"
    finally:
        await conn.close()
