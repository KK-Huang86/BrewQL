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
DEFAULT_ALLOWED_TABLES = frozenset({"cafes"})


class SqlGuardError(ValueError):
    """SQL failed validation; the message is safe to show users and the LLM."""


def validate_sql(sql: str, *, allowed_tables: frozenset[str] | set[str] = DEFAULT_ALLOWED_TABLES) -> str:
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
    return sql


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
        with_ = node.args.get("with_") if isinstance(node, exp.Query) else None
        if with_ and any(cte.alias_or_name.lower() == name for cte in with_.expressions):
            return True
        node = node.parent
    return False
