import asyncio
import logging
import time
from types import SimpleNamespace as NS

import pytest

from app.llm import REPLY_SCHEMA, BedrockSqlGenerator
from app.schema_context import SCHEMA_CONTEXT


class FakeClient:
    """Stands in for anthropic.AnthropicBedrock: records calls, returns a canned reply."""

    def __init__(self, sql="SELECT 1", stop_reason="end_turn"):
        self.calls = []
        self._reply = NS(
            content=[NS(type="text", text=f'{{"sql": "{sql}"}}')],
            stop_reason=stop_reason,
            usage=NS(input_tokens=321, output_tokens=12),
        )
        self.messages = NS(create=self._create)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return self._reply


async def test_sends_question_with_schema_and_json_schema_and_returns_sql():
    client = FakeClient(sql="SELECT COUNT(*) FROM cafes")
    gen = BedrockSqlGenerator(client, model_id="anthropic.claude-haiku-5-5")

    sql = await gen.generate("台北市有幾家咖啡店？")

    assert sql == "SELECT COUNT(*) FROM cafes"
    [call] = client.calls
    assert call["model"] == "anthropic.claude-haiku-5-5"
    assert call["system"] == SCHEMA_CONTEXT
    assert call["messages"] == [{"role": "user", "content": "台北市有幾家咖啡店？"}]
    assert call["output_config"]["format"] == {"type": "json_schema", "schema": REPLY_SCHEMA}
    assert REPLY_SCHEMA["required"] == ["sql"]


async def test_logs_model_tokens_and_stop_reason(caplog):
    caplog.set_level(logging.INFO, logger="app.llm")
    gen = BedrockSqlGenerator(FakeClient(), model_id="anthropic.claude-haiku-5-5")

    await gen.generate("q")

    [record] = [r for r in caplog.records if r.name == "app.llm"]
    assert record.model_id == "anthropic.claude-haiku-5-5"
    assert record.input_tokens == 321
    assert record.output_tokens == 12
    assert record.stop_reason == "end_turn"


class FailingClient:
    def __init__(self, exc):
        self.messages = NS(create=lambda **_: (_ for _ in ()).throw(exc))


async def test_sdk_errors_are_logged_and_reraised(caplog):
    caplog.set_level(logging.INFO, logger="app.llm")
    boom = RuntimeError("AccessDeniedException: not authorized to invoke model")
    gen = BedrockSqlGenerator(FailingClient(boom), model_id="anthropic.claude-haiku-5-5")

    with pytest.raises(RuntimeError) as raised:
        await gen.generate("q")

    assert raised.value is boom
    [record] = [r for r in caplog.records if r.name == "app.llm"]
    assert record.levelno == logging.ERROR
    assert record.model_id == "anthropic.claude-haiku-5-5"
    assert "AccessDenied" in record.getMessage() or record.exc_info


async def test_slow_model_call_does_not_block_the_event_loop():
    class SlowClient(FakeClient):
        def _create(self, **kwargs):
            time.sleep(0.3)  # the real SDK blocks its thread while waiting on the network
            return super()._create(**kwargs)

    gen = BedrockSqlGenerator(SlowClient(), model_id="m")
    start = time.perf_counter()

    async def heartbeat():
        await asyncio.sleep(0.01)
        return time.perf_counter() - start

    _, heartbeat_after = await asyncio.gather(gen.generate("q"), heartbeat())

    assert heartbeat_after < 0.1


async def test_effort_is_sent_only_when_configured():
    # Older models such as Haiku 4.5 reject the effort parameter with a 400.
    with_effort, without_effort = FakeClient(), FakeClient()

    await BedrockSqlGenerator(with_effort, model_id="m", effort="low").generate("q")
    await BedrockSqlGenerator(without_effort, model_id="m", effort=None).generate("q")

    assert with_effort.calls[0]["output_config"]["effort"] == "low"
    assert "effort" not in without_effort.calls[0]["output_config"]
    assert without_effort.calls[0]["output_config"]["format"]["type"] == "json_schema"


def test_bedrock_client_gives_up_before_nginx_cuts_the_request():
    from app.llm import build_bedrock_client

    client = build_bedrock_client(aws_region="us-east-1")

    assert client.max_retries == 2
    # Every attempt plus retries must finish inside nginx's 60s proxy timeout.
    assert client.timeout * (client.max_retries + 1) < 60
