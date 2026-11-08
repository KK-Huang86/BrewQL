"""The pipeline totals what one question cost: tokens over every attempt, guardrail units, time."""

import asyncio

from fastapi.testclient import TestClient

from app.input_guard import GuardrailUsage, GuardVerdict
from app.llm import ModelUsage, Reply, ReplyError
from app.main import create_app
from app.pipeline import AskUsage, ask


def billed(input_tokens, output_tokens):
    return ModelUsage(model_id="m-1", input_tokens=input_tokens, output_tokens=output_tokens)


class ScriptedGenerator:
    def __init__(self, *outcomes, delay=0.0):
        self.outcomes, self.delay, self.calls = list(outcomes), delay, 0

    async def generate(self, question, feedback=()):
        self.calls += 1
        await asyncio.sleep(self.delay)
        outcome = self.outcomes[self.calls - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class Executor:
    async def run(self, sql):
        return ["n"], [[1]]


class Guard:
    def __init__(self, blocked=False, units=(1, 1)):
        self.blocked, self.units = blocked, units

    async def check(self, question):
        usage = GuardrailUsage(topic_units=self.units[0], content_units=self.units[1])
        return GuardVerdict(blocked=self.blocked, message="擋下" if self.blocked else None, usage=usage)


GOOD = Reply(kind="sql", sql="SELECT 1", usage=billed(4321, 40))


async def test_single_attempt_reports_its_tokens_and_model():
    result = await ask("q", ScriptedGenerator(GOOD), Executor())

    assert (result.usage.model_id, result.usage.input_tokens, result.usage.output_tokens) == ("m-1", 4321, 40)


async def test_tokens_add_up_over_every_attempt_including_unusable_replies():
    bad = ReplyError("模型回覆格式不符", usage=billed(900, 30))

    result = await ask("q", ScriptedGenerator(bad, GOOD), Executor(), max_retries=1)

    assert result.attempts == 2
    assert (result.usage.input_tokens, result.usage.output_tokens) == (5221, 70)


async def test_guardrail_units_are_counted_when_the_question_passes():
    result = await ask("q", ScriptedGenerator(GOOD), Executor(), input_guard=Guard(units=(1, 1)))

    assert result.usage.guardrail == GuardrailUsage(topic_units=1, content_units=1)


async def test_blocked_question_costs_guardrail_units_and_no_tokens():
    gen = ScriptedGenerator(GOOD)

    result = await ask("q", gen, Executor(), input_guard=Guard(blocked=True, units=(2, 2)))

    assert gen.calls == 0
    assert result.usage == AskUsage(
        model_id=None,
        input_tokens=0,
        output_tokens=0,
        guardrail=GuardrailUsage(2, 2),
        elapsed_ms=result.usage.elapsed_ms,
    )


async def test_reply_without_usage_counts_zero_tokens():
    result = await ask("q", ScriptedGenerator(Reply(kind="sql", sql="SELECT 1")), Executor())

    assert (result.usage.input_tokens, result.usage.output_tokens) == (0, 0)


async def test_elapsed_time_covers_the_whole_question():
    result = await ask("q", ScriptedGenerator(GOOD, delay=0.05), Executor())

    assert result.usage.elapsed_ms >= 50


def test_usage_never_reaches_the_api_response():
    # Token counts and model ids are internal cost detail, not something visitors should see.
    app = create_app(generator=ScriptedGenerator(GOOD), executor=Executor(), cors_origins=[])

    body = TestClient(app).post("/api/ask", json={"question": "q"}).json()

    assert body["status"] == "ok"
    assert "usage" not in body
    assert "m-1" not in str(body)
    assert "4321" not in str(body)  # distinct from the guard's LIMIT 1000
