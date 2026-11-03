"""Turn a question into SQL with Claude on Bedrock, using structured outputs."""

import json


class ReplyError(ValueError):
    """The model reply has no usable SQL; the message is safe to show users."""


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
