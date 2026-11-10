"""Prompt context (rag-knowledge-base D8): reply rules always, knowledge static or retrieved."""

from app.retrieval import RetrievalResult, Retrieved
from app.schema_context import REPLY_RULES, SCHEMA_CONTEXT, STATIC_KNOWLEDGE, rag_context
from app.sql_guard import DEFAULT_ALLOWED_TABLES

WORK = Retrieved("glossary-work-friendly", "glossary", "工作友善", "limited_time IN ('no', 'maybe')", 0.3)
CAFES = Retrieved("schema-cafes", "schema", "資料表 cafes：咖啡店（每列一家店）", "- district：行政區", 0.4)
EXAMPLE = Retrieved("example-members", "example", "付費會員有幾位？", "SELECT count(*) FROM users", 0.5)


def test_static_context_is_the_rules_followed_by_the_full_knowledge_unchanged():
    # The static baseline (26/26) must not move: same text, now in two named parts.
    assert REPLY_RULES + STATIC_KNOWLEDGE == SCHEMA_CONTEXT
    assert "## 回覆類型（kind）" in REPLY_RULES
    assert "資料表 cafes" not in REPLY_RULES
    assert STATIC_KNOWLEDGE.lstrip().startswith("## 資料表 cafes")


def test_rag_context_keeps_rules_and_every_table_name_even_with_nothing_retrieved():
    context = rag_context(RetrievalResult())

    assert context.startswith(REPLY_RULES)
    for table in DEFAULT_ALLOWED_TABLES:
        assert table in context, table


def test_rag_context_carries_what_was_retrieved():
    context = rag_context(RetrievalResult(schema=(CAFES,), glossary=(WORK,), example=(EXAMPLE,)))

    assert "## 資料表 cafes：咖啡店（每列一家店）\n\n- district：行政區" in context
    assert "- 工作友善：limited_time IN ('no', 'maybe')" in context
    assert "付費會員有幾位？" in context
    assert "SELECT count(*) FROM users" in context


def test_rag_context_leaves_out_definitions_that_were_not_retrieved():
    context = rag_context(RetrievalResult(glossary=(WORK,)))

    assert "工作友善" in context
    assert "收藏轉換率" not in context
    assert "搜尋落空率" not in context
