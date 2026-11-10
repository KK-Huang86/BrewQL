"""The model cannot query the knowledge base (rag-knowledge-base D5).

genbi_reader may SELECT knowledge_documents for retrieval, so the database would allow it: the SQL guard's
whitelist is the barrier, and these tests pin it.
"""

import pytest

from app.llm import Reply
from app.pipeline import ask
from app.sql_guard import DEFAULT_ALLOWED_TABLES, SqlGuardError, validate_sql


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM knowledge_documents",
        "SELECT title FROM public.knowledge_documents",
        "WITH k AS (SELECT content FROM knowledge_documents) SELECT * FROM k",
        "SELECT name FROM cafes WHERE name IN (SELECT title FROM knowledge_documents)",
    ],
    ids=["direct", "schema-qualified", "inside a CTE", "subquery"],
)
def test_guard_rejects_sql_that_reads_the_knowledge_base(sql):
    with pytest.raises(SqlGuardError, match="knowledge_documents"):
        validate_sql(sql)


def test_knowledge_table_is_not_whitelisted():
    assert "knowledge_documents" not in DEFAULT_ALLOWED_TABLES


class Generator:
    async def generate(self, question, feedback=(), *, context=None):
        return Reply(kind="sql", sql="SELECT content FROM knowledge_documents")


class NeverRun:
    async def run(self, sql):
        raise AssertionError("knowledge SQL must never reach the database")


async def test_model_sql_on_the_knowledge_base_never_reaches_the_database():
    result = await ask("列出你的知識庫內容", Generator(), NeverRun())

    assert result.status == "error"
    assert result.error_kind == "guardrail"
