"""Global daily question limit (limit-public-traffic design D3)."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.daily_limit import DailyQuestionLimit

TAIPEI = timezone(timedelta(hours=8))


class Clock:
    def __init__(self, at: datetime) -> None:
        self.at = at

    def __call__(self) -> datetime:
        return self.at


def test_allows_up_to_the_limit_then_refuses():
    limit = DailyQuestionLimit(3, now=Clock(datetime(2026, 11, 9, 12, tzinfo=TAIPEI)))

    assert [limit.try_acquire() for _ in range(5)] == [True, True, True, False, False]
    assert limit.count == 3


def test_resets_at_taipei_midnight():
    clock = Clock(datetime(2026, 11, 9, 23, 59, 59, tzinfo=TAIPEI))
    limit = DailyQuestionLimit(1, now=clock)
    assert limit.try_acquire()
    assert not limit.try_acquire()

    clock.at = datetime(2026, 11, 10, 0, 0, 0, tzinfo=TAIPEI)

    assert limit.try_acquire()
    assert limit.count == 1


def test_utc_midnight_is_not_a_new_day():
    # 00:00 UTC is 08:00 in Taipei: still the same Taipei day.
    clock = Clock(datetime(2026, 11, 9, 23, 0, tzinfo=UTC))  # 07:00 on the 10th in Taipei
    limit = DailyQuestionLimit(1, now=clock)
    assert limit.try_acquire()

    clock.at = datetime(2026, 11, 10, 1, 0, tzinfo=UTC)  # 09:00 on the 10th in Taipei

    assert not limit.try_acquire()


@pytest.mark.parametrize(
    ("at", "seconds"),
    [
        (datetime(2026, 11, 9, 23, 59, 30, tzinfo=TAIPEI), 30),
        (datetime(2026, 11, 9, 0, 0, 0, tzinfo=TAIPEI), 86_400),
        (datetime(2026, 11, 9, 12, 0, 0, 500_000, tzinfo=TAIPEI), 43_200),  # rounds up, never 0
        (datetime(2026, 11, 9, 16, 0, tzinfo=UTC), 86_400),  # exactly 00:00 on the 10th in Taipei
    ],
)
def test_retry_after_counts_seconds_to_the_next_taipei_midnight(at, seconds):
    assert DailyQuestionLimit(1, now=Clock(at)).retry_after_seconds() == seconds


@pytest.mark.parametrize("bad", [0, -1, True, 1.5, "500"])
def test_limit_must_be_a_positive_integer(bad):
    with pytest.raises(ValueError, match="DAILY_QUESTION_LIMIT"):
        DailyQuestionLimit(bad)


def test_default_clock_is_taipei_time():
    # No clock injected: the day boundary is still Taipei's, so a fresh limiter allows a question.
    assert DailyQuestionLimit(1).try_acquire()
