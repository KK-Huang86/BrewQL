"""Summary numbers for one evaluation run."""

import math
from collections import Counter
from dataclasses import dataclass, field

from app.pipeline import AskUsage
from evaluation.golden import DIFFICULTIES, GoldenQuestion


@dataclass(frozen=True)
class QuestionOutcome:
    """One golden question after a run; status and usage are None when the service failed."""

    question: GoldenQuestion
    correct: bool
    status: str | None
    attempts: int
    usage: AskUsage | None
    cost_usd: float | None
    reason: str | None = None
    sql: str | None = None
    refusal_source: str | None = None
    error: str | None = None
    # Knowledge document ids used in rag mode.
    sources: tuple[str, ...] = ()


@dataclass(frozen=True)
class Score:
    correct: int
    total: int

    @property
    def accuracy(self) -> float | None:
        return self.correct / self.total if self.total else None


@dataclass(frozen=True)
class Summary:
    total: int
    correct: int
    accuracy: float | None
    by_difficulty: dict[str, Score]
    refusal_accuracy: float | None
    # Answerable questions the system refused or bounced back as a clarifying question.
    false_refusals: int
    service_errors: int
    p50_ms: int | None
    p95_ms: int | None
    avg_input_tokens: float | None
    avg_output_tokens: float | None
    avg_cost_usd: float | None
    total_cost_usd: float | None
    # False when some paid call used a model missing from the price table.
    cost_complete: bool
    attempts: dict[int, int] = field(default_factory=dict)


def summarize(outcomes: list[QuestionOutcome]) -> Summary:
    by_difficulty = {
        d: Score(
            correct=sum(o.correct for o in outcomes if o.question.difficulty == d),
            total=sum(o.question.difficulty == d for o in outcomes),
        )
        for d in DIFFICULTIES
    }
    correct = sum(o.correct for o in outcomes)
    used = [o for o in outcomes if o.usage is not None]
    costs = [o.cost_usd for o in used if o.cost_usd is not None]
    return Summary(
        total=len(outcomes),
        correct=correct,
        accuracy=correct / len(outcomes) if outcomes else None,
        by_difficulty=by_difficulty,
        refusal_accuracy=by_difficulty["refuse"].accuracy,
        false_refusals=sum(o.question.expect is None and o.status in ("refused", "clarify") for o in outcomes),
        service_errors=sum(o.error is not None for o in outcomes),
        p50_ms=_percentile([o.usage.elapsed_ms for o in used], 50),
        p95_ms=_percentile([o.usage.elapsed_ms for o in used], 95),
        avg_input_tokens=_mean([o.usage.input_tokens for o in used]),
        avg_output_tokens=_mean([o.usage.output_tokens for o in used]),
        avg_cost_usd=_mean(costs),
        total_cost_usd=sum(costs) if costs else None,
        cost_complete=len(costs) == len(used),
        attempts=dict(sorted(Counter(o.attempts for o in outcomes).items())),
    )


def _percentile(values: list[int], p: int) -> int | None:
    # Nearest rank: always a latency that actually happened; with 15 questions p95 is the slowest.
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(math.ceil(p / 100 * len(ordered)), 1) - 1]


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None
