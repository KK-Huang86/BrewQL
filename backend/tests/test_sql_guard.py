import pytest

from app.sql_guard import SqlGuardError, validate_sql


def test_plain_select_passes():
    assert validate_sql("SELECT name FROM cafes") == "SELECT name FROM cafes"


def test_delete_is_rejected():
    with pytest.raises(SqlGuardError):
        validate_sql("DELETE FROM cafes")


def test_multiple_statements_are_rejected():
    with pytest.raises(SqlGuardError, match="單一"):
        validate_sql("SELECT 1; DELETE FROM cafes")


@pytest.mark.parametrize("sql", ["", "   ", ";", " ; ;"])
def test_empty_sql_is_rejected(sql):
    with pytest.raises(SqlGuardError, match="空"):
        validate_sql(sql)


def test_unparseable_sql_is_rejected():
    with pytest.raises(SqlGuardError, match="無法解析"):
        validate_sql("SELEC name FROM")


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT name FROM cafes WHERE city = '台北市' UNION SELECT name FROM cafes WHERE city = '新北市'",
        "SELECT count(*) FROM cafes;",
        "WITH t AS (SELECT district FROM cafes) SELECT district, count(*) FROM t GROUP BY district",
    ],
)
def test_other_read_only_queries_pass(sql):
    validate_sql(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO cafes (name, address) VALUES ('x', 'y')",
        "UPDATE cafes SET rating = 5",
        "DROP TABLE cafes",
        "TRUNCATE cafes",
        "CREATE TABLE t (i int)",
        "GRANT ALL ON cafes TO PUBLIC",
    ],
)
def test_write_and_ddl_statements_are_rejected(sql):
    with pytest.raises(SqlGuardError):
        validate_sql(sql)


@pytest.mark.parametrize(
    "sql",
    [
        # Postgres allows data-modifying statements inside a CTE of a SELECT.
        "WITH d AS (DELETE FROM cafes RETURNING id) SELECT count(*) FROM d",
        # SELECT INTO creates a new table.
        "SELECT * INTO cafes_copy FROM cafes",
    ],
)
def test_writes_hidden_inside_a_select_are_rejected(sql):
    with pytest.raises(SqlGuardError, match="不允許"):
        validate_sql(sql)
