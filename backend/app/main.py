"""HTTP API: health check and question endpoint."""

from dataclasses import asdict
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import FastAPI
from pydantic import BaseModel, StringConstraints, field_serializer

from app.pipeline import MAX_QUESTION_CHARS, QueryExecutor, SqlGenerator, ask


class AskRequest(BaseModel):
    # Same rule as the pipeline, enforced at the edge so bad input is a 422.
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_QUESTION_CHARS)]


class AskResponse(BaseModel):
    status: Literal["ok", "error"]
    sql: str | None
    columns: list[str]
    rows: list[list[Any]]
    message: str | None

    @field_serializer("rows")
    def _rows(self, rows: list[list[Any]]) -> list[list[Any]]:
        # Postgres NUMERIC arrives as Decimal; charts need JSON numbers, not strings.
        return [[float(v) if isinstance(v, Decimal) else v for v in row] for row in rows]


def create_app(*, generator: SqlGenerator, executor: QueryExecutor, cors_origins: list[str]) -> FastAPI:
    app = FastAPI(title="BrewQL")

    @app.get("/health")
    async def health() -> dict[str, str]:
        # Liveness only: must not depend on the database or Bedrock.
        return {"status": "ok"}

    @app.post("/api/ask")
    async def ask_question(body: AskRequest) -> AskResponse:
        result = await ask(body.question, generator, executor)
        return AskResponse(**asdict(result))

    return app
