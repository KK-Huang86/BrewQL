from pathlib import Path

import sqlglot
from sqlglot import exp

from app.schema_context import SCHEMA_CONTEXT

SCHEMA_SQL = Path(__file__).parents[2] / "db" / "init" / "01_schema.sql"


def real_cafes_columns() -> set[str]:
    create = sqlglot.parse_one(SCHEMA_SQL.read_text(), read="postgres")
    return {col.name for col in create.find_all(exp.ColumnDef)}


def test_schema_context_describes_every_cafes_column():
    missing = {c for c in real_cafes_columns() if c not in SCHEMA_CONTEXT}
    assert not missing, f"schema context is missing columns: {missing}"


def test_schema_context_lists_the_enum_values_the_model_must_use():
    for value in ("'yes'", "'maybe'", "'no'", "台北市", "新北市"):
        assert value in SCHEMA_CONTEXT
