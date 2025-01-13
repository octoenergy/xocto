import random
from decimal import Decimal as D

import pytest

from xocto import ranges


def _shuffled(ranges_, *, seed=42):
    ranges_ = ranges_.copy()
    random.seed(seed)
    random.shuffle(ranges_)
    return ranges_


@pytest.mark.benchmark(group="ranges.any_overlapping")
def test_any_overlapping(benchmark):
    ranges_ = _shuffled([ranges.Range(D(i), D(i + 1)) for i in range(1000)])
    any_overlapping = benchmark(ranges.any_overlapping, ranges_)
    assert any_overlapping is False


@pytest.mark.benchmark(group="ranges.any_gaps")
def test_any_gaps(benchmark):
    ranges_ = _shuffled([ranges.Range(D(i), D(i + 1)) for i in range(1000)])
    any_overlapping = benchmark(ranges.any_gaps, ranges_)
    assert any_overlapping is False
