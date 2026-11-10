"""Embed backend/knowledge/*.yaml with Titan and sync them into pgvector (rag-knowledge-base 2.3).

    docker compose run --rm knowledge-import          # in the compose stack
    uv --directory backend run python -m scripts.import_knowledge   # needs KNOWLEDGE_DATABASE_URL

Re-running is free when nothing changed. Exit codes: 0 done, 1 import failed (nothing written),
2 invalid documents or settings (nothing embedded).
"""

import asyncio
import sys
from pathlib import Path

from app.knowledge import KNOWLEDGE_DIR, KnowledgeError, load_knowledge
from app.knowledge_sync import Embedder, ImportFailed, KnowledgeStore, sync_knowledge


async def main(directory: Path, *, embedder: Embedder, store: KnowledgeStore, model_id: str, dimension: int) -> int:
    try:
        docs = load_knowledge(directory)
    except KnowledgeError as e:
        print(f"knowledge documents error: {e}", file=sys.stderr)
        return 2
    try:
        report = await sync_knowledge(docs, embedder=embedder, store=store, model_id=model_id, dimension=dimension)
    except ImportFailed as e:
        print(f"import failed: {e}", file=sys.stderr)
        return 1
    print(
        f"{len(docs)} documents, model {model_id}: added={report.added} updated={report.updated} "
        f"unchanged={report.unchanged} deleted={report.deleted}"
    )
    return 0


async def _run() -> int:
    from app.config import Settings
    from app.embeddings import EMBEDDING_DIMENSION, build_embedder
    from app.knowledge_sync import PgKnowledgeStore
    from app.logging_setup import configure_logging

    configure_logging()
    settings = Settings()
    if not settings.knowledge_database_url:
        print("KNOWLEDGE_DATABASE_URL is not set (genbi_knowledge_writer)", file=sys.stderr)
        return 2
    store = PgKnowledgeStore(settings.knowledge_database_url)
    try:
        return await main(
            KNOWLEDGE_DIR,
            embedder=build_embedder(aws_region=settings.aws_region, model_id=settings.embedding_model_id),
            store=store,
            model_id=settings.embedding_model_id,
            dimension=EMBEDDING_DIMENSION,
        )
    finally:
        await store.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(_run()))
