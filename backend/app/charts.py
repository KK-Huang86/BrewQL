"""Pick how to show a result from its shape alone: no model call, same input same chart.

line (time + number) > bar (text + number, <= 30 rows) > number (one numeric cell) > table.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

# Only these fixed text shapes count as time (design D4), e.g. to_char(created_at, 'YYYY-MM').
# The regex enforces zero padding (strptime accepts "2026-5"); strptime rejects "2026-13".
TIME_TEXT_FORMATS = ((re.compile(r"\d{4}-\d{2}"), "%Y-%m"), (re.compile(r"\d{4}-\d{2}-\d{2}"), "%Y-%m-%d"))


@dataclass(frozen=True)
class Chart:
    type: Literal["line", "bar", "number", "table"]
    x_key: str | None = None
    y_key: str | None = None
    # Only the number card uses it: the column holding the single value.
    value_key: str | None = None


TABLE = Chart(type="table")

# More bars than this stop being readable (design D3).
MAX_BARS = 30


def choose_chart(columns: list[str], rows: list[list[Any]]) -> Chart:
    # Order matters: month text is also text, so the line check runs before the bar check.
    if len(columns) == 1 and len(rows) == 1 and len(rows[0]) == 1 and _is_number(rows[0][0]):
        return Chart(type="number", value_key=columns[0])
    if len(columns) != 2 or not rows or any(len(row) != 2 for row in rows):
        return TABLE
    # NULL values leave a gap (line) or an empty bar; a column with no number at all has nothing to draw.
    values = [y for _, y in rows if y is not None]
    if not values or not all(_is_number(y) for y in values):
        return TABLE
    if all(_is_time(x) for x, _ in rows):
        return Chart(type="line", x_key=columns[0], y_key=columns[1])
    if len(rows) <= MAX_BARS and all(isinstance(x, str) for x, _ in rows):
        return Chart(type="bar", x_key=columns[0], y_key=columns[1])
    return TABLE


def _is_time(value: Any) -> bool:
    # datetime is a subclass of date, so both pass here.
    if isinstance(value, date):
        return True
    if isinstance(value, str):
        return any(shape.fullmatch(value) and _parses(value, fmt) for shape, fmt in TIME_TEXT_FORMATS)
    return False


def _parses(text: str, fmt: str) -> bool:
    try:
        datetime.strptime(text, fmt)
    except ValueError:
        return False
    return True


def _is_number(value: Any) -> bool:
    # bool is an int subclass, but true/false is not a quantity to plot.
    return isinstance(value, int | float | Decimal) and not isinstance(value, bool)
