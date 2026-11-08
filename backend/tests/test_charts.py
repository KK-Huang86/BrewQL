"""The chart comes from the result's shape: two columns, time then number, is a line; anything else a table."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.charts import Chart, choose_chart

TABLE = Chart(type="table")


def test_date_and_number_is_a_line_over_those_columns():
    chart = choose_chart(["month", "searches"], [[date(2026, 5, 1), 120], [date(2026, 6, 1), 340]])

    assert chart == Chart(type="line", x_key="month", y_key="searches")


def test_timestamp_and_decimal_is_a_line():
    # date_trunc returns timestamptz; AVG/ROUND return Decimal.
    rows = [[datetime(2026, 5, 1, tzinfo=UTC), Decimal("4.25")], [datetime(2026, 6, 1, tzinfo=UTC), Decimal("4.5")]]

    assert choose_chart(["m", "avg"], rows).type == "line"


@pytest.mark.parametrize("x", [["2026-05", "2026-06"], ["2026-05-01", "2026-05-02"]])
def test_iso_month_or_day_text_is_a_line(x):
    # The model often writes to_char(created_at, 'YYYY-MM') (design D4).
    assert choose_chart(["month", "n"], [[x[0], 1], [x[1], 2]]).type == "line"


@pytest.mark.parametrize(
    "x",
    [
        ["大安區", "信義區"],  # categories are not time
        ["2026-13", "2026-12"],  # not a real month
        ["2026/05", "2026/06"],  # not the ISO shape
        ["2026-5", "2026-6"],  # ISO months are zero-padded
        ["2026-05-1", "2026-05-2"],  # and so are days
        ["2026-05", "大安區"],  # one bad value is enough
        [date(2026, 5, 1), None],  # a missing time cannot be placed on the axis
    ],
)
def test_first_column_that_is_not_all_time_is_a_table(x):
    assert choose_chart(["k", "n"], [[x[0], 1], [x[1], 2]]) == TABLE


def test_empty_result_is_a_table():
    assert choose_chart(["month", "n"], []) == TABLE


@pytest.mark.parametrize(
    ("columns", "row"),
    [(["n"], [3]), (["month", "city", "n"], [date(2026, 5, 1), "台北市", 3])],
)
def test_other_column_counts_are_a_table(columns, row):
    assert choose_chart(columns, [row]) == TABLE


def test_row_with_a_different_length_is_a_table():
    assert choose_chart(["month", "n"], [[date(2026, 5, 1), 3], [date(2026, 6, 1)]]) == TABLE


@pytest.mark.parametrize("y", [True, "3"])
def test_boolean_or_text_second_column_is_a_table(y):
    # bool is an int in Python, but true/false is not a quantity to plot.
    assert choose_chart(["day", "v"], [[date(2026, 1, 1), y]]) == TABLE


def test_some_null_values_are_skipped_and_still_a_line():
    assert choose_chart(["day", "n"], [[date(2026, 1, 1), 3], [date(2026, 1, 2), None]]).type == "line"


def test_all_null_values_are_a_table():
    assert choose_chart(["day", "n"], [[date(2026, 1, 1), None], [date(2026, 1, 2), None]]) == TABLE
