"""Turn a question into SQL with Claude on Bedrock, using structured outputs."""

import json


class ReplyError(ValueError):
    """The model reply has no usable SQL; the message is safe to show users."""


def parse_reply(message) -> str:
    """Extract the SQL from a structured-output reply."""
    # A truncated reply may hold half a query; never run it.
    if message.stop_reason == "max_tokens":
        raise ReplyError("模型回覆超過長度上限，未產生完整 SQL")
    block = next(b for b in message.content if b.type == "text")
    sql = json.loads(block.text)["sql"]
    if not sql.strip():
        raise ReplyError("模型回覆的 SQL 是空的")
    return sql
