"""HTTP API: health check and question endpoint."""

from dataclasses import asdict
from typing import Any, Literal

from fastapi import FastAPI
from pydantic import BaseModel

from app.pipeline import QueryExecutor, SqlGenerator, ask


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    status: Literal["ok", "error"]
    sql: str | None
    columns: list[str]
    rows: list[list[Any]]
    message: str | None


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
