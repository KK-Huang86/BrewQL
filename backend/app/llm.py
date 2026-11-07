"""Turn a question into SQL with Claude on Bedrock, using structured outputs."""

import asyncio
import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, get_args

from app.schema_context import SCHEMA_CONTEXT

log = logging.getLogger(__name__)

# The model's three possible decisions; the schema, the type and the parser all use this.
ReplyKind = Literal["sql", "refuse", "clarify"]
REPLY_KINDS: tuple[str, ...] = get_args(ReplyKind)

# Structured-output schema: the API guarantees the reply text is JSON of this shape.
# All fields are required (structured outputs need that); unused ones are "".
REPLY_SCHEMA = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": list(REPLY_KINDS), "description": "回覆類型"},
        "sql": {"type": "string", "description": "kind=sql 時的單一 PostgreSQL SELECT 查詢，其餘為空字串"},
        "message": {"type": "string", "description": "kind=refuse 的原因或 kind=clarify 的反問，kind=sql 時為空字串"},
    },
    "required": ["kind", "sql", "message"],
    "additionalProperties": False,
}

REFUSAL_MESSAGE = "模型拒絕回答這個問題"

# Which step rejected an attempt; the pipeline reports it and feedback names it for the model.
ErrorKind = Literal["generation", "guardrail", "query"]
_FEEDBACK_LABELS: dict[str, str] = {
    "generation": "回覆不符合格式",
    "guardrail": "SQL 被 SQL 防護拒絕",
    "query": "SQL 發生資料庫執行錯誤",
}


@dataclass(frozen=True)
class FailedAttempt:
    """One earlier try that did not produce a usable result; sql is None when none was produced."""

    error_kind: ErrorKind
    reason: str
    sql: str | None = None


def _feedback_text(attempt: FailedAttempt) -> str:
    return f"上一次的{_FEEDBACK_LABELS[attempt.error_kind]}：{attempt.reason}\n請修正後依相同格式重新回覆。"


def build_messages(question: str, feedback: Sequence[FailedAttempt] = ()) -> list[dict]:
    """Replay failed attempts as turns: the model's SQL as its own reply, the reason as the user's next turn."""
    turns: list[tuple[str, str]] = [("user", question)]
    for attempt in feedback:
        if attempt.sql is not None:
            reply = json.dumps({"kind": "sql", "sql": attempt.sql, "message": ""}, ensure_ascii=False)
            turns.append(("assistant", reply))
        turns.append(("user", _feedback_text(attempt)))
    # Without a model turn to replay, user texts end up adjacent; the API needs alternating roles.
    messages: list[dict] = []
    for role, text in turns:
        if messages and messages[-1]["role"] == role:
            messages[-1]["content"] += "\n\n" + text
        else:
            messages.append({"role": role, "content": text})
    return messages


# 3 attempts x 15s (+ short backoff) stays under nginx's 60s proxy_read_timeout.
BEDROCK_TIMEOUT_SECONDS = 15
BEDROCK_MAX_RETRIES = 2


def build_bedrock_client(*, aws_region: str):
    """Bedrock client shared by the API and the smoke script; no network call until used."""
    from anthropic import AnthropicBedrock

    return AnthropicBedrock(aws_region=aws_region, timeout=BEDROCK_TIMEOUT_SECONDS, max_retries=BEDROCK_MAX_RETRIES)


class ReplyError(ValueError):
    """The model reply is unusable; the message is safe to show users."""


@dataclass(frozen=True)
class Reply:
    """What the model decided: run this SQL, refuse, or ask the user to clarify."""

    kind: ReplyKind
    sql: str | None = None
    message: str | None = None


class BedrockSqlGenerator:
    """Generate SQL with Claude via an injected Bedrock client (anthropic.AnthropicBedrock)."""

    def __init__(self, client, *, model_id: str, effort: str | None = "low", max_tokens: int = 4000):
        self._client = client
        self._model_id = model_id
        self._max_tokens = max_tokens
        # Effort exists on Claude 4.6+/5.x only; None omits it for models like Haiku 4.5.
        self._output_config: dict = {"format": {"type": "json_schema", "schema": REPLY_SCHEMA}}
        if effort:
            self._output_config["effort"] = effort

    async def generate(self, question: str, feedback: Sequence[FailedAttempt] = ()) -> Reply:
        # The SDK call is synchronous; run it in a worker thread so the event loop stays free.
        try:
            message = await asyncio.to_thread(
                self._client.messages.create,
                model=self._model_id,
                max_tokens=self._max_tokens,
                system=SCHEMA_CONTEXT,
                messages=build_messages(question, feedback),
                output_config=self._output_config,
            )
        except Exception as e:
            # Re-raise so the API answers 5xx; it logs the traceback, here we only add the model.
            log.error(
                "bedrock call failed model=%s error=%s",
                self._model_id,
                f"{type(e).__name__}: {e}",
                extra={"model_id": self._model_id},
            )
            raise
        log.info(
            "bedrock call model=%s input_tokens=%d output_tokens=%d stop_reason=%s",
            self._model_id,
            message.usage.input_tokens,
            message.usage.output_tokens,
            message.stop_reason,
            extra={
                "model_id": self._model_id,
                "input_tokens": message.usage.input_tokens,
                "output_tokens": message.usage.output_tokens,
                "stop_reason": message.stop_reason,
            },
        )
        return parse_reply(message)


def parse_reply(message) -> Reply:
    """Turn a structured-output reply into a Reply, checking kind and content agree."""
    # A truncated reply may hold half a query; never run it.
    if message.stop_reason == "max_tokens":
        raise ReplyError("模型回覆超過長度上限，未產生完整 SQL")
    # A safety refusal is a refuse; its content is not read.
    if message.stop_reason == "refusal":
        return Reply(kind="refuse", message=REFUSAL_MESSAGE)

    # Structured outputs should guarantee the shape; still verify, never trust blindly.
    block = next((b for b in message.content if b.type == "text"), None)
    try:
        data = json.loads(block.text) if block else None
    except json.JSONDecodeError:
        data = None
    if not isinstance(data, dict) or data.get("kind") not in REPLY_KINDS:
        raise ReplyError("模型回覆格式不符，沒有有效的回覆類型")
    kind, sql, text = data["kind"], data.get("sql"), data.get("message")
    if not isinstance(sql, str) or not isinstance(text, str):
        raise ReplyError("模型回覆格式不符，sql 與 message 必須是字串")

    if kind == "sql":
        if not sql.strip():
            raise ReplyError("模型回覆的 SQL 是空的")
        return Reply(kind="sql", sql=sql)
    # Only kind=sql may carry SQL toward the executor.
    if not text.strip():
        raise ReplyError("模型回覆的拒答原因或反問是空的")
    return Reply(kind=kind, message=text.strip())
