"""Titan Text Embeddings V2 via an injected boto3 bedrock-runtime client; no AWS call in tests."""

import io
import json

import pytest

from app.embeddings import EmbeddingError, TitanEmbedder

MODEL = "amazon.titan-embed-text-v2:0"


class FakeRuntime:
    def __init__(self, response: dict | None = None, error: Exception | None = None):
        self.calls: list[dict] = []
        self._response = response if response is not None else {"embedding": [0.5] * 1024, "inputTextTokenCount": 7}
        self._error = error

    def invoke_model(self, **kwargs):
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        return {"body": io.BytesIO(json.dumps(self._response).encode())}


async def test_embeds_text_with_the_configured_model_and_dimension():
    client = FakeRuntime()

    vector = await TitanEmbedder(client, model_id=MODEL, dimension=1024).embed("工作友善")

    assert vector == [0.5] * 1024
    [call] = client.calls
    assert call["modelId"] == MODEL
    # Normalised vectors make cosine distance the natural measure (D7).
    assert json.loads(call["body"]) == {"inputText": "工作友善", "dimensions": 1024, "normalize": True}


async def test_bedrock_error_propagates_for_the_caller_to_report():
    client = FakeRuntime(error=RuntimeError("AccessDeniedException"))

    with pytest.raises(RuntimeError, match="AccessDenied"):
        await TitanEmbedder(client, model_id=MODEL, dimension=1024).embed("x")


@pytest.mark.parametrize("response", [{}, {"embedding": "not a list"}, {"embedding": []}])
async def test_unreadable_response_is_an_error_not_an_empty_vector(response):
    with pytest.raises(EmbeddingError):
        await TitanEmbedder(FakeRuntime(response), model_id=MODEL, dimension=1024).embed("x")


@pytest.mark.parametrize("text", ["", "   "])
async def test_blank_text_is_refused_before_calling_bedrock(text):
    client = FakeRuntime()

    with pytest.raises(EmbeddingError):
        await TitanEmbedder(client, model_id=MODEL, dimension=1024).embed(text)

    assert client.calls == []
