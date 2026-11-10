"""The knowledge import command: exit codes say what went wrong, the report says what changed."""

from scripts.import_knowledge import main
from tests.test_knowledge_sync import FakeEmbedder, FakeStore

YAML = {
    "schema.yaml": "- id: schema-cafes\n  title: 資料表 cafes\n  content: 咖啡店\n",
    "glossary.yaml": "- id: glossary-work\n  title: 工作友善\n  content: 不限時\n",
    "examples.yaml": "[]\n",
}


def knowledge_dir(tmp_path, **override):
    for name, text in {**YAML, **override}.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    return tmp_path


async def test_prints_what_changed_and_succeeds(tmp_path, capsys):
    store = FakeStore()

    code = await main(knowledge_dir(tmp_path), embedder=FakeEmbedder(), store=store, model_id="m", dimension=1024)

    assert code == 0
    assert set(store.docs) == {"schema-cafes", "glossary-work"}
    assert "added=2 updated=0 unchanged=0 deleted=0" in capsys.readouterr().out


async def test_invalid_documents_exit_2_before_any_embedding(tmp_path, capsys):
    embedder = FakeEmbedder()
    bad = knowledge_dir(tmp_path, **{"examples.yaml": "- id: e\n  question: q\n  sql: DELETE FROM cafes\n"})

    code = await main(bad, embedder=embedder, store=FakeStore(), model_id="m", dimension=1024)

    assert code == 2
    assert embedder.texts == []
    assert "e: example SQL rejected" in capsys.readouterr().err


async def test_failed_import_exits_1_and_says_nothing_was_written(tmp_path, capsys):
    store = FakeStore()

    code = await main(
        knowledge_dir(tmp_path), embedder=FakeEmbedder(fail_on_call=1), store=store, model_id="m", dimension=1024
    )

    assert code == 1
    assert store.docs == {}
    assert "knowledge base unchanged" in capsys.readouterr().err
