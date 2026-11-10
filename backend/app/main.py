"""HTTP API: health check and question endpoint."""

import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST
from pydantic import BaseModel, StringConstraints, field_serializer

from app.audit import (
    AuditRecord,
    AuditWriter,
    PgAuditWriter,
    record_from_outage,
    record_from_result,
    store,
    visitor_id,
)
from app.charts import Chart, choose_chart
from app.daily_limit import DailyQuestionLimit
from app.db import DatabaseUnavailable
from app.input_guard import InputGuardUnavailable
from app.llm import ErrorKind
from app.metrics import AskMetrics, Unavailable
from app.pipeline import MAX_QUESTION_CHARS, InputGuard, QueryExecutor, SqlGenerator, ask

log = logging.getLogger(__name__)
# HMAC-SHA256 key for visitor IDs; shorter keys make the IPv4 space cheap to brute-force (D5).
MIN_VISITOR_KEY_LENGTH = 32


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


@dataclass(frozen=True)
class _Outage:
    kind: Unavailable
    status_code: int
    message: str
    log_message: str


def _outage(exc: Exception) -> _Outage:
    """A dependency the pipeline could not reach: how it is counted, answered and logged."""
    if isinstance(exc, InputGuardUnavailable):
        return _Outage("unavailable_guardrail", 502, "輸入檢查暫時無法使用，請稍後再試", "input guardrail unavailable")
    if isinstance(exc, DatabaseUnavailable):
        return _Outage("unavailable_db", 503, "資料庫暫時無法使用，請稍後再試", "database unavailable")
    # Bedrock/network failures: full detail goes to the log, a generic message to the client.
    return _Outage("unavailable_model", 502, "模型服務暫時無法使用，請稍後再試", "ask failed")


def create_app(
    *,
    generator: SqlGenerator,
    executor: QueryExecutor,
    cors_origins: list[str],
    input_guard: InputGuard | None = None,
    max_sql_retries: int = 0,
    daily_limit: DailyQuestionLimit | None = None,
    model_id: str | None = None,
    audit_writer: AuditWriter | None = None,
    visitor_key: bytes | None = None,
    audit_timeout_seconds: float = 2.0,
) -> FastAPI:
    # model_id only pre-creates the token series at 0; the reply's own model ID is what gets counted.
    metrics = AskMetrics(daily_limit, model_id=model_id)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        # Release pooled connections so restarts don't leave sessions open on Postgres.
        await executor.close()
        if audit_writer is not None:
            await audit_writer.close()

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

    async def record_audit(record: AuditRecord) -> None:
        await store(record, audit_writer, timeout_seconds=audit_timeout_seconds, failures=metrics.audit_write_failures)

    def visitor_of(request: Request) -> str | None:
        # nginx overwrites X-Real-IP with the connecting address; direct calls (SSH tunnel) have none.
        ip = request.headers.get("x-real-ip") or (request.client.host if request.client else None)
        return visitor_id(ip, visitor_key) if visitor_key else None

    @app.post("/api/ask", response_model=AskResponse)
    async def ask_question(body: AskRequest, request: Request):
        # Checked before the guardrail and the model so a question over the limit costs nothing.
        # Invalid input is a 422 before this handler runs, so it never uses up the limit.
        if daily_limit is not None and not daily_limit.try_acquire():
            log.warning("daily question limit reached: %d/%d", daily_limit.count, daily_limit.limit)
            metrics.record_daily_limit_hit()
            return _error(429, "今日提問次數已達上限，請明天再試", retry_after=daily_limit.retry_after_seconds())
        started = time.perf_counter()
        request_id = uuid.uuid4()
        try:
            result = await ask(body.question, generator, executor, input_guard=input_guard, max_retries=max_sql_retries)
        except Exception as exc:
            outage = _outage(exc)
            log.exception(outage.log_message)
            seconds = time.perf_counter() - started
            metrics.record_unavailable(outage.kind, seconds)
            await record_audit(
                record_from_outage(
                    request_id, body.question, outage.kind, visitor=visitor_of(request), elapsed_ms=int(seconds * 1000)
                )
            )
            return _error(outage.status_code, outage.message)
        metrics.record(result, time.perf_counter() - started)
        await record_audit(record_from_result(request_id, body.question, result, visitor=visitor_of(request)))
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
    # D4: every question must leave an audit trail, so a missing setting stops startup.
    if not settings.audit_database_url:
        raise RuntimeError("AUDIT_DATABASE_URL is required (genbi_audit_writer connection)")
    if len(settings.audit_ip_hmac_key) < MIN_VISITOR_KEY_LENGTH:
        raise RuntimeError(f"AUDIT_IP_HMAC_KEY must be at least {MIN_VISITOR_KEY_LENGTH} characters")
    deps = build_dependencies(settings)
    return create_app(
        generator=deps.generator,
        executor=deps.executor,
        cors_origins=settings.cors_origins,
        input_guard=deps.input_guard,
        max_sql_retries=settings.max_sql_retries,
        daily_limit=DailyQuestionLimit(settings.daily_question_limit),
        model_id=settings.bedrock_model_id,
        audit_writer=PgAuditWriter(settings.audit_database_url),
        visitor_key=settings.audit_ip_hmac_key.encode(),
    )
