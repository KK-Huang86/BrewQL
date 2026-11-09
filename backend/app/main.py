"""HTTP API: health check and question endpoint."""

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST
from pydantic import BaseModel, StringConstraints, field_serializer

from app.charts import Chart, choose_chart
from app.daily_limit import DailyQuestionLimit
from app.db import DatabaseUnavailable
from app.input_guard import InputGuardUnavailable
from app.llm import ErrorKind
from app.metrics import AskMetrics
from app.pipeline import MAX_QUESTION_CHARS, InputGuard, QueryExecutor, SqlGenerator, ask

log = logging.getLogger(__name__)


class AskRequest(BaseModel):
    # Same rule as the pipeline, enforced at the edge so bad input is a 422.
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_QUESTION_CHARS)]


class AskResponse(BaseModel):
    status: Literal["ok", "error", "refused", "clarify"]
    sql: str | None
    columns: list[str]
    rows: list[list[Any]]
    message: str | None
    error_kind: ErrorKind | None = None
    refusal_source: Literal["input_guardrail", "model"] | None = None
    # Model calls behind this answer; 0 when none finished (input block, 5xx).
    attempts: int = 0
    # How to draw the rows (result-visualization); null when there is no successful result.
    chart: Chart | None = None

    @field_serializer("rows")
    def _rows(self, rows: list[list[Any]]) -> list[list[Any]]:
        # Postgres NUMERIC arrives as Decimal; charts need JSON numbers, not strings.
        return [[float(v) if isinstance(v, Decimal) else v for v in row] for row in rows]


def _error(status_code: int, message: str, *, retry_after: int | None = None) -> JSONResponse:
    # Same shape as a normal answer so the client never special-cases 5xx bodies.
    body = AskResponse(status="error", sql=None, columns=[], rows=[], message=message)
    headers = {"Retry-After": str(retry_after)} if retry_after is not None else None
    return JSONResponse(status_code=status_code, content=body.model_dump(), headers=headers)


def create_app(
    *,
    generator: SqlGenerator,
    executor: QueryExecutor,
    cors_origins: list[str],
    input_guard: InputGuard | None = None,
    max_sql_retries: int = 0,
    daily_limit: DailyQuestionLimit | None = None,
    model_id: str | None = None,
) -> FastAPI:
    # model_id only pre-creates the token series at 0; the reply's own model ID is what gets counted.
    metrics = AskMetrics(daily_limit, model_id=model_id)

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

    @app.get("/metrics")
    async def prometheus_metrics() -> Response:
        # Internal only: nginx never forwards it; Alloy scrapes it on the compose network (D9).
        return Response(metrics.render(), media_type=CONTENT_TYPE_LATEST)

    @app.post("/api/ask", response_model=AskResponse)
    async def ask_question(body: AskRequest):
        # Checked before the guardrail and the model so a question over the limit costs nothing.
        # Invalid input is a 422 before this handler runs, so it never uses up the limit.
        if daily_limit is not None and not daily_limit.try_acquire():
            log.warning("daily question limit reached: %d/%d", daily_limit.count, daily_limit.limit)
            metrics.record_daily_limit_hit()
            return _error(429, "今日提問次數已達上限，請明天再試", retry_after=daily_limit.retry_after_seconds())
        started = time.perf_counter()
        try:
            result = await ask(body.question, generator, executor, input_guard=input_guard, max_retries=max_sql_retries)
        except InputGuardUnavailable:
            log.exception("input guardrail unavailable")
            metrics.record_unavailable("unavailable_guardrail", time.perf_counter() - started)
            return _error(502, "輸入檢查暫時無法使用，請稍後再試")
        except DatabaseUnavailable:
            log.exception("database unavailable")
            metrics.record_unavailable("unavailable_db", time.perf_counter() - started)
            return _error(503, "資料庫暫時無法使用，請稍後再試")
        except Exception:
            # Bedrock/network failures: full detail goes to the log, a generic message to the client.
            log.exception("ask failed")
            metrics.record_unavailable("unavailable_model", time.perf_counter() - started)
            return _error(502, "模型服務暫時無法使用，請稍後再試")
        metrics.record(result, time.perf_counter() - started)
        chart = choose_chart(result.columns, result.rows) if result.status == "ok" else None
        return AskResponse(**asdict(result), chart=chart)

    return app


@dataclass(frozen=True)
class Dependencies:
    generator: SqlGenerator
    executor: QueryExecutor
    input_guard: InputGuard | None


def build_dependencies(settings) -> Dependencies:
    """Real Bedrock, guardrail and database clients from settings; shared by the API and the eval."""
    from app.db import PgExecutor
    from app.input_guard import build_input_guard
    from app.llm import BedrockSqlGenerator, build_bedrock_client

    generator = BedrockSqlGenerator(
        build_bedrock_client(aws_region=settings.aws_region),
        model_id=settings.bedrock_model_id,
        effort=settings.bedrock_effort,
    )
    input_guard = None
    if settings.bedrock_guardrail_id:
        input_guard = build_input_guard(
            aws_region=settings.aws_region,
            guardrail_id=settings.bedrock_guardrail_id,
            guardrail_version=settings.bedrock_guardrail_version,
        )
    else:
        # Local development only; deployed environments must set it.
        log.warning("BEDROCK_GUARDRAIL_ID not set: questions skip the input guardrail")
    return Dependencies(generator=generator, executor=PgExecutor(settings.database_url), input_guard=input_guard)


def build_app() -> FastAPI:
    """Wire real dependencies from settings. Nothing connects until the first question."""
    from app.config import Settings
    from app.logging_setup import configure_logging

    configure_logging()
    settings = Settings()
    deps = build_dependencies(settings)
    return create_app(
        generator=deps.generator,
        executor=deps.executor,
        cors_origins=settings.cors_origins,
        input_guard=deps.input_guard,
        max_sql_retries=settings.max_sql_retries,
        daily_limit=DailyQuestionLimit(settings.daily_question_limit),
        model_id=settings.bedrock_model_id,
    )
