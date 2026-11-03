"""HTTP API: health check and question endpoint."""

from fastapi import FastAPI

from app.pipeline import QueryExecutor, SqlGenerator


def create_app(*, generator: SqlGenerator, executor: QueryExecutor, cors_origins: list[str]) -> FastAPI:
    app = FastAPI(title="BrewQL")

    @app.get("/health")
    async def health() -> dict[str, str]:
        # Liveness only: must not depend on the database or Bedrock.
        return {"status": "ok"}

    return app
