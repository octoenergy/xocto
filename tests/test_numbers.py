from decimal import ROUND_DOWN, ROUND_HALF_DOWN, ROUND_HALF_UP, ROUND_UP
from decimal import Decimal as D

import pytest
from hypothesis import assume, given, strategies

from xocto import numbers


@pytest.mark.parametrize(
    "number_to_round, base, rounding_strategy, expected_result",
    [
        # DEFAULT ROUNDING STRATEGY (round-half-even)
        (153, 5, None, 155),
        # 23 * 12,793 == 294,239, which is the closest multiple of 23 to our starting number.
        (294_242, 23, None, 294_239),
        (64, 1, None, 64),
        # Numbers halfway between the rounding boundary will always round down
        (15, 30, None, 0),
        # CUSTOM ROUNDING STRATEGIES
        (153, 5, ROUND_DOWN, 150),
        (D("152.5"), 5, ROUND_HALF_DOWN, 150),
        (D("152.5"), 5, ROUND_HALF_UP, 155),
        # Check that rounding doesn't round beyond a quantised value
        (155, 5, ROUND_DOWN, 155),
        (150, 5, ROUND_UP, 150),
    ],
)
def test_quantise(number_to_round, base, rounding_strategy, expected_result):
    args = (number_to_round, base)
    kwargs = dict(rounding=rounding_strategy) if rounding_strategy else {}
    assert numbers.quantise(*args, **kwargs) == expected_result


def test_truncate_decimal_places():
    assert numbers.truncate_decimal_places(D("123.45"), 1) == 123.4
    assert numbers.truncate_decimal_places(D("123.456"), 1) == 123.4
    assert numbers.truncate_decimal_places(D("123.4"), 2) == 123.40
    assert numbers.truncate_decimal_places(D("123.45"), 0) == 123.0


class TestClipToRange:
    @given(strategies.integers(), strategies.integers(), strategies.integers())
    def test_always_clips_ints_to_range(self, val, minval, maxval):
        assume(minval <= maxval)
        clipped_val = numbers.clip_to_range(val, minval=minval, maxval=maxval)
        assert minval <= clipped_val <= maxval

    @given(strategies.dates(), strategies.dates(), strategies.dates())
    def test_always_clips_dates_to_range(self, val, minval, maxval):
        assume(minval <= maxval)
        clipped_val = numbers.clip_to_range(val, minval=minval, maxval=maxval)
        assert minval <= clipped_val <= maxval

    @given(
        strategies.floats(allow_nan=False),
        strategies.floats(allow_nan=False),
        strategies.floats(allow_nan=False),
    )
    def test_always_clips_floats_to_range(self, val, minval, maxval):
        assume(minval <= maxval)
        clipped_val = numbers.clip_to_range(val, minval=minval, maxval=maxval)
        assert minval <= clipped_val <= maxval

    def test_raises_if_min_gt_max(self):
        with pytest.raises(AssertionError):
            numbers.clip_to_range(5, minval=8, maxval=4)


class TestRandomInt:
    @pytest.mark.parametrize("length", [2, 10, 20])
    def test_correct_length_returned(self, length):
        number = numbers.random_int(length=length)
        assert len(str(number)) == length

    @pytest.mark.parametrize("length", [-1, 0, 1])
    def test_too_small_length_raises_exception(self, length):
        with pytest.raises(ValueError):
            numbers.random_int(length=length)
