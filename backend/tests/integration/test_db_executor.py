import pytest

from app.db import QueryError


async def test_select_returns_columns_and_rows(executor):
    columns, rows = await executor.run("SELECT city, count(*) AS n FROM cafes GROUP BY city ORDER BY city")
    assert columns == ["city", "n"]
    assert rows == [["台北市", 160], ["新北市", 40]]


@pytest.mark.parametrize(
    ("sql", "expected"),
    [
        ("SELECT count(*) FROM users", 2000),
        ("SELECT count(*) > 45000 FROM search_logs", True),
        ("SELECT count(*) > 150 FROM v_daily_activity", True),
    ],
)
async def test_reader_can_query_members_searches_and_daily_activity(executor, sql, expected):
    _, rows = await executor.run(sql)
    assert rows == [[expected]]


@pytest.mark.parametrize(
    ("sql", "expected"),
    [
        ("SELECT count(*) > 0 FROM favorites", True),
        ("SELECT count(*) > 150000 FROM cafe_views", True),
        ("SELECT count(*) FROM cafe_nomad_cache", 140),
        ("SELECT count(*) > 0 FROM cafe_attribute_votes", True),
        ("SELECT count(*) FROM v_cafe_profile", 200),
    ],
)
async def test_reader_can_query_views_favorites_and_community_ratings(executor, sql, expected):
    # Spec (ticket 8): genbi_reader is granted SELECT on the new tables and view.
    _, rows = await executor.run(sql)
    assert rows == [[expected]]


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


async def test_each_query_gets_its_own_statement_timeout(reader_dsn):
    # 300ms is far below the role's 5s default, so only SET LOCAL can stop this.
    import time

    from app.db import PgExecutor

    ex = PgExecutor(reader_dsn, statement_timeout_ms=300)
    try:
        started = time.monotonic()
        with pytest.raises(QueryError, match="QueryCanceled"):
            await ex.run("SELECT pg_sleep(2)")
        assert time.monotonic() - started < 1.5
        # The connection goes back to the pool healthy and the next query works.
        _, rows = await ex.run("SELECT count(*) FROM cafes")
        assert rows == [[200]]
    finally:
        await ex.close()


async def test_timeout_is_marked_so_the_pipeline_does_not_retry_it(reader_dsn):
    from app.db import PgExecutor

    ex = PgExecutor(reader_dsn, statement_timeout_ms=300)
    try:
        with pytest.raises(QueryError) as timed_out:
            await ex.run("SELECT pg_sleep(2)")
        with pytest.raises(QueryError) as plain:
            await ex.run("SELECT no_such_column FROM cafes")
    finally:
        await ex.close()

    assert timed_out.value.timed_out is True
    assert plain.value.timed_out is False
