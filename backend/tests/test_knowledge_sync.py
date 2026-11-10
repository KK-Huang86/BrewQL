"""Knowledge import (rag-knowledge-base D4): re-runs are free, changes land whole or not at all."""

import logging

import pytest

from app.knowledge import KnowledgeDoc
from app.knowledge_sync import EmbeddedDoc, ImportFailed, SyncReport, content_hash, sync_knowledge

MODEL = "amazon.titan-embed-text-v2:0"
DIM = 1024

CAFES = KnowledgeDoc(id="schema-cafes", kind="schema", title="資料表 cafes", content="咖啡店")
WORK = KnowledgeDoc(id="glossary-work", kind="glossary", title="工作友善", content="不限時且有插座")
EXAMPLE = KnowledgeDoc(id="example-count", kind="example", title="有幾家店？", content="SELECT count(*) FROM cafes")


class FakeEmbedder:
    def __init__(self, *, fail_on_call: int | None = None, dimension: int = DIM):
        self.texts: list[str] = []
        self._fail_on_call = fail_on_call
        self._dimension = dimension

    async def embed(self, text: str) -> list[float]:
        self.texts.append(text)
        if len(self.texts) == self._fail_on_call:
            raise RuntimeError("ThrottlingException")
        return [0.1] * self._dimension


class FakeStore:
    """In-memory store: apply() swaps the whole state, like one committed transaction."""

    def __init__(self, docs: dict[str, EmbeddedDoc] | None = None):
        self.docs = dict(docs or {})
        self.applied: list[tuple[list[EmbeddedDoc], list[str]]] = []

    async def hashes(self) -> dict[str, str]:
        return {doc_id: doc.content_hash for doc_id, doc in self.docs.items()}

    async def apply(self, upserts: list[EmbeddedDoc], deletes: list[str]) -> None:
        self.applied.append((upserts, deletes))
        for doc in upserts:
            self.docs[doc.doc.id] = doc
        for doc_id in deletes:
            self.docs.pop(doc_id, None)


async def sync(docs, embedder, store):
    return await sync_knowledge(docs, embedder=embedder, store=store, model_id=MODEL, dimension=DIM)


async def test_first_import_embeds_and_stores_every_document():
    store = FakeStore()

    report = await sync([CAFES, WORK, EXAMPLE], FakeEmbedder(), store)

    assert report == SyncReport(added=3, updated=0, unchanged=0, deleted=0)
    assert set(store.docs) == {"schema-cafes", "glossary-work", "example-count"}
    assert store.docs["glossary-work"].content_hash == content_hash(WORK, MODEL)


async def test_second_run_with_unchanged_documents_calls_no_embedding_and_writes_nothing():
    store = FakeStore()
    await sync([CAFES, WORK], FakeEmbedder(), store)
    embedder = FakeEmbedder()

    report = await sync([CAFES, WORK], embedder, store)

    assert report == SyncReport(added=0, updated=0, unchanged=2, deleted=0)
    assert embedder.texts == []
    assert len(store.applied) == 1  # only the first run wrote


async def test_changed_document_is_re_embedded_and_others_are_left_alone():
    store = FakeStore()
    await sync([CAFES, WORK], FakeEmbedder(), store)
    changed = KnowledgeDoc(id="glossary-work", kind="glossary", title="工作友善", content="新的定義")
    embedder = FakeEmbedder()

    report = await sync([CAFES, changed], embedder, store)

    assert report == SyncReport(added=0, updated=1, unchanged=1, deleted=0)
    assert len(embedder.texts) == 1
    assert store.docs["glossary-work"].doc.content == "新的定義"


async def test_document_removed_from_the_repo_is_deleted():
    store = FakeStore()
    await sync([CAFES, WORK], FakeEmbedder(), store)

    report = await sync([CAFES], FakeEmbedder(), store)

    assert report == SyncReport(added=0, updated=0, unchanged=1, deleted=1)
    assert set(store.docs) == {"schema-cafes"}


async def test_a_new_embedding_model_re_embeds_everything():
    # Vectors from two models are not comparable, so the model is part of the hash.
    store = FakeStore()
    await sync([CAFES], FakeEmbedder(), store)
    embedder = FakeEmbedder()

    await sync_knowledge([CAFES], embedder=embedder, store=store, model_id="another-model", dimension=DIM)

    assert len(embedder.texts) == 1


async def test_example_is_embedded_by_its_question_and_others_by_title_and_content():
    # Users ask questions, so an example matches on its question, not on SQL keywords.
    embedder = FakeEmbedder()

    await sync([WORK, EXAMPLE], embedder, FakeStore())

    assert embedder.texts == ["工作友善\n不限時且有插座", "有幾家店？"]


async def test_failure_on_the_fifth_embedding_leaves_the_store_untouched_and_logs_it(caplog):
    docs = [KnowledgeDoc(id=f"glossary-{i}", kind="glossary", title=f"名詞 {i}", content="定義") for i in range(1, 7)]
    store = FakeStore({"schema-old": EmbeddedDoc(CAFES, "old-hash", [0.0] * DIM)})

    with caplog.at_level(logging.ERROR, logger="app.knowledge_sync"), pytest.raises(ImportFailed, match="glossary-5"):
        await sync(docs, FakeEmbedder(fail_on_call=5), store)

    assert store.applied == []
    assert set(store.docs) == {"schema-old"}
    [record] = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert record.doc_id == "glossary-5"
    assert record.error == "RuntimeError"


async def test_wrong_dimension_stops_before_any_write():
    store = FakeStore()

    with pytest.raises(ImportFailed, match="schema-cafes: .*3 dimensions"):
        await sync([CAFES], FakeEmbedder(dimension=3), store)

    assert store.applied == []


async def test_store_failure_is_reported_as_an_import_failure():
    class BrokenStore(FakeStore):
        async def apply(self, upserts, deletes):
            raise ConnectionError("database went away")

    with pytest.raises(ImportFailed, match="write failed"):
        await sync([CAFES], FakeEmbedder(), BrokenStore())


async def test_empty_document_list_deletes_everything_stored():
    # Only reachable when every file holds []; a missing file already stops the loader.
    store = FakeStore()
    await sync([CAFES], FakeEmbedder(), store)

    report = await sync([], FakeEmbedder(), store)

    assert report == SyncReport(added=0, updated=0, unchanged=0, deleted=1)
    assert store.docs == {}
