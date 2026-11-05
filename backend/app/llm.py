"""Turn a question into SQL with Claude on Bedrock, using structured outputs."""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Literal

from app.schema_context import SCHEMA_CONTEXT

log = logging.getLogger(__name__)

# Structured-output schema: the API guarantees the reply text is JSON of this shape.
# All fields are required (structured outputs need that); unused ones are "".
REPLY_SCHEMA = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": ["sql", "refuse", "clarify"], "description": "回覆類型"},
        "sql": {"type": "string", "description": "kind=sql 時的單一 PostgreSQL SELECT 查詢，其餘為空字串"},
        "message": {"type": "string", "description": "kind=refuse 的原因或 kind=clarify 的反問，kind=sql 時為空字串"},
    },
    "required": ["kind", "sql", "message"],
    "additionalProperties": False,
}

REFUSAL_MESSAGE = "模型拒絕回答這個問題"


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

    kind: Literal["sql", "refuse", "clarify"]
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

    async def generate(self, question: str) -> Reply:
        # The SDK call is synchronous; run it in a worker thread so the event loop stays free.
        try:
            message = await asyncio.to_thread(
                self._client.messages.create,
                model=self._model_id,
                max_tokens=self._max_tokens,
                system=SCHEMA_CONTEXT,
                messages=[{"role": "user", "content": question}],
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
    if not isinstance(data, dict) or data.get("kind") not in ("sql", "refuse", "clarify"):
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
