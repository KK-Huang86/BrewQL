"""Summary numbers for one evaluation run."""

import pytest

from app.input_guard import GuardrailUsage
from app.pipeline import AskUsage
from evaluation.golden import GoldenQuestion
from evaluation.metrics import QuestionOutcome, summarize


def outcome(qid, difficulty, correct, *, status="ok", attempts=1, ms=1000, tokens=(1000, 50), cost=0.002, usage=True):
    q = GoldenQuestion(
        id=qid,
        difficulty=difficulty,
        question=qid,
        sql=None if difficulty == "refuse" else "SELECT 1",
        expect="refused" if difficulty == "refuse" else None,
    )
    u = AskUsage(
        model_id="m", input_tokens=tokens[0], output_tokens=tokens[1], guardrail=GuardrailUsage(1, 1), elapsed_ms=ms
    )
    return QuestionOutcome(
        question=q,
        correct=correct,
        status=status,
        attempts=attempts,
        usage=u if usage else None,
        cost_usd=cost,
    )


def test_accuracy_overall_and_per_difficulty():
    summary = summarize(
        [
            outcome("q1", "easy", True),
            outcome("q2", "easy", True),
            outcome("q3", "medium", False),
            outcome("q4", "hard", True),
            outcome("q5", "refuse", True, status="refused"),
        ]
    )

    assert (summary.total, summary.correct) == (5, 4)
    assert summary.accuracy == pytest.approx(0.8)
    assert summary.by_difficulty["easy"].accuracy == 1.0
    assert summary.by_difficulty["medium"].accuracy == 0.0
    assert (summary.by_difficulty["refuse"].correct, summary.by_difficulty["refuse"].total) == (1, 1)


def test_refusal_accuracy_and_false_refusals():
    summary = summarize(
        [
            outcome("q1", "refuse", True, status="refused"),
            outcome("q2", "refuse", False, status="ok"),
            # Answerable questions the system refused or bounced back: blocked by mistake.
            outcome("q3", "easy", False, status="refused"),
            outcome("q4", "medium", False, status="clarify"),
            outcome("q5", "easy", False, status="error"),
        ]
    )

    assert summary.refusal_accuracy == pytest.approx(0.5)
    assert summary.false_refusals == 2


def test_latency_percentiles_use_nearest_rank():
    summary = summarize([outcome(f"q{i}", "easy", True, ms=ms) for i, ms in enumerate([100, 200, 300, 400, 5000])])

    assert summary.p50_ms == 300
    assert summary.p95_ms == 5000


def test_average_tokens_and_cost_per_question():
    summary = summarize(
        [
            outcome("q1", "easy", True, tokens=(1000, 40), cost=0.002),
            outcome("q2", "easy", True, tokens=(3000, 60), cost=0.004),
        ]
    )

    assert summary.avg_input_tokens == 2000
    assert summary.avg_output_tokens == 50
    assert summary.avg_cost_usd == pytest.approx(0.003)
    assert summary.total_cost_usd == pytest.approx(0.006)
    assert summary.cost_complete is True


def test_unknown_cost_is_flagged_not_counted_as_free():
    summary = summarize([outcome("q1", "easy", True, cost=0.002), outcome("q2", "easy", True, cost=None)])

    assert summary.cost_complete is False
    assert summary.avg_cost_usd == pytest.approx(0.002)


def test_attempts_distribution():
    summary = summarize(
        [
            outcome("q1", "easy", True, attempts=1),
            outcome("q2", "easy", True, attempts=2),
            outcome("q3", "easy", True, attempts=1),
            outcome("q4", "refuse", True, status="refused", attempts=0),
        ]
    )

    assert summary.attempts == {0: 1, 1: 2, 2: 1}


def test_service_errors_count_as_wrong_and_skip_usage_stats():
    failed = QuestionOutcome(
        question=GoldenQuestion(id="q2", difficulty="easy", question="q", sql="SELECT 1"),
        correct=False,
        status=None,
        attempts=0,
        usage=None,
        cost_usd=None,
        error="ThrottlingException",
    )

    summary = summarize([outcome("q1", "easy", True, ms=800), failed])

    assert summary.accuracy == pytest.approx(0.5)
    assert summary.p50_ms == 800
    assert summary.service_errors == 1
    # No usage means no bill to count; the run's cost is still complete for the calls that happened.
    assert summary.cost_complete is True


def test_empty_run_has_no_numbers_instead_of_crashing():
    summary = summarize([])

    assert summary.total == 0
    assert summary.accuracy is None
    assert summary.refusal_accuracy is None
    assert summary.p50_ms is None
    assert summary.avg_cost_usd is None
    assert summary.attempts == {}
