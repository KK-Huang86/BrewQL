from types import SimpleNamespace as NS

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
