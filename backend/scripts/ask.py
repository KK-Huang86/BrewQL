"""Smoke test: ask Bedrock for SQL from the terminal (needs AWS credentials + model access).

uv run python -m scripts.ask "台北市有幾家咖啡店？"
"""

import asyncio
import logging
import sys

from app.config import Settings
from app.llm import BedrockSqlGenerator, build_bedrock_client
from app.logging_setup import configure_logging


class _UsageCatcher(logging.Handler):
    """Pick the token counts out of the generator's structured log record."""

    def __init__(self):
        super().__init__()
        self.usage: dict[str, int] = {}

    def emit(self, record: logging.LogRecord) -> None:
        if hasattr(record, "input_tokens"):
            self.usage = {"input_tokens": record.input_tokens, "output_tokens": record.output_tokens}


async def main(question: str, *, client=None, model_id: str | None = None, effort: str | None = None) -> None:
    if client is None:
        settings = Settings()
        client = build_bedrock_client(aws_region=settings.aws_region)
        model_id, effort = settings.bedrock_model_id, settings.bedrock_effort
    generator = BedrockSqlGenerator(client, model_id=model_id, effort=effort)

    catcher = _UsageCatcher()
    llm_log = logging.getLogger("app.llm")
    old_level = llm_log.level
    # The usage record is INFO; make sure it is emitted whatever logging was configured.
    llm_log.setLevel(logging.INFO)
    llm_log.addHandler(catcher)
    try:
        reply = await generator.generate(question)
    finally:
        llm_log.removeHandler(catcher)
        llm_log.setLevel(old_level)
    print(reply.sql if reply.kind == "sql" else f"[{reply.kind}] {reply.message}")
    print(f"input_tokens={catcher.usage.get('input_tokens')} output_tokens={catcher.usage.get('output_tokens')}")


if __name__ == "__main__":
    configure_logging()
    asyncio.run(main(" ".join(sys.argv[1:]) or "台北市有幾家咖啡店？"))
