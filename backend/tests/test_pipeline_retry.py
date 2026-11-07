"""Self-correction: failed attempts go back to the model, bounded by max_retries."""

import pytest

from app.db import QueryError
from app.input_guard import GuardVerdict
from app.llm import FailedAttempt, Reply, ReplyError
from app.pipeline import ask

BAD = Reply(kind="sql", sql="DELETE FROM cafes")
GOOD = Reply(kind="sql", sql="SELECT name FROM cafes")


class ScriptedGenerator:
    """Plays back one outcome per call (a Reply, or an exception to raise) and records the feedback."""

    def __init__(self, *outcomes):
        self.outcomes, self.feedbacks = list(outcomes), []

    async def generate(self, question, feedback=()):
        self.feedbacks.append(tuple(feedback))
        outcome = self.outcomes[min(len(self.feedbacks), len(self.outcomes)) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    @property
    def calls(self):
        return len(self.feedbacks)


class ScriptedExecutor:
    """Raises the queued errors first, then succeeds."""

    def __init__(self, *errors):
        self.errors, self.calls = list(errors), []

    async def run(self, sql):
        self.calls.append(sql)
        if self.errors:
            raise self.errors.pop(0)
        return ["name"], [["咖啡店"]]


async def test_guard_rejection_is_fed_back_and_the_fix_runs_once():
    gen, ex = ScriptedGenerator(BAD, GOOD), ScriptedExecutor()

    result = await ask("q", gen, ex, max_retries=2)

    assert result.status == "ok"
    assert result.attempts == 2
    [failure] = gen.feedbacks[1]
    assert failure.error_kind == "guardrail"
    assert failure.sql == "DELETE FROM cafes"
    assert "SELECT" in failure.reason
    # The rejected SQL never ran; only the fix did.
    assert ex.calls == ["SELECT name FROM cafes LIMIT 1000"]


async def test_database_error_text_reaches_the_model_but_not_the_user():
    raw = 'UndefinedColumnError: column "nmae" does not exist'
    gen, ex = ScriptedGenerator(GOOD), ScriptedExecutor(QueryError(raw))

    result = await ask("q", gen, ex, max_retries=2)

    assert result.status == "ok"
    assert result.attempts == 2
    assert gen.feedbacks[1] == (FailedAttempt(error_kind="query", reason=raw, sql="SELECT name FROM cafes LIMIT 1000"),)


async def test_unusable_reply_is_fed_back_without_sql():
    gen = ScriptedGenerator(ReplyError("模型回覆的 SQL 是空的"), GOOD)

    result = await ask("q", gen, ScriptedExecutor(), max_retries=2)

    assert result.status == "ok"
    assert result.attempts == 2
    assert gen.feedbacks[1] == (FailedAttempt(error_kind="generation", reason="模型回覆的 SQL 是空的"),)


async def test_retries_stop_at_the_limit_and_report_the_last_failure():
    gen, ex = ScriptedGenerator(BAD), ScriptedExecutor()

    result = await ask("q", gen, ex, max_retries=2)

    # 1 try + 2 retries, never more: each call costs tokens.
    assert gen.calls == 3
    assert result.status == "error"
    assert result.attempts == 3
    assert result.error_kind == "guardrail"
    assert result.sql == "DELETE FROM cafes"
    assert ex.calls == []
    # Every retry sees all earlier failures, oldest first.
    assert [len(f) for f in gen.feedbacks] == [0, 1, 2]


async def test_zero_retries_means_a_single_attempt():
    gen = ScriptedGenerator(BAD, GOOD)

    result = await ask("q", gen, ScriptedExecutor(), max_retries=0)

    assert gen.calls == 1
    assert result.status == "error"
    assert result.attempts == 1


async def test_default_is_no_retry():
    gen = ScriptedGenerator(BAD, GOOD)

    await ask("q", gen, ScriptedExecutor())

    assert gen.calls == 1


async def test_timeout_is_not_retried():
    gen = ScriptedGenerator(GOOD)
    ex = ScriptedExecutor(QueryError("QueryCanceledError: canceling statement", timed_out=True))

    result = await ask("q", gen, ex, max_retries=2)

    assert gen.calls == 1
    assert len(ex.calls) == 1
    assert result.status == "error"
    assert result.error_kind == "query"
    assert result.attempts == 1


async def test_model_service_error_is_not_retried():
    boom = RuntimeError("ThrottlingException")
    gen = ScriptedGenerator(boom, GOOD)

    with pytest.raises(RuntimeError):
        await ask("q", gen, ScriptedExecutor(), max_retries=2)

    assert gen.calls == 1


async def test_service_error_during_a_retry_propagates():
    boom = RuntimeError("ThrottlingException")
    gen = ScriptedGenerator(BAD, boom, GOOD)

    with pytest.raises(RuntimeError):
        await ask("q", gen, ScriptedExecutor(), max_retries=2)

    assert gen.calls == 2


@pytest.mark.parametrize(
    ("reply", "status"),
    [
        (Reply(kind="refuse", message="不能修改資料"), "refused"),
        (Reply(kind="clarify", message="指哪一區？"), "clarify"),
    ],
)
async def test_refuse_or_clarify_is_final_and_not_retried(reply, status):
    gen = ScriptedGenerator(reply, GOOD)

    result = await ask("q", gen, ScriptedExecutor(), max_retries=2)

    assert gen.calls == 1
    assert result.status == status
    assert result.attempts == 1


async def test_refusal_during_a_retry_is_returned_as_is():
    gen = ScriptedGenerator(BAD, Reply(kind="refuse", message="不能修改資料"))

    result = await ask("q", gen, ScriptedExecutor(), max_retries=2)

    assert gen.calls == 2
    assert result.status == "refused"
    assert result.refusal_source == "model"
    assert result.attempts == 2


class CountingGuard:
    def __init__(self, blocked=False):
        self.blocked, self.calls = blocked, 0

    async def check(self, question):
        self.calls += 1
        return GuardVerdict(blocked=self.blocked, message="這個問題無法處理" if self.blocked else None)


async def test_input_guardrail_runs_once_even_when_retrying():
    guard = CountingGuard()

    await ask("q", ScriptedGenerator(BAD), ScriptedExecutor(), input_guard=guard, max_retries=2)

    assert guard.calls == 1


async def test_input_guardrail_block_means_zero_attempts():
    gen = ScriptedGenerator(GOOD)

    result = await ask("q", gen, ScriptedExecutor(), input_guard=CountingGuard(blocked=True), max_retries=2)

    assert gen.calls == 0
    assert result.attempts == 0


def attempt_logs(caplog):
    return [r for r in caplog.records if r.name == "app.pipeline" and r.getMessage().startswith("sql attempt failed")]


async def test_each_failed_attempt_is_logged_with_number_kind_reason_and_sql(caplog):
    caplog.set_level("INFO", logger="app.pipeline")

    await ask("台北有幾家店（私人問題）", ScriptedGenerator(BAD, GOOD), ScriptedExecutor(), max_retries=1)

    [record] = attempt_logs(caplog)
    assert record.levelname == "WARNING"
    assert record.attempt == 1
    assert record.error_kind == "guardrail"
    assert record.sql == "DELETE FROM cafes"
    assert "SELECT" in record.reason
    # The question may hold personal data; only the audit log may keep it.
    assert "私人問題" not in record.getMessage()
    assert "私人問題" not in str(vars(record))


async def test_every_attempt_is_logged_when_retries_run_out(caplog):
    caplog.set_level("INFO", logger="app.pipeline")

    await ask("q", ScriptedGenerator(BAD), ScriptedExecutor(), max_retries=1)

    assert [r.attempt for r in attempt_logs(caplog)] == [1, 2]


async def test_a_timeout_is_logged_even_though_it_is_not_retried(caplog):
    caplog.set_level("INFO", logger="app.pipeline")
    ex = ScriptedExecutor(QueryError("QueryCanceledError: canceling statement", timed_out=True))

    await ask("q", ScriptedGenerator(GOOD), ex, max_retries=1)

    [record] = attempt_logs(caplog)
    assert record.error_kind == "query"
    assert "QueryCanceled" in record.reason


async def test_success_logs_no_failed_attempt(caplog):
    caplog.set_level("INFO", logger="app.pipeline")

    await ask("q", ScriptedGenerator(GOOD), ScriptedExecutor(), max_retries=1)

    assert attempt_logs(caplog) == []
