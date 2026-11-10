"""Retrieval (rag-knowledge-base D3): one embedding per question, three kinds searched at once."""

import asyncio
import time

import pytest

from app.retrieval import RetrievalUnavailable, Retrieved, Retriever, TopN

VECTOR = [0.1] * 1024


def hit(doc_id: str, kind: str) -> Retrieved:
    return Retrieved(id=doc_id, kind=kind, title=doc_id, content="內容", distance=0.2)


class FakeEmbedder:
    def __init__(self, error: Exception | None = None):
        self.texts: list[str] = []
        self._error = error

    async def embed(self, text: str) -> list[float]:
        self.texts.append(text)
        if self._error:
            raise self._error
        return VECTOR


class FakeSearch:
    def __init__(self, docs: dict[str, list[Retrieved]] | None = None, *, delay: float = 0, error=None):
        self.calls: list[tuple[list[float], str, int]] = []
        self._docs = docs or {}
        self._delay = delay
        self._error = error

    async def nearest(self, vector: list[float], kind: str, limit: int) -> list[Retrieved]:
        self.calls.append((vector, kind, limit))
        await asyncio.sleep(self._delay)
        if self._error:
            raise self._error
        return self._docs.get(kind, [])[:limit]


async def test_question_is_embedded_once_and_each_kind_gets_its_own_limit():
    embedder, search = FakeEmbedder(), FakeSearch()

    await Retriever(embedder, search, top_n=TopN(schema=4, glossary=3, example=2)).retrieve("工作友善的店有幾家？")

    assert embedder.texts == ["工作友善的店有幾家？"]
    assert sorted(search.calls, key=lambda c: c[1]) == [
        (VECTOR, "example", 2),
        (VECTOR, "glossary", 3),
        (VECTOR, "schema", 4),
    ]


async def test_results_are_grouped_by_kind_in_search_order():
    docs = {
        "schema": [hit("schema-cafes", "schema"), hit("schema-users", "schema")],
        "glossary": [hit("glossary-work", "glossary")],
    }

    result = await Retriever(FakeEmbedder(), FakeSearch(docs)).retrieve("q")

    assert [d.id for d in result.schema] == ["schema-cafes", "schema-users"]
    assert [d.id for d in result.glossary] == ["glossary-work"]
    assert result.example == ()
    assert [d.id for d in result.all()] == ["schema-cafes", "schema-users", "glossary-work"]


def test_default_limits_match_the_spec():
    assert TopN() == TopN(schema=4, glossary=3, example=3)


async def test_the_three_searches_run_concurrently():
    search = FakeSearch(delay=0.1)

    start = time.perf_counter()
    await Retriever(FakeEmbedder(), search).retrieve("q")

    assert len(search.calls) == 3
    assert time.perf_counter() - start < 0.25  # sequential would take 0.3 s


async def test_empty_knowledge_base_returns_empty_groups():
    result = await Retriever(FakeEmbedder(), FakeSearch()).retrieve("q")

    assert (result.schema, result.glossary, result.example) == ((), (), ())


async def test_embedding_failure_is_retrieval_unavailable_and_searches_nothing():
    search = FakeSearch()

    with pytest.raises(RetrievalUnavailable):
        await Retriever(FakeEmbedder(error=RuntimeError("ThrottlingException")), search).retrieve("q")

    assert search.calls == []


async def test_search_failure_is_retrieval_unavailable():
    with pytest.raises(RetrievalUnavailable):
        await Retriever(FakeEmbedder(), FakeSearch(error=OSError("connection refused"))).retrieve("q")


@pytest.mark.parametrize("field", ["schema", "glossary", "example"])
def test_limits_must_be_positive(field):
    with pytest.raises(ValueError, match=field):
        TopN(**{field: 0})
