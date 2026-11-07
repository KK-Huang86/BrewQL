"""Judging an answer by its result, not its SQL text (execution accuracy)."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.pipeline import AskResult
from evaluation.compare import judge, same_rows
from evaluation.golden import GoldenQuestion

SQL_Q = GoldenQuestion(id="q", difficulty="easy", question="q", sql="SELECT COUNT(*) FROM cafes")
ORDERED_Q = GoldenQuestion(id="q", difficulty="medium", question="q", sql="SELECT 1", ordered=True)


def answered(rows, columns=("n",)):
    return AskResult(status="ok", sql="SELECT ...", columns=list(columns), rows=rows, attempts=1)


def test_different_sql_with_the_same_result_is_correct():
    # System wrote COUNT(id), the reference COUNT(*): both 42.
    assert judge(SQL_Q, answered([[42]]), reference_rows=[[42]]).correct


def test_different_result_is_wrong_and_says_so():
    verdict = judge(SQL_Q, answered([[41]]), reference_rows=[[42]])

    assert not verdict.correct
    assert verdict.reason


def test_row_order_is_ignored_unless_the_question_asks_for_it():
    actual, reference = [["大安區", 40], ["中山區", 35]], [["中山區", 35], ["大安區", 40]]

    assert judge(SQL_Q, answered(actual), reference_rows=reference).correct
    assert not judge(ORDERED_Q, answered(actual), reference_rows=reference).correct
    assert judge(ORDERED_Q, answered(reference), reference_rows=reference).correct


def test_column_names_and_order_are_ignored():
    actual = answered([[40, "大安區"]], columns=("store_count", "district"))

    assert judge(SQL_Q, actual, reference_rows=[["大安區", 40]]).correct


def test_an_extra_or_missing_column_is_wrong():
    assert not same_rows([["板橋區", Decimal("4.38")]], [["板橋區"]], ordered=False)
    assert not same_rows([["板橋區"]], [["板橋區", Decimal("4.38")]], ordered=False)


def test_numbers_match_after_rounding_to_two_places():
    assert same_rows([[4.2300001]], [[Decimal("4.23")]], ordered=False)
    assert same_rows([[Decimal("52.0")]], [[52]], ordered=False)
    assert not same_rows([[4.24]], [[Decimal("4.23")]], ordered=False)


def test_booleans_are_not_numbers():
    assert not same_rows([[True]], [[1]], ordered=False)
    assert same_rows([[True]], [[True]], ordered=False)


def test_dates_compare_as_iso_strings():
    assert same_rows([[date(2025, 1, 1)]], [["2025-01-01"]], ordered=False)
    assert same_rows(
        [[datetime(2025, 1, 1, 9, 30, tzinfo=UTC)]], [[datetime(2025, 1, 1, 9, 30, tzinfo=UTC)]], ordered=False
    )
    assert not same_rows([[date(2025, 1, 1)]], [["2025-01"]], ordered=False)


def test_duplicate_rows_count():
    # Rows are a multiset: one row is not the same answer as the same row twice.
    assert not same_rows([["板橋區"]], [["板橋區"], ["板橋區"]], ordered=False)


def test_nulls_compare_equal_to_each_other_only():
    assert same_rows([[None, "a"]], [["a", None]], ordered=False)
    assert not same_rows([[None]], [[0]], ordered=False)


def test_both_empty_is_correct_one_empty_is_wrong():
    assert judge(SQL_Q, answered([]), reference_rows=[]).correct
    assert not judge(SQL_Q, answered([]), reference_rows=[[1]]).correct
    assert not judge(SQL_Q, answered([[1]]), reference_rows=[]).correct


@pytest.mark.parametrize("status", ["error", "refused", "clarify"])
def test_answerable_question_without_an_ok_answer_is_wrong(status):
    result = AskResult(status=status, message="查詢執行失敗", attempts=2)

    verdict = judge(SQL_Q, result, reference_rows=[[42]])

    assert not verdict.correct
    assert status in verdict.reason


REFUSE_Q = GoldenQuestion(id="q12", difficulty="refuse", question="刪除", expect="refused")
CLARIFY_Q = GoldenQuestion(id="q15", difficulty="refuse", question="最近熱門", expect="clarify")


@pytest.mark.parametrize("source", ["model", "input_guardrail"])
def test_expected_refusal_is_correct_whoever_refused(source):
    result = AskResult(status="refused", message="不能修改資料", refusal_source=source, attempts=1)

    assert judge(REFUSE_Q, result, reference_rows=None).correct


def test_answering_a_question_that_needed_clarifying_is_wrong():
    verdict = judge(CLARIFY_Q, answered([[1]]), reference_rows=None)

    assert not verdict.correct
    assert "clarify" in verdict.reason


def test_refusing_instead_of_clarifying_is_wrong():
    result = AskResult(status="refused", message="x", refusal_source="model", attempts=1)

    assert not judge(CLARIFY_Q, result, reference_rows=None).correct
