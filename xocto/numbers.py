import decimal
import random
from typing import TypeVar

from . import types


def quantise(number, base, rounding=decimal.ROUND_HALF_EVEN):
    """
    Round a number to an arbitrary integer base. For example:
    >>> quantise(256, 5)
    255

    Note that numbers equal to half of the rounding amount will always
    round down. So:
    >>> quantise(15, 30)
    0
    """
    assert base > 0
    rounded_result = base * (decimal.Decimal(number) / base).quantize(
        decimal.Decimal("1."), rounding=rounding
    )
    return int(rounded_result)


def truncate_decimal_places(value: decimal.Decimal, places: int = 1) -> float:
    """
    Truncate a float (i.e round towards zero) to a given number of decimal places.

    NB: Takes a decimal but returns a float!

    >>> truncate_decimal_places(12.364, 1)
    12.3

    >>> round_decimal_places(-12.364, 1)
    -12.3 # -12.3 is bigger than -12.4

    >>> round_decimal_places(12.364, 0)
    12.0 # rounding to 0 returns float with no decmial part
    """

    if places == 0:
        quantize_string = "1"
    else:
        quantize_string = "0." + ((places - 1) * "0") + "1"

    exponent = decimal.Decimal(quantize_string)
    decimal_result = value.quantize(exponent, rounding=decimal.ROUND_DOWN)
    return float(decimal_result)


def round_decimal_places(
    value: decimal.Decimal, places: int = 1, rounding=decimal.ROUND_HALF_UP
) -> decimal.Decimal:
    """
    Round a decimal to a given number of decimal places using a given rounding method.

    By default, we use half-up rounding so that parts from half way between the given rounding
    precision will be rounded up towards the greater number.

    This differs from the default rounding since Python 3.0 which is also used elsewhere in Kraken
    (which use "banker's"/half-even rounding, which is considered by IEEE 754 to be the recommended
    default for decimal).

    >>> round_decimal_places(12.35, 1)
    12.4

    >>> round_decimal_places(-12.35, 1)
    -12.3 #-12.3 is bigger than -12.4
    """

    if places == 0:
        quantize_string = "1"
    else:
        quantize_string = "0." + ((places - 1) * "0") + "1"

    return value.quantize(decimal.Decimal(quantize_string), rounding=rounding)


def round_to_integer(value: decimal.Decimal, rounding=decimal.ROUND_HALF_UP) -> int:
    """
    Round a decimal to the nearest integer, using a given rounding method.

    By default, we use half-up rounding.

    This differs from the default rounding since Python 3.0 which is also used elsewhere in Kraken
    (which use "banker's"/half-even rounding, which is considered by IEEE 754 to be the recommended
    default for decimal).
    """
    return int(round_decimal_places(value, places=0, rounding=rounding))


T = TypeVar("T")


def clip_to_range(
    val: types.Comparable[T], *, minval: types.Comparable[T], maxval: types.Comparable[T]
) -> types.Comparable[T]:
    """
    Clip the value to the min and max values given.

    Values to be compared must be of the same type.

    Example usage:
        >>> clip_to_range(10, minval=20, maxval=25)
        20
        >>> clip_to_range(date(2020, 1, 4), minval=date(2020, 1, 1), maxval=date(2020, 1, 3))
        date(2020, 1, 3)
        >>> clip_to_range(1.5, minval=1.0, maxval=2.0)
        1.5
    """
    assert not minval > maxval, "minval must not be greater than maxval"
    if val < minval:
        return minval
    elif val > maxval:
        return maxval
    else:
        return val


def remove_exponent(d: decimal.Decimal) -> decimal.Decimal:
    """
    Util function for removing the exponent and trailing zeroes of a decimal.

    From https://docs.python.org/3/library/decimal.html#decimal-faq
    """
    return d.quantize(decimal.Decimal(1)) if d == d.to_integral() else d.normalize()


def random_int(length: int) -> int:
    """
    Return a pseudo-random integer based on the provided `length`.

        >>> random_int(3)
        114
    """
    if length < 2:
        raise ValueError("length must be greater than or equal to 2")
    range_start = 10 ** (length - 1)
    range_end = (10**length) - 1
    return random.randint(range_start, range_end)
