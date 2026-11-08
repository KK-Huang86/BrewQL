"""The chart comes from the result's shape: time + number is a line, text + number a bar,
a single number a card; anything else a table (design D3)."""

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
def test_first_column_that_is_not_all_time_is_not_a_line(x):
    # Ticket 7: text categories became bars, so these are "not a line" rather than "a table".
    assert choose_chart(["k", "n"], [[x[0], 1], [x[1], 2]]).type != "line"


def test_empty_result_is_a_table():
    assert choose_chart(["month", "n"], []) == TABLE


@pytest.mark.parametrize(
    ("columns", "row"),
    # Ticket 7: a single numeric cell is now a number card (see below), so (["n"], [3]) left this list.
    [(["month", "city", "n"], [date(2026, 5, 1), "台北市", 3]), (["a", "b"], [[1], [2]])],
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


# Bar chart: two columns, text categories, numeric values, at most 30 rows.


def test_district_and_count_is_a_bar_over_those_columns():
    chart = choose_chart(["district", "n"], [["內湖區", 30], ["大安區", 20]])

    assert chart == Chart(type="bar", x_key="district", y_key="n")


def test_exactly_30_categories_is_a_bar_and_31_is_a_table():
    rows = [[f"區{i}", i] for i in range(31)]

    assert choose_chart(["k", "n"], rows[:30]).type == "bar"
    assert choose_chart(["k", "n"], rows) == TABLE


def test_month_text_is_still_a_line_not_a_bar():
    # Month text is also text; the line check comes first (design D3).
    assert choose_chart(["month", "n"], [["2026-05", 1], ["2026-06", 2]]).type == "line"


def test_decimal_values_and_some_nulls_still_make_a_bar():
    rows = [["內湖區", Decimal("0.54")], ["大安區", None], ["中山區", Decimal("0.1")]]

    assert choose_chart(["district", "rate"], rows).type == "bar"


@pytest.mark.parametrize(
    "rows",
    [
        [["內湖區", 3], [None, 2]],  # a category with no name has no bar to label
        [["a", "x"]],  # text values
        [["a", True], ["b", False]],  # true/false is not a quantity
        [["a", None], ["b", None]],  # nothing to draw
        [[1, 3], [2, 4]],  # numeric first column is not a category
    ],
)
def test_bar_shapes_that_fall_back_to_a_table(rows):
    assert choose_chart(["k", "v"], rows) == TABLE


# Number card: one row, one numeric column.


@pytest.mark.parametrize("value", [42, 0, Decimal("4.25"), 3.5])
def test_single_number_is_a_number_card(value):
    assert choose_chart(["count"], [[value]]) == Chart(type="number", value_key="count")


@pytest.mark.parametrize("value", [None, True, "42"])
def test_single_cell_that_is_not_a_number_is_a_table(value):
    assert choose_chart(["v"], [[value]]) == TABLE


def test_single_column_with_no_rows_is_a_table():
    assert choose_chart(["count"], []) == TABLE
