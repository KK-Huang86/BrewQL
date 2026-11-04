"""Smoke test: ask Bedrock for SQL from the terminal (needs AWS credentials + model access).

uv run python -m scripts.ask "台北市有幾家咖啡店？"
"""

import asyncio
import sys

from app.config import Settings
from app.llm import BedrockSqlGenerator, build_bedrock_client
from app.logging_setup import configure_logging


async def main(question: str) -> None:
    settings = Settings()
    client = build_bedrock_client(aws_region=settings.aws_region)
    generator = BedrockSqlGenerator(client, model_id=settings.bedrock_model_id, effort=settings.bedrock_effort)
    sql = await generator.generate(question)
    print(sql)


if __name__ == "__main__":
    configure_logging()
    asyncio.run(main(" ".join(sys.argv[1:]) or "台北市有幾家咖啡店？"))
