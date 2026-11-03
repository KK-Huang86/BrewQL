"""Turn a question into SQL with Claude on Bedrock, using structured outputs."""

import json


def parse_reply(message) -> str:
    """Extract the SQL from a structured-output reply."""
    block = next(b for b in message.content if b.type == "text")
    return json.loads(block.text)["sql"]
