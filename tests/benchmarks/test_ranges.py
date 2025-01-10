import random
from decimal import Decimal as D

from xocto import ranges


def test_any_overlapping(benchmark):
    ranges_ = [ranges.Range(D(i), D(i + 1)) for i in range(1000)]
    random.seed(42)
    random.shuffle(ranges_)

    any_overlapping = benchmark(ranges.any_overlapping, ranges_)
    assert any_overlapping is False
