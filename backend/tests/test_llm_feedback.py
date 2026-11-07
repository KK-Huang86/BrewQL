"""Self-correction: the generator replays earlier failed attempts as conversation turns."""

import json
from types import SimpleNamespace as NS

from app.llm import BedrockSqlGenerator, FailedAttempt, Reply


class FakeClient:
    """Stands in for anthropic.AnthropicBedrock: records calls, always replies with valid SQL."""

    def __init__(self):
        self.calls = []
        body = json.dumps({"kind": "sql", "sql": "SELECT 2", "message": ""})
        self._reply = NS(
            content=[NS(type="text", text=body)],
            stop_reason="end_turn",
            usage=NS(input_tokens=1, output_tokens=1),
        )
        self.messages = NS(create=self._create)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return self._reply


async def sent_messages(*feedback):
    client = FakeClient()
    reply = await BedrockSqlGenerator(client, model_id="m").generate("台北有幾家店？", feedback=feedback)
    assert reply == Reply(kind="sql", sql="SELECT 2")
    [call] = client.calls
    return call["messages"]


async def test_no_feedback_sends_only_the_question():
    assert await sent_messages() == [{"role": "user", "content": "台北有幾家店？"}]


async def test_rejected_sql_is_replayed_as_the_model_turn_followed_by_the_reason():
    messages = await sent_messages(
        FailedAttempt(error_kind="guardrail", reason="不允許的資料表：pg_shadow", sql="SELECT * FROM pg_shadow")
    )

    assert [m["role"] for m in messages] == ["user", "assistant", "user"]
    assert messages[0]["content"] == "台北有幾家店？"
    # The model sees its own earlier answer in the same JSON shape it produced.
    assert json.loads(messages[1]["content"]) == {"kind": "sql", "sql": "SELECT * FROM pg_shadow", "message": ""}
    assert "SQL 防護" in messages[2]["content"]
    assert "不允許的資料表：pg_shadow" in messages[2]["content"]


async def test_database_error_is_labelled_as_an_execution_failure():
    messages = await sent_messages(
        FailedAttempt(
            error_kind="query", reason='UndefinedColumnError: column "nmae" does not exist', sql="SELECT nmae"
        )
    )

    assert "資料庫執行錯誤" in messages[-1]["content"]
    assert 'column "nmae" does not exist' in messages[-1]["content"]


async def test_attempt_without_sql_is_folded_into_the_user_turn():
    # No SQL means no model turn to replay; roles must still alternate.
    messages = await sent_messages(FailedAttempt(error_kind="generation", reason="模型回覆的 SQL 是空的"))

    assert [m["role"] for m in messages] == ["user"]
    assert messages[0]["content"].startswith("台北有幾家店？")
    assert "格式" in messages[0]["content"]
    assert "模型回覆的 SQL 是空的" in messages[0]["content"]


async def test_several_failures_are_replayed_in_order_and_end_on_a_user_turn():
    messages = await sent_messages(
        FailedAttempt(error_kind="guardrail", reason="只允許 SELECT 查詢", sql="DELETE FROM cafes"),
        FailedAttempt(error_kind="generation", reason="模型回覆格式不符"),
        FailedAttempt(error_kind="query", reason="SyntaxError", sql="SELEC 1"),
    )

    roles = [m["role"] for m in messages]
    assert roles == ["user", "assistant", "user", "assistant", "user"]
    assert "只允許 SELECT 查詢" in messages[2]["content"]
    assert "模型回覆格式不符" in messages[2]["content"]  # folded into the turn after the first failure
    assert json.loads(messages[3]["content"])["sql"] == "SELEC 1"
    assert "SyntaxError" in messages[4]["content"]
