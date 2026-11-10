"""The knowledge documents in the repo: every queryable table is described and the example count fits the spec."""

from collections import Counter

from app.knowledge import KNOWLEDGE_DIR, load_knowledge
from app.sql_guard import DEFAULT_ALLOWED_TABLES


def test_repo_knowledge_loads():
    assert load_knowledge(KNOWLEDGE_DIR)


def test_every_queryable_table_has_exactly_one_schema_document():
    # One document per table or view, so retrieval returns whole tables, never half a column list.
    schema_ids = [d.id for d in load_knowledge(KNOWLEDGE_DIR) if d.kind == "schema"]

    assert sorted(schema_ids) == sorted(f"schema-{table}" for table in DEFAULT_ALLOWED_TABLES)


def test_kinds_have_the_planned_sizes():
    counts = Counter(d.kind for d in load_knowledge(KNOWLEDGE_DIR))

    assert counts["glossary"] >= 5
    assert 10 <= counts["example"] <= 15
