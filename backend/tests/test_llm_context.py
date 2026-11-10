"""The generator takes the prompt context per call; without one it uses the static schema (rag-knowledge-base D8)."""

from datetime import UTC, datetime

from app.llm import BedrockSqlGenerator
from app.schema_context import SCHEMA_CONTEXT
from tests.test_llm_today import FakeClient

NOW = datetime(2026, 11, 10, 3, 0, tzinfo=UTC)


async def system_prompt(**kwargs):
    client = FakeClient()
    await BedrockSqlGenerator(client, model_id="m", now=lambda: NOW).generate("有幾家店？", **kwargs)
    return client.calls[0]["system"]


async def test_given_context_replaces_the_static_schema_and_keeps_today():
    system = await system_prompt(context="規則與檢索到的知識")

    assert system.startswith("規則與檢索到的知識")
    assert SCHEMA_CONTEXT not in system
    assert "2026-11-10" in system


async def test_no_context_means_the_static_schema():
    assert (await system_prompt()).startswith(SCHEMA_CONTEXT)
