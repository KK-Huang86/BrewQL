"""Core flow: question -> SQL (model) -> guard -> read-only execution -> result."""

import logging
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from app.db import QueryError
from app.input_guard import GuardVerdict
from app.llm import Reply, ReplyError
from app.sql_guard import SqlGuardError, validate_sql

log = logging.getLogger(__name__)

MAX_QUESTION_CHARS = 1000


class InvalidQuestion(ValueError):
    """The question is blank or too long; the model is never called."""


class SqlGenerator(Protocol):
    async def generate(self, question: str) -> Reply: ...


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
    error_kind: Literal["generation", "guardrail", "query"] | None = None
    # Who refused, so users can tell an input block from a model decision.
    refusal_source: Literal["input_guardrail", "model"] | None = None


async def ask(
    question: str, generator: SqlGenerator, executor: QueryExecutor, *, input_guard: InputGuard | None = None
) -> AskResult:
    question = question.strip()
    if not 1 <= len(question) <= MAX_QUESTION_CHARS:
        raise InvalidQuestion(f"問題需為 1~{MAX_QUESTION_CHARS} 字")
    # First gate: a blocked question never reaches the model. Failures propagate (fail closed).
    if input_guard is not None:
        verdict = await input_guard.check(question)
        if verdict.blocked:
            return AskResult(status="refused", message=verdict.message, refusal_source="input_guardrail")
    try:
        reply = await generator.generate(question)
    except ReplyError as e:
        return AskResult(status="error", message=str(e), error_kind="generation")
    # Refuse and clarify end here: no SQL exists, nothing reaches the database.
    if reply.kind == "refuse":
        return AskResult(status="refused", message=reply.message, refusal_source="model")
    if reply.kind == "clarify":
        return AskResult(status="clarify", message=reply.message)
    try:
        sql = validate_sql(reply.sql)
    except SqlGuardError as e:
        return AskResult(status="error", sql=reply.sql, message=str(e), error_kind="guardrail")
    try:
        columns, rows = await executor.run(sql)
    except QueryError as e:
        log.warning("query failed sql=%s detail=%s", sql, e)
        return AskResult(status="error", sql=sql, message="查詢執行失敗，請換個問法再試", error_kind="query")
    return AskResult(status="ok", sql=sql, columns=columns, rows=rows)
