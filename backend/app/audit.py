"""Audit trail for /api/ask (record-audit-log): one record per question, written by the handler.

Builds the record only; where it goes (the ask_audit log line and table) is the handler's job.
"""

import hashlib
import hmac
import logging
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

from app.metrics import Unavailable
from app.pipeline import AskResult
from app.pricing import cost_usd

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuditRecord:
    request_id: uuid.UUID
    visitor: str | None
    question: str
    status: str
    sql: str | None = None
    # Earlier tries as plain dicts: {error_kind, reason, sql}, ready for JSON and JSONB.
    failed_attempts: list[dict[str, Any]] = field(default_factory=list)
    refusal_source: str | None = None
    error_kind: str | None = None
    guardrail_reasons: tuple[str, ...] = ()
    model_id: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    guardrail_units: int = 0
    # None: a price or the usage was unknown, never a guessed zero.
    estimated_cost_usd: float | None = None
    elapsed_ms: int | None = None
    # Only when answered; the rows themselves are never recorded.
    row_count: int | None = None


def visitor_id(ip: str | None, key: bytes) -> str | None:
    """HMAC-SHA256 of the source IP: groups one visitor's questions without storing the IP."""
    if ip is None:
        return None
    return hmac.new(key, ip.encode(), hashlib.sha256).hexdigest()


def record_from_result(request_id: uuid.UUID, question: str, result: AskResult, *, visitor: str | None) -> AuditRecord:
    usage = result.usage
    return AuditRecord(
        request_id=request_id,
        visitor=visitor,
        question=question.strip(),
        status=result.status,
        sql=result.sql,
        failed_attempts=[asdict(attempt) for attempt in result.failed_attempts],
        refusal_source=result.refusal_source,
        error_kind=result.error_kind,
        guardrail_reasons=usage.guardrail_reasons,
        model_id=usage.model_id,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        guardrail_units=usage.guardrail.topic_units + usage.guardrail.content_units,
        estimated_cost_usd=cost_usd(usage),
        elapsed_ms=usage.elapsed_ms,
        row_count=len(result.rows) if result.status == "ok" else None,
    )


def record_from_outage(
    request_id: uuid.UUID, question: str, kind: Unavailable, *, visitor: str | None, elapsed_ms: int
) -> AuditRecord:
    """A dependency failed and the pipeline raised: only the outcome and the time are known."""
    return AuditRecord(
        request_id=request_id,
        visitor=visitor,
        question=question.strip(),
        status="error",
        error_kind=kind,
        elapsed_ms=elapsed_ms,
    )


class AuditWriter(Protocol):
    async def write(self, record: AuditRecord) -> None: ...


def log_record(record: AuditRecord) -> None:
    """The second copy (D6): one ask_audit line, the only log allowed to carry the question text."""
    fields = asdict(record)
    fields["request_id"] = str(record.request_id)
    log.info("ask_audit", extra={"event": "ask_audit", **fields})
