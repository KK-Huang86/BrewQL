"""rag mode is priced and observed like the rest of a question (rag-knowledge-base D9).

The embedding's tokens join the question's usage, so metrics, the audit trail and evals all count them;
a retrieval failure is its own outage and the SQL model is never called.
"""

import pytest
from fastapi.testclient import TestClient

from app.input_guard import GuardrailUsage
from app.llm import ModelUsage, Reply
from app.main import create_app
from app.pipeline import AskUsage, ask
from app.pricing import cost_usd, embedding_cost_usd
from app.retrieval import RetrievalResult, RetrievalUnavailable
from tests.test_metrics import ask_total, scrape, value
from tests.test_pipeline_rag import CAFES, Executor

TITAN = "amazon.titan-embed-text-v2:0"
HAIKU_US = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
FOUND = RetrievalResult(schema=(CAFES,), embedding_model_id=TITAN, embedding_tokens=12)


class Retriever:
    def __init__(self, result=FOUND, error=None):
        self._result, self._error = result, error

    async def retrieve(self, question):
        if self._error:
            raise self._error
        return self._result

    async def close(self):
        pass


class Generator:
    def __init__(self):
        self.calls = 0

    async def generate(self, question, feedback=(), *, context=None):
        self.calls += 1
        return Reply(kind="sql", sql="SELECT 1", usage=ModelUsage(HAIKU_US, 2000, 50))


# --- price ---------------------------------------------------------------------------------------


def test_titan_v2_costs_two_cents_per_million_tokens():
    assert embedding_cost_usd(AskUsage(embedding_model_id=TITAN, embedding_tokens=1_000_000)) == pytest.approx(0.02)


def test_question_cost_includes_the_embedding():
    usage = AskUsage(
        model_id=HAIKU_US, input_tokens=2000, output_tokens=50, embedding_model_id=TITAN, embedding_tokens=10_000
    )

    # 2000 x $1.10/M + 50 x $5.50/M + 10,000 x $0.02/M
    assert cost_usd(usage) == pytest.approx(0.0022 + 0.000275 + 0.0002)


def test_static_question_has_no_embedding_cost():
    assert embedding_cost_usd(AskUsage()) == 0.0


def test_unknown_embedding_model_makes_the_cost_unknown_not_zero():
    usage = AskUsage(model_id=HAIKU_US, input_tokens=1, embedding_model_id="cohere.embed-v4", embedding_tokens=5)

    assert embedding_cost_usd(usage) is None
    assert cost_usd(usage) is None


# --- pipeline ------------------------------------------------------------------------------------


async def test_rag_answer_carries_embedding_usage_and_a_retrieval_timing():
    result = await ask("q", Generator(), Executor(), retriever=Retriever())

    assert (result.usage.embedding_model_id, result.usage.embedding_tokens) == (TITAN, 12)
    assert [t.stage for t in result.usage.stages] == ["retrieval", "model", "db"]


async def test_retrieval_failure_propagates_and_the_model_is_never_called():
    generator = Generator()

    with pytest.raises(RetrievalUnavailable):
        await ask("q", generator, Executor(), retriever=Retriever(error=RetrievalUnavailable("ThrottlingException")))

    assert generator.calls == 0


# --- API, metrics and audit ----------------------------------------------------------------------


class Writer:
    def __init__(self):
        self.records = []

    async def write(self, record):
        self.records.append(record)

    async def close(self):
        pass


def make_client(retriever, writer=None):
    app = create_app(
        generator=Generator(), executor=Executor(), cors_origins=[], retriever=retriever, audit_writer=writer
    )
    return TestClient(app, raise_server_exceptions=False)


def test_retrieval_outage_is_a_502_with_its_own_kind():
    writer = Writer()
    c = make_client(Retriever(error=RetrievalUnavailable("connection refused")), writer)

    response = c.post("/api/ask", json={"question": "工作友善的店有幾家？"})

    assert response.status_code == 502
    assert response.json()["message"] == "知識檢索暫時無法使用，請稍後再試"
    assert ask_total(scrape(c), "error", error_kind="unavailable_retrieval") == 1
    [record] = writer.records
    assert record.error_kind == "unavailable_retrieval"


def test_metrics_count_embedding_tokens_cost_and_retrieval_time():
    c = make_client(Retriever())

    c.post("/api/ask", json={"question": "工作友善的店有幾家？"})

    samples = scrape(c)
    assert value(samples, "brewql_llm_tokens_total", model=TITAN, direction="input") == 12
    assert value(samples, "brewql_estimated_cost_usd_total", component="embedding") == pytest.approx(12 * 0.02 / 1e6)
    assert value(samples, "brewql_stage_seconds_count", stage="retrieval") == 1


def test_new_series_start_at_zero():
    # increase() needs two samples, so the first retrieval outage must not be born at 1.
    samples = scrape(make_client(None))

    assert (
        "brewql_ask_total",
        frozenset({"status": "error", "refusal_source": "", "error_kind": "unavailable_retrieval"}.items()),
    ) in samples
    assert ("brewql_stage_seconds_count", frozenset({"stage": "retrieval"}.items())) in samples
    assert ("brewql_estimated_cost_usd_total", frozenset({"component": "embedding"}.items())) in samples


def test_audit_cost_of_a_rag_answer_includes_the_embedding():
    writer = Writer()

    make_client(Retriever(), writer).post("/api/ask", json={"question": "工作友善的店有幾家？"})

    [record] = writer.records
    usage = AskUsage(
        model_id=HAIKU_US,
        input_tokens=2000,
        output_tokens=50,
        guardrail=GuardrailUsage(),
        embedding_model_id=TITAN,
        embedding_tokens=12,
    )
    assert record.estimated_cost_usd == pytest.approx(cost_usd(usage))
