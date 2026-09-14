import datetime
import random
from decimal import Decimal as D
from typing import TypeVar

from pytest_benchmark.fixture import BenchmarkFixture as PytestBenchmarkFixture

from xocto import ranges


T = TypeVar("T")


def _shuffled(items: list[T], *, seed: int = 42) -> list[T]:
    items = items.copy()
    random.seed(seed)
    random.shuffle(items)
    return items


def benchmark_any_overlapping(benchmark: PytestBenchmarkFixture) -> None:
    ranges_ = _shuffled([ranges.Range(D(i), D(i + 1)) for i in range(1000)])
    any_overlapping = benchmark(ranges.any_overlapping, ranges_)
    assert any_overlapping is False


def benchmark_any_gaps(benchmark: PytestBenchmarkFixture) -> None:
    ranges_ = _shuffled([ranges.Range(D(i), D(i + 1)) for i in range(1000)])
    any_gaps = benchmark(ranges.any_gaps, ranges_)
    assert any_gaps is False


class BenchmarkFiniteDatetimeRange:
    def benchmark_intersection_is_none(self, benchmark: PytestBenchmarkFixture) -> None:
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

    def benchmark_intersection_is_not_none(
        self, benchmark: PytestBenchmarkFixture
    ) -> None:
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

    def benchmark_union_is_none(self, benchmark: PytestBenchmarkFixture) -> None:
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

    def benchmark_union_is_not_none(self, benchmark: PytestBenchmarkFixture) -> None:
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

    def benchmark_sorting(self, benchmark: PytestBenchmarkFixture) -> None:
        sorted_ranges_ = []
        dt = datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)
        for _ in range(100_000):
            sorted_ranges_.append(
                ranges.FiniteDatetimeRange(dt, dt + datetime.timedelta(hours=1))
            )
            dt += datetime.timedelta(hours=1)

        ranges_ = _shuffled(sorted_ranges_)

        result = benchmark(lambda: sorted(ranges_))
        assert result == sorted_ranges_
