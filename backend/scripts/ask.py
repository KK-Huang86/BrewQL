"""Smoke test: ask Bedrock for SQL from the terminal (needs AWS credentials + model access).

uv run python -m scripts.ask "台北市有幾家咖啡店？"
"""

import asyncio
import logging
import sys

from anthropic import AnthropicBedrock

from app.config import Settings
from app.llm import BedrockSqlGenerator


async def main(question: str) -> None:
    settings = Settings()
    client = AnthropicBedrock(aws_region=settings.aws_region)
    generator = BedrockSqlGenerator(client, model_id=settings.bedrock_model_id, effort=settings.bedrock_effort)
    sql = await generator.generate(question)
    print(sql)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    asyncio.run(main(" ".join(sys.argv[1:]) or "台北市有幾家咖啡店？"))
