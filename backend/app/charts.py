"""Pick how to show a result from its shape alone (design D3): no model call, same input same chart."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

# Only these fixed text shapes count as time (design D4), e.g. to_char(created_at, 'YYYY-MM').
TIME_TEXT_FORMATS = ("%Y-%m", "%Y-%m-%d")


@dataclass(frozen=True)
class Chart:
    type: Literal["line", "table"]
    x_key: str | None = None
    y_key: str | None = None


TABLE = Chart(type="table")


def choose_chart(columns: list[str], rows: list[list[Any]]) -> Chart:
    if len(columns) != 2 or not rows or any(len(row) != 2 for row in rows):
        return TABLE
    if not all(_is_time(x) for x, _ in rows):
        return TABLE
    # NULL values leave a gap in the line; a column with no number at all has nothing to draw.
    values = [y for _, y in rows if y is not None]
    if not values or not all(_is_number(y) for y in values):
        return TABLE
    return Chart(type="line", x_key=columns[0], y_key=columns[1])


def _is_time(value: Any) -> bool:
    # datetime is a subclass of date, so both pass here.
    if isinstance(value, date):
        return True
    if isinstance(value, str):
        return any(_parses(value, f) for f in TIME_TEXT_FORMATS)
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
