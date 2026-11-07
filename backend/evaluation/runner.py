"""Run golden questions one by one through the full pipeline and judge each answer."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol

from app.pipeline import AskResult
from app.pricing import cost_usd
from app.sql_guard import validate_sql
from evaluation.compare import judge
from evaluation.golden import GoldenQuestion
from evaluation.metrics import QuestionOutcome

AskFn = Callable[[str], Awaitable[AskResult]]


class ReferenceDb(Protocol):
    async def run(self, sql: str) -> tuple[list[str], list[list[Any]]]: ...


@dataclass(frozen=True)
class Estimate:
    questions: int
    guardrail_checks: int
    min_model_calls: int
    max_model_calls: int


@dataclass(frozen=True)
class ReferenceCheck:
    question: GoldenQuestion
    ok: bool
    rows: int = 0
    error: str | None = None


def select(questions: list[GoldenQuestion], only: set[str] | None) -> list[GoldenQuestion]:
    """Keep the file order; an unknown id is a typo that would silently shrink the run."""
    if not only:
        return questions
    unknown = only - {q.id for q in questions}
    if unknown:
        raise ValueError(f"unknown question ids: {sorted(unknown)}")
    return [q for q in questions if q.id in only]


def estimate(questions: list[GoldenQuestion], *, max_retries: int, guardrail: bool = True) -> Estimate:
    # Shown before a paid run: one guardrail check per question when the guardrail is on; one model
    # call per question when nothing is blocked or retried, up to max_retries more each.
    n = len(questions)
    return Estimate(
        questions=n,
        guardrail_checks=n if guardrail else 0,
        min_model_calls=n,
        max_model_calls=n * (max_retries + 1),
    )


async def run_eval(
    questions: list[GoldenQuestion],
    *,
    ask: AskFn,
    reference_db: ReferenceDb,
    on_progress: Callable[[QuestionOutcome], None] | None = None,
) -> list[QuestionOutcome]:
    # Sequential on purpose: no Bedrock throttling, and latencies are not inflated by contention.
    outcomes = []
    for question in questions:
        outcome = await _run_one(question, ask, reference_db)
        outcomes.append(outcome)
        if on_progress:
            on_progress(outcome)
    return outcomes


async def _run_one(question: GoldenQuestion, ask: AskFn, reference_db: ReferenceDb) -> QuestionOutcome:
    reference_rows = None
    if question.sql is not None:
        # Reference first: it is free, and a broken one would make the paid answer unjudgeable.
        try:
            _, reference_rows = await reference_db.run(validate_sql(question.sql))
        except Exception as e:
            return _failed(question, f"reference sql failed: {type(e).__name__}: {e}")
    try:
        result = await ask(question.question)
    except Exception as e:
        # One bad call (throttling, timeout) must not throw away the rest of a paid run.
        return _failed(question, f"{type(e).__name__}: {e}")
    verdict = judge(question, result, reference_rows=reference_rows)
    return QuestionOutcome(
        question=question,
        correct=verdict.correct,
        reason=verdict.reason,
        status=result.status,
        sql=result.sql,
        refusal_source=result.refusal_source,
        attempts=result.attempts,
        usage=result.usage,
        cost_usd=cost_usd(result.usage),
    )


def _failed(question: GoldenQuestion, error: str) -> QuestionOutcome:
    return QuestionOutcome(
        question=question, correct=False, status=None, attempts=0, usage=None, cost_usd=None, error=error
    )


async def dry_run(questions: list[GoldenQuestion], *, reference_db: ReferenceDb) -> list[ReferenceCheck]:
    """Check every reference SQL passes the guard and runs; no model or guardrail call is made."""
    checks = []
    for question in questions:
        if question.sql is None:
            continue
        try:
            _, rows = await reference_db.run(validate_sql(question.sql))
        except Exception as e:
            checks.append(ReferenceCheck(question=question, ok=False, error=f"{type(e).__name__}: {e}"))
            continue
        checks.append(ReferenceCheck(question=question, ok=True, rows=len(rows)))
    return checks
