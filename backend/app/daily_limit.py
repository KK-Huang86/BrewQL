"""Global daily question limit: the last cost guard against many IPs asking at once.

nginx limits each IP; this caps the whole site per Taipei day before any paid call
(limit-public-traffic design D3). The count lives in memory: one process, one event loop,
and try_acquire has no await, so concurrent requests cannot both take the last slot.
A restart resets it, which needs an operator anyway.
"""

import math
from collections.abc import Callable
from datetime import date, datetime, timedelta

from app.llm import LOCAL_TZ


class DailyQuestionLimit:
    def __init__(self, limit: int, *, now: Callable[[], datetime] | None = None) -> None:
        # bool is an int subclass; True must not pass as a limit of 1.
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise ValueError(f"DAILY_QUESTION_LIMIT must be a positive integer, got {limit!r}")
        self.limit = limit
        self._now = now or (lambda: datetime.now(LOCAL_TZ))
        self._day: date | None = None
        self.count = 0

    def try_acquire(self) -> bool:
        """Count one question if today's limit allows it; False (and no count) once it is reached."""
        today = self._local_now().date()
        if today != self._day:
            self._day, self.count = today, 0
        if self.count >= self.limit:
            return False
        self.count += 1
        return True

    def used_today(self) -> int:
        """Questions counted today; 0 once the Taipei date has moved on, even before the next question."""
        return self.count if self._local_now().date() == self._day else 0

    def retry_after_seconds(self) -> int:
        """Whole seconds until the next Taipei midnight, rounded up so it is never 0."""
        now = self._local_now()
        midnight = datetime.combine(now.date() + timedelta(days=1), datetime.min.time(), tzinfo=LOCAL_TZ)
        return math.ceil((midnight - now).total_seconds())

    def _local_now(self) -> datetime:
        return self._now().astimezone(LOCAL_TZ)
