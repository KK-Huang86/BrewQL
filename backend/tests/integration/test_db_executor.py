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
