"""Turn a question into SQL with Claude on Bedrock, using structured outputs."""

import asyncio
import json
import logging

from app.schema_context import SCHEMA_CONTEXT

log = logging.getLogger(__name__)

# Structured-output schema: the API guarantees the reply text is JSON of this shape.
# Ticket 3 extends it to sql / refuse / clarify.
REPLY_SCHEMA = {
    "type": "object",
    "properties": {"sql": {"type": "string", "description": "單一 PostgreSQL SELECT 查詢"}},
    "required": ["sql"],
    "additionalProperties": False,
}


class ReplyError(ValueError):
    """The model reply has no usable SQL; the message is safe to show users."""


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

    async def generate(self, question: str) -> str:
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


def parse_reply(message) -> str:
    """Extract the SQL from a structured-output reply."""
    # A truncated reply may hold half a query; never run it.
    if message.stop_reason == "max_tokens":
        raise ReplyError("模型回覆超過長度上限，未產生完整 SQL")
    if message.stop_reason == "refusal":
        raise ReplyError("模型拒絕回答這個問題")

    # Structured outputs should guarantee the shape; still verify, never trust blindly.
    block = next((b for b in message.content if b.type == "text"), None)
    try:
        data = json.loads(block.text) if block else None
    except json.JSONDecodeError:
        data = None
    sql = data.get("sql") if isinstance(data, dict) else None
    if not isinstance(sql, str):
        raise ReplyError("模型回覆格式不符，沒有 sql 欄位")

    if not sql.strip():
        raise ReplyError("模型回覆的 SQL 是空的")
    return sql
