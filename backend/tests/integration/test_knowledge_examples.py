"""Every example in the repo runs as genbi_reader and finds rows, so the model never learns from a broken query."""

import pytest

from app.knowledge import KNOWLEDGE_DIR, load_knowledge
from app.sql_guard import validate_sql

EXAMPLES = [d for d in load_knowledge(KNOWLEDGE_DIR) if d.kind == "example"]


@pytest.mark.parametrize("example", EXAMPLES, ids=[d.id for d in EXAMPLES])
async def test_example_runs_and_finds_rows(executor, example):
    columns, rows = await executor.run(validate_sql(example.content))

    # An empty result usually means a wrong literal (e.g. '台北' for '台北市'): a bad lesson for the model.
    assert columns
    assert rows
