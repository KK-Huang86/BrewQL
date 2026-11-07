"""The model must know today's date, or it treats past years as the future (eval q09)."""

import json
from datetime import UTC, datetime
from types import SimpleNamespace as NS

from app.llm import BedrockSqlGenerator
from app.schema_context import SCHEMA_CONTEXT


class FakeClient:
    def __init__(self):
        self.calls = []
        body = json.dumps({"kind": "sql", "sql": "SELECT 1", "message": ""})
        reply = NS(
            content=[NS(type="text", text=body)], stop_reason="end_turn", usage=NS(input_tokens=1, output_tokens=1)
        )
        self.messages = NS(create=lambda **kw: (self.calls.append(kw), reply)[1])


async def system_prompt_at(now):
    client = FakeClient()
    await BedrockSqlGenerator(client, model_id="m", now=lambda: now).generate("2025 年每月新上架幾家")
    return client.calls[0]["system"]


async def test_system_prompt_keeps_the_schema_and_adds_today():
    system = await system_prompt_at(datetime(2026, 11, 8, 3, 0, tzinfo=UTC))

    assert system.startswith(SCHEMA_CONTEXT)
    assert "2026-11-08" in system
    # Earlier periods are history to query, not a forecast to refuse.
    assert "歷史資料" in system


async def test_today_is_the_taipei_date():
    # 17:00 UTC on the 7th is already 01:00 on the 8th in Taipei.
    system = await system_prompt_at(datetime(2026, 11, 7, 17, 0, tzinfo=UTC))

    assert "2026-11-08" in system
    assert "2026-11-07" not in system


async def test_the_date_follows_the_clock_on_every_call():
    times = iter([datetime(2026, 11, 8, 3, 0, tzinfo=UTC), datetime(2026, 11, 9, 3, 0, tzinfo=UTC)])
    client = FakeClient()
    gen = BedrockSqlGenerator(client, model_id="m", now=lambda: next(times))

    await gen.generate("q")
    await gen.generate("q")

    assert "2026-11-08" in client.calls[0]["system"]
    assert "2026-11-09" in client.calls[1]["system"]
