"""HTTP API: health check and question endpoint."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, StringConstraints, field_serializer

from app.db import DatabaseUnavailable
from app.pipeline import MAX_QUESTION_CHARS, QueryExecutor, SqlGenerator, ask

log = logging.getLogger(__name__)


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


def _error(status_code: int, message: str) -> JSONResponse:
    # Same shape as a normal answer so the client never special-cases 5xx bodies.
    body = AskResponse(status="error", sql=None, columns=[], rows=[], message=message)
    return JSONResponse(status_code=status_code, content=body.model_dump())


def create_app(*, generator: SqlGenerator, executor: QueryExecutor, cors_origins: list[str]) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        # Release pooled connections so restarts don't leave sessions open on Postgres.
        await executor.close()

    app = FastAPI(title="BrewQL", lifespan=lifespan)
    # Dev only: in deployment nginx serves the UI and /api on one origin, so no CORS is needed.
    app.add_middleware(
        CORSMiddleware, allow_origins=cors_origins, allow_methods=["GET", "POST"], allow_headers=["Content-Type"]
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        # Liveness only: must not depend on the database or Bedrock.
        return {"status": "ok"}

    @app.post("/api/ask", response_model=AskResponse)
    async def ask_question(body: AskRequest):
        try:
            result = await ask(body.question, generator, executor)
        except DatabaseUnavailable:
            log.exception("database unavailable")
            return _error(503, "資料庫暫時無法使用，請稍後再試")
        except Exception:
            # Bedrock/network failures: full detail goes to the log, a generic message to the client.
            log.exception("ask failed")
            return _error(502, "模型服務暫時無法使用，請稍後再試")
        return AskResponse(**asdict(result))

    return app


def build_app() -> FastAPI:
    """Wire real dependencies from settings. Nothing connects until the first question."""
    from anthropic import AnthropicBedrock

    from app.config import Settings
    from app.db import PgExecutor
    from app.llm import BedrockSqlGenerator
    from app.logging_setup import configure_logging

    configure_logging()
    settings = Settings()
    generator = BedrockSqlGenerator(
        AnthropicBedrock(aws_region=settings.aws_region),
        model_id=settings.bedrock_model_id,
        effort=settings.bedrock_effort,
    )
    return create_app(
        generator=generator, executor=PgExecutor(settings.database_url), cors_origins=settings.cors_origins
    )
