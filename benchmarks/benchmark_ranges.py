import datetime
import random
from decimal import Decimal as D

from xocto import ranges


def _shuffled(ranges_, *, seed=42):
    ranges_ = ranges_.copy()
    random.seed(seed)
    random.shuffle(ranges_)
    return ranges_


def benchmark_any_overlapping(benchmark):
    ranges_ = _shuffled([ranges.Range(D(i), D(i + 1)) for i in range(1000)])
    any_overlapping = benchmark(ranges.any_overlapping, ranges_)
    assert any_overlapping is False


def benchmark_any_gaps(benchmark):
    ranges_ = _shuffled([ranges.Range(D(i), D(i + 1)) for i in range(1000)])
    any_gaps = benchmark(ranges.any_gaps, ranges_)
    assert any_gaps is False


class BenchmarkFiniteDatetimeRange:
    def benchmark_intersection_is_none(self, benchmark):
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

    def benchmark_intersection_is_not_none(self, benchmark):
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

    def benchmark_union_is_none(self, benchmark):
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

    def benchmark_union_is_not_none(self, benchmark):
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

    def benchmark_sorting(self, benchmark):
        sorted_ranges_ = []
        dt = datetime.datetime(2020, 1, 1)
        for _ in range(100_000):
            sorted_ranges_.append(
                ranges.FiniteDatetimeRange(dt, dt + datetime.timedelta(hours=1))
            )
            dt += datetime.timedelta(hours=1)

        ranges_ = _shuffled(sorted_ranges_)

        result = benchmark(lambda: sorted(ranges_))
        assert result == sorted_ranges_
