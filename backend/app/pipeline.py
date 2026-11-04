"""Core flow: question -> SQL (model) -> guard -> read-only execution -> result."""

import logging
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from app.db import QueryError
from app.llm import ReplyError
from app.sql_guard import SqlGuardError, validate_sql

log = logging.getLogger(__name__)

MAX_QUESTION_CHARS = 1000


class InvalidQuestion(ValueError):
    """The question is blank or too long; the model is never called."""


class SqlGenerator(Protocol):
    async def generate(self, question: str) -> str: ...


class QueryExecutor(Protocol):
    async def run(self, sql: str) -> tuple[list[str], list[list[Any]]]: ...


@dataclass
class AskResult:
    status: Literal["ok", "error"]
    sql: str | None = None
    columns: list[str] = field(default_factory=list)
    rows: list[list[Any]] = field(default_factory=list)
    message: str | None = None


async def ask(question: str, generator: SqlGenerator, executor: QueryExecutor) -> AskResult:
    question = question.strip()
    if not 1 <= len(question) <= MAX_QUESTION_CHARS:
        raise InvalidQuestion(f"問題需為 1~{MAX_QUESTION_CHARS} 字")
    try:
        sql = await generator.generate(question)
    except ReplyError as e:
        return AskResult(status="error", message=str(e))
    try:
        sql = validate_sql(sql)
    except SqlGuardError as e:
        return AskResult(status="error", sql=sql, message=str(e))
    try:
        columns, rows = await executor.run(sql)
    except QueryError as e:
        log.warning("query failed sql=%s detail=%s", sql, e)
        return AskResult(status="error", sql=sql, message="查詢執行失敗，請換個問法再試")
    return AskResult(status="ok", sql=sql, columns=columns, rows=rows)
