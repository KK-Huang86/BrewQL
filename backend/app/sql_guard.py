"""Guardrail layer 2 (minimal): accept only a single read-only SELECT.

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


class SqlGuardError(ValueError):
    """SQL failed validation; the message is safe to show users and the LLM."""


def validate_sql(sql: str) -> str:
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
    return sql
