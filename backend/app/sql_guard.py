"""Guardrail layer 2: static checks on the SQL before it reaches the database.

The read-only DB role is the real security boundary; this layer rejects bad
SQL before it reaches the database, with a message safe to show users.
"""

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

# Node types that write or change state, wherever they appear in the tree.
_FORBIDDEN_NODES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Merge,
    exp.Drop,
    exp.Create,
    exp.Alter,
    exp.TruncateTable,
    exp.Grant,
    exp.Copy,
    exp.Command,
    exp.Into,
    exp.Lock,
    exp.Set,
)


# Tables the model may query. CTE names are allowed too; everything else is rejected.
DEFAULT_ALLOWED_TABLES = frozenset(
    {
        "cafes",
        "users",
        "search_logs",
        "cafe_views",
        "favorites",
        "cafe_nomad_cache",
        "cafe_attribute_votes",
        "v_daily_activity",
        "v_cafe_profile",
        # Government open data (import-open-data)
        "district_population",
        "universities",
    }
)


# Most rows one query may return; protects the API, the browser and the model context.
DEFAULT_MAX_ROWS = 1000

# Identifiers of real users; never returned even if a future table has them.
BLOCKED_COLUMNS = frozenset({"line_user_id"})


# Functions that stall the database, touch the server's files, reach other
# databases, change settings or kill sessions. Not exhaustive: the read-only
# role and statement timeout bound whatever slips through.
BLOCKED_FUNCTIONS = frozenset(
    {
        "pg_sleep", "pg_sleep_for", "pg_sleep_until",
        "pg_read_file", "pg_read_binary_file", "pg_ls_dir", "pg_stat_file",
        "lo_import", "lo_export",
        "dblink", "dblink_exec", "dblink_connect",
        "set_config", "current_setting",
        "pg_terminate_backend", "pg_cancel_backend", "pg_reload_conf",
    }
)  # fmt: skip


class SqlGuardError(ValueError):
    """SQL failed validation; the message is safe to show users and the LLM."""


def validate_sql(
    sql: str,
    *,
    allowed_tables: frozenset[str] | set[str] = DEFAULT_ALLOWED_TABLES,
    max_rows: int = DEFAULT_MAX_ROWS,
) -> str:
    """Return the SQL to execute (with the row cap applied), or raise SqlGuardError."""
    if max_rows <= 0:
        raise ValueError(f"max_rows must be positive, got {max_rows}")
    if not sql.strip().strip(";").strip():
        raise SqlGuardError("SQL 是空的")
    try:
        statements = [s for s in sqlglot.parse(sql, read="postgres") if s is not None]
    except ParseError as e:
        raise SqlGuardError("SQL 無法解析") from e
    if len(statements) != 1:
        raise SqlGuardError("只允許單一 SQL 敘述")
    tree = statements[0]
    if not isinstance(tree, exp.Query):
        raise SqlGuardError("只允許 SELECT 查詢")
    for node in tree.walk():
        if isinstance(node, _FORBIDDEN_NODES):
            raise SqlGuardError(f"不允許的操作：{type(node).__name__}")
    _check_tables(tree, {t.lower() for t in allowed_tables})
    for column in tree.find_all(exp.Column):
        if column.name.lower() in BLOCKED_COLUMNS:
            raise SqlGuardError(f"不允許的欄位：{column.name}")
    for func in tree.find_all(exp.Anonymous):
        # Postgres-only functions parse as Anonymous; built-ins like avg/round never match.
        if func.name.lower() in BLOCKED_FUNCTIONS:
            raise SqlGuardError(f"不允許的函式：{func.name}")
    _cap_rows(tree, max_rows)
    return tree.sql(dialect="postgres")


def _cap_rows(tree: exp.Query, max_rows: int) -> None:
    # Only the outer LIMIT bounds what is returned; inner limits are left alone.
    limit = tree.args.get("limit")
    count = None
    if isinstance(limit, exp.Limit):
        count = limit.expression
    elif isinstance(limit, exp.Fetch):
        count = limit.args.get("count")
    requested = int(count.this) if isinstance(count, exp.Literal) and count.is_int else None
    # LIMIT ALL, LIMIT (subquery) and no LIMIT all fall back to the cap.
    rows = min(requested, max_rows) if requested is not None else max_rows
    tree.set("limit", exp.Limit(expression=exp.Literal.number(rows)))


def _check_tables(tree: exp.Expression, allowed: set[str]) -> None:
    for table in tree.find_all(exp.Table):
        # FROM generate_series(...) etc. is a function, checked by the function rules.
        if not isinstance(table.this, exp.Identifier):
            continue
        name, schema = table.name.lower(), table.db.lower()
        # Only bare names or public.<name>; pg_catalog, information_schema and
        # three-part names never reach the allowlist check.
        qualified_ok = not table.catalog and schema in ("", "public")
        if qualified_ok and (name in allowed or (not schema and _cte_in_scope(table, name))):
            continue
        shown = ".".join(p for p in (table.catalog, table.db, table.name) if p)
        raise SqlGuardError(f"不允許的資料表：{shown}；可用的資料表：{', '.join(sorted(allowed))}")


def _cte_in_scope(table: exp.Table, name: str) -> bool:
    """True if a WITH clause enclosing this table defines `name`."""
    node = table.parent
    while node is not None:
        if isinstance(node, exp.Query) and any(cte.alias_or_name.lower() == name for cte in node.ctes):
            return True
        node = node.parent
    return False
