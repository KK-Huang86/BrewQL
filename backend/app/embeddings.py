"""Text embeddings for RAG (rag-knowledge-base D2): Amazon Titan Text Embeddings V2 on Bedrock."""

import asyncio
import json

DEFAULT_EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"
EMBEDDING_DIMENSION = 1024  # must match knowledge_documents.embedding (db/init/05_knowledge.sh)


class EmbeddingError(ValueError):
    """The text cannot be embedded or the response holds no usable vector."""


class TitanEmbedder:
    """InvokeModel via an injected boto3 bedrock-runtime client."""

    def __init__(self, client, *, model_id: str, dimension: int = EMBEDDING_DIMENSION):
        self._client = client
        self._model_id = model_id
        self._dimension = dimension

    async def embed(self, text: str) -> list[float]:
        if not text.strip():
            raise EmbeddingError("cannot embed blank text")
        body = json.dumps({"inputText": text, "dimensions": self._dimension, "normalize": True})
        # boto3 is synchronous; keep the event loop free. Errors propagate for the caller to report.
        response = await asyncio.to_thread(
            self._client.invoke_model,
            modelId=self._model_id,
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        vector = json.loads(response["body"].read()).get("embedding")
        if not isinstance(vector, list) or not vector:
            raise EmbeddingError(f"{self._model_id} returned no embedding")
        return vector


def build_embedder(*, aws_region: str, model_id: str) -> TitanEmbedder:
    import boto3
    from botocore.config import Config

    # Bounded like the guardrail client: a hung call must not hold a question or an import forever.
    config = Config(connect_timeout=3, read_timeout=5, retries={"max_attempts": 2, "mode": "standard"})
    return TitanEmbedder(boto3.client("bedrock-runtime", region_name=aws_region, config=config), model_id=model_id)
