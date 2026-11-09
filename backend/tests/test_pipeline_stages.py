"""Per-stage timings on AskUsage (observe-with-grafana D4): the pipeline measures, the API records metrics."""

import asyncio

from app.db import QueryError
from app.input_guard import GuardVerdict
from app.llm import Reply, ReplyError
from app.pipeline import ask

DELAY = 0.02


class SlowGuard:
    def __init__(self, blocked=False):
        self.blocked = blocked

    async def check(self, question):
        await asyncio.sleep(DELAY)
        return GuardVerdict(blocked=self.blocked, message="擋下" if self.blocked else None)


class ScriptedGenerator:
    """Returns (or raises) each scripted reply in turn, after a short delay."""

    def __init__(self, *replies):
        self.replies = list(replies)

    async def generate(self, question, feedback=()):
        await asyncio.sleep(DELAY)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


class ScriptedExecutor:
    def __init__(self, *outcomes):
        self.outcomes = list(outcomes) or [None]

    async def run(self, sql):
        await asyncio.sleep(DELAY)
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if isinstance(outcome, Exception):
            raise outcome
        return ["n"], [[1]]


SQL = Reply(kind="sql", sql="SELECT 1")


def stages(result):
    return [s.stage for s in result.usage.stages]


async def test_an_answer_times_guard_model_and_database_in_order():
    result = await ask("q", ScriptedGenerator(SQL), ScriptedExecutor(), input_guard=SlowGuard())

    assert result.status == "ok"
    assert stages(result) == ["input_guard", "model", "db"]
    assert all(s.seconds >= DELAY for s in result.usage.stages)


async def test_a_guardrail_block_has_only_the_guard_stage():
    result = await ask("q", ScriptedGenerator(), ScriptedExecutor(), input_guard=SlowGuard(blocked=True))

    assert result.status == "refused"
    assert stages(result) == ["input_guard"]


async def test_without_a_guard_there_is_no_guard_stage():
    result = await ask("q", ScriptedGenerator(SQL), ScriptedExecutor())

    assert stages(result) == ["model", "db"]


async def test_refuse_and_unsafe_sql_never_time_the_database():
    refused = await ask("q", ScriptedGenerator(Reply(kind="refuse", message="不回答")), ScriptedExecutor())
    unsafe = await ask("q", ScriptedGenerator(Reply(kind="sql", sql="DELETE FROM cafes")), ScriptedExecutor())

    assert stages(refused) == ["model"]
    assert (unsafe.error_kind, stages(unsafe)) == ("guardrail", ["model"])


async def test_each_retry_adds_its_own_model_and_database_timings():
    executor = ScriptedExecutor(QueryError("column does not exist"), None)

    result = await ask("q", ScriptedGenerator(SQL, SQL), executor, input_guard=SlowGuard(), max_retries=1)

    assert (result.status, result.attempts) == ("ok", 2)
    assert stages(result) == ["input_guard", "model", "db", "model", "db"]


async def test_a_failed_model_reply_is_still_timed():
    result = await ask("q", ScriptedGenerator(ReplyError("not JSON")), ScriptedExecutor())

    assert (result.error_kind, stages(result)) == ("generation", ["model"])
    assert result.usage.stages[0].seconds >= DELAY
