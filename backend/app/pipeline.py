"""Core flow: question -> SQL (model) -> guard -> read-only execution -> result."""

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


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
    columns, rows = await executor.run(sql)
    return AskResult(status="ok", sql=sql, columns=columns, rows=rows)
