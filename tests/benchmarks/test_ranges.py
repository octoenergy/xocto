import datetime
import random
from decimal import Decimal as D

from xocto import ranges


def _shuffled(ranges_, *, seed=42):
    ranges_ = ranges_.copy()
    random.seed(seed)
    random.shuffle(ranges_)
    return ranges_


def test_any_overlapping(benchmark):
    ranges_ = _shuffled([ranges.Range(D(i), D(i + 1)) for i in range(1000)])
    any_overlapping = benchmark(ranges.any_overlapping, ranges_)
    assert any_overlapping is False


def test_any_gaps(benchmark):
    ranges_ = _shuffled([ranges.Range(D(i), D(i + 1)) for i in range(1000)])
    any_overlapping = benchmark(ranges.any_gaps, ranges_)
    assert any_overlapping is False


class TestFiniteDatetimeRange:
    def test_intersection_is_none(self, benchmark):
        r1 = ranges.FiniteDatetimeRange(
            datetime.datetime(2020, 1, 1),
            datetime.datetime(2020, 1, 2),
        )
        r2 = ranges.FiniteDatetimeRange(
            datetime.datetime(2020, 1, 3),
            datetime.datetime(2020, 1, 4),
        )

        result = benchmark(lambda: r2 & r1)

        assert result is None

    def test_intersection_is_not_none(self, benchmark):
        r1 = ranges.FiniteDatetimeRange(
            datetime.datetime(2020, 1, 1),
            datetime.datetime(2020, 1, 3),
        )
        r2 = ranges.FiniteDatetimeRange(
            datetime.datetime(2020, 1, 2),
            datetime.datetime(2020, 1, 4),
        )

        result = benchmark(lambda: r2 & r1)

        assert result == ranges.FiniteDatetimeRange(
            datetime.datetime(2020, 1, 2),
            datetime.datetime(2020, 1, 3),
        )

    def test_union_is_none(self, benchmark):
        r1 = ranges.FiniteDatetimeRange(
            datetime.datetime(2020, 1, 1),
            datetime.datetime(2020, 1, 2),
        )
        r2 = ranges.FiniteDatetimeRange(
            datetime.datetime(2020, 1, 3),
            datetime.datetime(2020, 1, 4),
        )

        result = benchmark(lambda: r2 | r1)

        assert result is None

    def test_union_is_not_none(self, benchmark):
        r1 = ranges.FiniteDatetimeRange(
            datetime.datetime(2020, 1, 1),
            datetime.datetime(2020, 1, 3),
        )
        r2 = ranges.FiniteDatetimeRange(
            datetime.datetime(2020, 1, 2),
            datetime.datetime(2020, 1, 4),
        )

        result = benchmark(lambda: r2 | r1)

        assert result == ranges.FiniteDatetimeRange(
            datetime.datetime(2020, 1, 1),
            datetime.datetime(2020, 1, 4),
        )
