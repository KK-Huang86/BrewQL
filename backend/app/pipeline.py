"""Core flow: question -> SQL (model) -> guard -> read-only execution -> result."""

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from app.sql_guard import SqlGuardError, validate_sql


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
    sql = await generator.generate(question)
    try:
        sql = validate_sql(sql)
    except SqlGuardError as e:
        return AskResult(status="error", sql=sql, message=str(e))
    columns, rows = await executor.run(sql)
    return AskResult(status="ok", sql=sql, columns=columns, rows=rows)
