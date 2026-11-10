"""Knowledge documents are validated before import, so a typo never reaches the embedding bill or the prompt."""

import pytest

from app.knowledge import KnowledgeDoc, KnowledgeError, load_knowledge

SCHEMA = """
- id: schema-cafes
  title: 資料表 cafes
  content: 咖啡店，每列一家店。
- id: schema-users
  title: 資料表 users
  content: 模擬會員。
"""

GLOSSARY = """
- id: glossary-work-friendly
  title: 工作友善
  content: limited_time IN ('no', 'maybe') AND has_socket IN ('yes', 'maybe')
"""

EXAMPLES = """
- id: example-district-count
  question: 各行政區有幾家咖啡店？
  sql: SELECT district, count(*) FROM cafes GROUP BY district
"""


def write(tmp_path, schema=SCHEMA, glossary=GLOSSARY, examples=EXAMPLES):
    for name, text in [("schema", schema), ("glossary", glossary), ("examples", examples)]:
        if text is not None:
            (tmp_path / f"{name}.yaml").write_text(text, encoding="utf-8")
    return tmp_path


def test_documents_load_in_kind_then_file_order(tmp_path):
    docs = load_knowledge(write(tmp_path))

    assert [d.id for d in docs] == [
        "schema-cafes",
        "schema-users",
        "glossary-work-friendly",
        "example-district-count",
    ]
    assert docs[1] == KnowledgeDoc(id="schema-users", kind="schema", title="資料表 users", content="模擬會員。")
    assert docs[2].kind == "glossary"


def test_an_example_is_titled_by_its_question_and_holds_its_sql(tmp_path):
    example = load_knowledge(write(tmp_path))[-1]

    assert example == KnowledgeDoc(
        id="example-district-count",
        kind="example",
        title="各行政區有幾家咖啡店？",
        content="SELECT district, count(*) FROM cafes GROUP BY district",
    )


def test_an_empty_kind_is_allowed(tmp_path):
    # Deleting every example is a real edit; the import then removes them from the knowledge base.
    docs = load_knowledge(write(tmp_path, examples="[]"))

    assert {d.kind for d in docs} == {"schema", "glossary"}


def test_duplicate_id_across_kinds_stops_the_load(tmp_path):
    glossary = GLOSSARY + "\n- id: schema-cafes\n  title: 重複\n  content: x\n"

    with pytest.raises(KnowledgeError, match="schema-cafes: duplicate id"):
        load_knowledge(write(tmp_path, glossary=glossary))


def test_example_sql_outside_the_whitelist_names_the_document(tmp_path):
    examples = "- id: example-leak\n  question: 看稽核紀錄\n  sql: SELECT * FROM ask_audit\n"

    with pytest.raises(KnowledgeError, match="example-leak: .*ask_audit"):
        load_knowledge(write(tmp_path, examples=examples))


@pytest.mark.parametrize(
    "sql",
    ["DELETE FROM cafes", "SELECT 1; SELECT 2", "SELEC name FROM cafes"],
    ids=["write", "two statements", "unparsable"],
)
def test_example_sql_that_fails_the_guard_stops_the_load(tmp_path, sql):
    examples = f'- id: example-bad\n  question: 壞範例\n  sql: "{sql}"\n'

    with pytest.raises(KnowledgeError, match="example-bad"):
        load_knowledge(write(tmp_path, examples=examples))


@pytest.mark.parametrize(
    ("kind", "text", "reason"),
    [
        ("schema", "- id: schema-x\n  content: 沒有標題\n", "schema-x: missing title"),
        ("glossary", "- id: g\n  title: 名詞\n  content: '  '\n", "g: missing content"),
        ("examples", "- id: e\n  question: 只有問題\n", "e: missing sql"),
        ("schema", "- title: 沒有 ID\n  content: x\n", "schema.yaml entry 1: missing id"),
        ("schema", "- id: s\n  title: t\n  content: c\n  sql: SELECT 1\n", "s: unknown keys sql"),
        ("glossary", "- just a string\n", "glossary.yaml entry 1: must be a mapping"),
        ("examples", "id: e\nquestion: q\n", "examples.yaml must be a list"),
        ("schema", "", "schema.yaml must be a list"),
        ("glossary", "- id: [unclosed\n", "glossary.yaml is not valid YAML"),
    ],
)
def test_malformed_entries_name_the_file_or_document(tmp_path, kind, text, reason):
    with pytest.raises(KnowledgeError, match=reason):
        load_knowledge(write(tmp_path, **{kind: text}))


def test_missing_file_stops_the_load(tmp_path):
    # A missing file would otherwise look like "delete every document of this kind".
    with pytest.raises(KnowledgeError, match="glossary.yaml"):
        load_knowledge(write(tmp_path, glossary=None))
