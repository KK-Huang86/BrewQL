"""Core flow: question -> SQL (model) -> guard -> read-only execution -> result, with bounded retries."""

import logging
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from app.db import QueryError
from app.input_guard import GuardrailUsage, GuardVerdict
from app.llm import ErrorKind, FailedAttempt, ModelUsage, Reply, ReplyError
from app.sql_guard import SqlGuardError, validate_sql

log = logging.getLogger(__name__)

MAX_QUESTION_CHARS = 1000


class InvalidQuestion(ValueError):
    """The question is blank or too long; the model is never called."""


class SqlGenerator(Protocol):
    async def generate(self, question: str, feedback: Sequence[FailedAttempt] = ()) -> Reply: ...


class InputGuard(Protocol):
    async def check(self, question: str) -> GuardVerdict: ...


class QueryExecutor(Protocol):
    async def run(self, sql: str) -> tuple[list[str], list[list[Any]]]: ...
    async def close(self) -> None: ...


Stage = Literal["input_guard", "model", "db"]


@dataclass(frozen=True)
class StageTiming:
    stage: Stage
    seconds: float


@dataclass
class AskUsage:
    """What one question cost, over every attempt. Internal: evals and metrics, never the API."""

    model_id: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    guardrail: GuardrailUsage = field(default_factory=GuardrailUsage)
    # Why the input guardrail blocked the question (fixed reason codes); empty when it passed.
    guardrail_reasons: tuple[str, ...] = ()
    elapsed_ms: int = 0
    # One entry per call, in order; retries add their own model and db entries. Left out of
    # equality: timings differ on every run, while usage compares by what was billed.
    stages: list[StageTiming] = field(default_factory=list, compare=False)

    @contextmanager
    def timed(self, stage: Stage) -> Iterator[None]:
        """Time one call, failed ones included: a failed model reply was still waited for (and billed)."""
        started = time.perf_counter()
        try:
            yield
        finally:
            self.stages.append(StageTiming(stage, time.perf_counter() - started))

    def add(self, call: ModelUsage | None) -> None:
        if call is None:
            return
        self.model_id = call.model_id
        self.input_tokens += call.input_tokens
        self.output_tokens += call.output_tokens


AskStatus = Literal["ok", "error", "refused", "clarify"]


@dataclass
class AskResult:
    status: AskStatus
    sql: str | None = None
    columns: list[str] = field(default_factory=list)
    rows: list[list[Any]] = field(default_factory=list)
    message: str | None = None
    # Which step failed, so the UI, evals and retries can treat each differently.
    error_kind: ErrorKind | None = None
    # Who refused, so users can tell an input block from a model decision.
    refusal_source: Literal["input_guardrail", "model"] | None = None
    # Model calls made for this question; 0 when the input guardrail blocked it first.
    attempts: int = 0
    # Tries that failed before this result, for the audit trail; the result itself is the last try.
    failed_attempts: list[FailedAttempt] = field(default_factory=list, compare=False)
    # Cost detail; left out of equality so results compare by answer alone.
    usage: AskUsage = field(default_factory=AskUsage, compare=False)


async def ask(
    question: str,
    generator: SqlGenerator,
    executor: QueryExecutor,
    *,
    input_guard: InputGuard | None = None,
    max_retries: int = 0,
) -> AskResult:
    question = question.strip()
    if not 1 <= len(question) <= MAX_QUESTION_CHARS:
        raise InvalidQuestion(f"問題需為 1~{MAX_QUESTION_CHARS} 字")
    started = time.perf_counter()
    usage = AskUsage()
    result = await _answer(question, generator, executor, input_guard, max_retries, usage)
    usage.elapsed_ms = int((time.perf_counter() - started) * 1000)
    result.usage = usage
    return result


async def _answer(
    question: str,
    generator: SqlGenerator,
    executor: QueryExecutor,
    input_guard: InputGuard | None,
    max_retries: int,
    usage: AskUsage,
) -> AskResult:
    # First gate: a blocked question never reaches the model. Failures propagate (fail closed).
    # Checked once: retries reuse the same question, so screening it again only adds cost.
    if input_guard is not None:
        with usage.timed("input_guard"):
            verdict = await input_guard.check(question)
        usage.guardrail = verdict.usage
        if verdict.blocked:
            usage.guardrail_reasons = verdict.reasons
            return AskResult(status="refused", message=verdict.message, refusal_source="input_guardrail")
    feedback: list[FailedAttempt] = []
    while True:
        result, failure, retryable = await _attempt(question, generator, executor, feedback, usage)
        result.attempts = len(feedback) + 1
        result.failed_attempts = list(feedback)
        if failure is not None:
            _log_failure(result.attempts, failure)
        # Stop on success, refuse/clarify, a failure not worth retrying, or the retry budget.
        if failure is None or not retryable or len(feedback) >= max_retries:
            return result
        feedback.append(failure)


def _log_failure(attempt: int, failure: FailedAttempt) -> None:
    # Never the question: it may hold personal data, which only the audit log may keep.
    log.warning(
        "sql attempt failed attempt=%d kind=%s reason=%s sql=%s",
        attempt,
        failure.error_kind,
        failure.reason,
        failure.sql,
        extra={"attempt": attempt, "error_kind": failure.error_kind, "reason": failure.reason, "sql": failure.sql},
    )


async def _attempt(
    question: str,
    generator: SqlGenerator,
    executor: QueryExecutor,
    feedback: Sequence[FailedAttempt],
    usage: AskUsage,
) -> tuple[AskResult, FailedAttempt | None, bool]:
    """One model call and, for SQL, guard + execution: (result, failure if any, whether a retry may help)."""
    try:
        with usage.timed("model"):
            reply = await generator.generate(question, feedback)
    except ReplyError as e:
        usage.add(e.usage)  # an unusable reply was still billed
        failure = FailedAttempt(error_kind="generation", reason=str(e))
        return AskResult(status="error", message=str(e), error_kind="generation"), failure, True
    usage.add(reply.usage)
    # Refuse and clarify end here: no SQL exists, nothing reaches the database.
    if reply.kind == "refuse":
        return AskResult(status="refused", message=reply.message, refusal_source="model"), None, False
    if reply.kind == "clarify":
        return AskResult(status="clarify", message=reply.message), None, False
    try:
        # Every attempt, retries included, passes the same guard: a fix is never a bypass.
        sql = validate_sql(reply.sql)
    except SqlGuardError as e:
        failure = FailedAttempt(error_kind="guardrail", reason=str(e), sql=reply.sql)
        return AskResult(status="error", sql=reply.sql, message=str(e), error_kind="guardrail"), failure, True
    try:
        with usage.timed("db"):
            columns, rows = await executor.run(sql)
    except QueryError as e:
        result = AskResult(status="error", sql=sql, message="查詢執行失敗，請換個問法再試", error_kind="query")
        # A timed-out rewrite would likely run as long again; not worth another call.
        return result, FailedAttempt(error_kind="query", reason=str(e), sql=sql), not e.timed_out
    return AskResult(status="ok", sql=sql, columns=columns, rows=rows), None, False
