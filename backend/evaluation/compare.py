"""Execution accuracy: an answer is right when its rows match the reference result, whatever the SQL."""

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.pipeline import AskResult
from evaluation.golden import GoldenQuestion


@dataclass(frozen=True)
class Verdict:
    correct: bool
    reason: str | None = None


def judge(question: GoldenQuestion, result: AskResult, *, reference_rows: list[list[Any]] | None) -> Verdict:
    if question.expect is not None:
        # Either layer may refuse; the report keeps refusal_source to show which one did.
        if result.status == question.expect:
            return Verdict(correct=True)
        return Verdict(correct=False, reason=f"expected {question.expect}, got {result.status}")
    if result.status != "ok":
        return Verdict(correct=False, reason=f"expected an answer, got {result.status}: {result.message}")
    if same_rows(result.rows, reference_rows or [], ordered=question.ordered):
        return Verdict(correct=True)
    return Verdict(correct=False, reason=f"result differs: {len(result.rows)} rows vs {len(reference_rows or [])}")


def same_rows(actual: list[list[Any]], expected: list[list[Any]], *, ordered: bool) -> bool:
    """Compare rows ignoring column names and order; row order matters only when ordered."""
    left, right = [_row_key(r) for r in actual], [_row_key(r) for r in expected]
    if ordered:
        return left == right
    # A multiset, so duplicated rows still count.
    return Counter(left) == Counter(right)


def _row_key(row: list[Any]) -> tuple:
    # Sorting the values drops column order (aliases and SELECT order differ freely); the rare cost is
    # that swapped values across columns would match, an accepted trade-off noted in the design.
    return tuple(sorted((_value_key(v) for v in row), key=repr))


def _value_key(value: Any) -> tuple:
    # Tag each value with its kind so True never equals 1 and "4.23" never equals 4.23.
    if value is None:
        return ("null",)
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, int | float | Decimal):
        return ("num", round(float(value), 2))
    if isinstance(value, datetime | date):
        return ("text", value.isoformat())
    return ("text", str(value))
