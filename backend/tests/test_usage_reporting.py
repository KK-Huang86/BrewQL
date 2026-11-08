"""Usage the eval and cost tracking need: model tokens per call and guardrail units per check."""

import json
import logging
from types import SimpleNamespace as NS

import pytest

from app.input_guard import BedrockInputGuard, GuardrailUsage
from app.llm import BedrockSqlGenerator, ModelUsage, ReplyError


class FakeAnthropic:
    def __init__(self, text, stop_reason="end_turn"):
        self._reply = NS(
            content=[NS(type="text", text=text)], stop_reason=stop_reason, usage=NS(input_tokens=321, output_tokens=12)
        )
        self.messages = NS(create=lambda **_: self._reply)


def sql_json(sql="SELECT 1"):
    return json.dumps({"kind": "sql", "sql": sql, "message": ""})


async def test_reply_carries_the_model_and_tokens_of_its_call():
    reply = await BedrockSqlGenerator(FakeAnthropic(sql_json()), model_id="m-1").generate("q")

    assert reply.usage == ModelUsage(model_id="m-1", input_tokens=321, output_tokens=12)


@pytest.mark.parametrize(
    ("text", "stop_reason"),
    [("not json", "end_turn"), (sql_json("SELECT 1 FR"), "max_tokens"), (sql_json(" "), "end_turn")],
)
async def test_unusable_reply_still_reports_the_tokens_it_was_billed(text, stop_reason):
    # A bad reply is still a paid call; the retry and the eval must count it.
    with pytest.raises(ReplyError) as raised:
        await BedrockSqlGenerator(FakeAnthropic(text, stop_reason), model_id="m-1").generate("q")

    assert raised.value.usage == ModelUsage(model_id="m-1", input_tokens=321, output_tokens=12)


async def test_safety_refusal_carries_usage_too():
    reply = await BedrockSqlGenerator(FakeAnthropic("", "refusal"), model_id="m-1").generate("q")

    assert reply.kind == "refuse"
    assert reply.usage.input_tokens == 321


def test_usage_does_not_change_reply_equality():
    from app.llm import Reply

    assert Reply(kind="sql", sql="SELECT 1", usage=ModelUsage("m", 1, 1)) == Reply(kind="sql", sql="SELECT 1")


class FakeBedrockRuntime:
    def __init__(self, response):
        self.response = response

    def apply_guardrail(self, **_):
        return self.response


def usage(topic, content):
    return {"topicPolicyUnits": topic, "contentPolicyUnits": content, "wordPolicyUnits": 0}


def check(response):
    return BedrockInputGuard(FakeBedrockRuntime(response), guardrail_id="gr", guardrail_version="1").check("q")


async def test_passed_check_reports_topic_and_content_units():
    verdict = await check({"action": "NONE", "outputs": [], "assessments": [{}], "usage": usage(1, 1)})

    assert verdict.usage == GuardrailUsage(topic_units=1, content_units=1)


async def test_blocked_check_is_billed_the_same_way():
    response = {
        "action": "GUARDRAIL_INTERVENED",
        "outputs": [{"text": "這個問題無法處理"}],
        "assessments": [{"topicPolicy": {"topics": [{"name": "off-topic", "action": "BLOCKED"}]}}],
        "usage": usage(2, 2),
    }

    verdict = await check(response)

    assert verdict.blocked
    assert verdict.usage == GuardrailUsage(topic_units=2, content_units=2)


async def test_missing_usage_counts_zero_and_warns(caplog):
    caplog.set_level(logging.INFO, logger="app.input_guard")

    verdict = await check({"action": "NONE", "outputs": [], "assessments": [{}]})

    # Not reported, so the eval must treat this question's cost as unknown, not as zero units.
    assert verdict.usage == GuardrailUsage(topic_units=0, content_units=0, reported=False)
    assert any(r.levelno == logging.WARNING and "usage" in r.getMessage() for r in caplog.records)


def test_usage_does_not_change_verdict_equality():
    from app.input_guard import GuardVerdict

    assert GuardVerdict(blocked=False, usage=GuardrailUsage(1, 1)) == GuardVerdict(blocked=False)
