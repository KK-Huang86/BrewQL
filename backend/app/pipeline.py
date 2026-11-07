"""Core flow: question -> SQL (model) -> guard -> read-only execution -> result, with bounded retries."""

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from app.db import QueryError
from app.input_guard import GuardVerdict
from app.llm import ErrorKind, FailedAttempt, Reply, ReplyError
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


@dataclass
class AskResult:
    status: Literal["ok", "error", "refused", "clarify"]
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
    # First gate: a blocked question never reaches the model. Failures propagate (fail closed).
    # Checked once: retries reuse the same question, so screening it again only adds cost.
    if input_guard is not None:
        verdict = await input_guard.check(question)
        if verdict.blocked:
            return AskResult(status="refused", message=verdict.message, refusal_source="input_guardrail")
    feedback: list[FailedAttempt] = []
    while True:
        result, failure = await _attempt(question, generator, executor, feedback)
        result.attempts = len(feedback) + 1
        # Stop on success, refuse/clarify, a failure not worth retrying, or the retry budget.
        if failure is None or len(feedback) >= max_retries:
            return result
        feedback.append(failure)


async def _attempt(
    question: str, generator: SqlGenerator, executor: QueryExecutor, feedback: Sequence[FailedAttempt]
) -> tuple[AskResult, FailedAttempt | None]:
    """One model call and, for SQL, guard + execution. The failure is set only when a retry may help."""
    try:
        reply = await generator.generate(question, feedback)
    except ReplyError as e:
        failure = FailedAttempt(error_kind="generation", reason=str(e))
        return AskResult(status="error", message=str(e), error_kind="generation"), failure
    # Refuse and clarify end here: no SQL exists, nothing reaches the database.
    if reply.kind == "refuse":
        return AskResult(status="refused", message=reply.message, refusal_source="model"), None
    if reply.kind == "clarify":
        return AskResult(status="clarify", message=reply.message), None
    try:
        # Every attempt, retries included, passes the same guard: a fix is never a bypass.
        sql = validate_sql(reply.sql)
    except SqlGuardError as e:
        failure = FailedAttempt(error_kind="guardrail", reason=str(e), sql=reply.sql)
        return AskResult(status="error", sql=reply.sql, message=str(e), error_kind="guardrail"), failure
    try:
        columns, rows = await executor.run(sql)
    except QueryError as e:
        log.warning("query failed sql=%s detail=%s", sql, e)
        result = AskResult(status="error", sql=sql, message="查詢執行失敗，請換個問法再試", error_kind="query")
        # A timed-out rewrite would likely run as long again; not worth another call.
        failure = None if e.timed_out else FailedAttempt(error_kind="query", reason=str(e), sql=sql)
        return result, failure
    return AskResult(status="ok", sql=sql, columns=columns, rows=rows), None
