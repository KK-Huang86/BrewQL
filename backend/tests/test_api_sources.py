"""The API reports which knowledge a rag answer used; static answers report none."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.main import create_app
from tests.test_pipeline_rag import Executor, FakeRetriever, RecordingGenerator


def post(**kwargs):
    app = create_app(generator=RecordingGenerator(), executor=Executor(), cors_origins=[], **kwargs)
    return TestClient(app).post("/api/ask", json={"question": "工作友善的店有幾家？"})


def test_rag_answer_lists_its_sources():
    response = post(retriever=FakeRetriever())

    assert response.status_code == 200
    assert response.json()["sources"] == [
        {"id": "schema-cafes", "kind": "schema", "title": "資料表 cafes"},
        {"id": "glossary-work-friendly", "kind": "glossary", "title": "工作友善"},
    ]


def test_static_answer_has_empty_sources():
    assert post().json()["sources"] == []


def test_prompt_mode_defaults_to_rag_and_rejects_unknown_values(monkeypatch):
    # rag became the default after the evaluation (RESULTS.md 2026-11-10: 52/52 like static, ~25% cheaper).
    monkeypatch.delenv("PROMPT_MODE", raising=False)
    assert Settings(_env_file=None).prompt_mode == "rag"

    with pytest.raises(ValidationError):
        Settings(_env_file=None, prompt_mode="vector")
