"""HTTP API: health check and question endpoint."""

import logging
from dataclasses import asdict
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, StringConstraints, field_serializer

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


def create_app(*, generator: SqlGenerator, executor: QueryExecutor, cors_origins: list[str]) -> FastAPI:
    app = FastAPI(title="BrewQL")
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
        except Exception:
            # Bedrock/network failures: full detail goes to the log, a generic message to the client.
            log.exception("ask failed")
            return JSONResponse(
                status_code=502, content={"status": "error", "message": "模型服務暫時無法使用，請稍後再試"}
            )
        return AskResponse(**asdict(result))

    return app
