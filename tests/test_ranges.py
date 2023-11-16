from __future__ import annotations

import datetime
import re
from typing import Any

import pytest
from hypothesis import assume, given
from hypothesis.strategies import composite, integers, none, one_of, sampled_from

from xocto import ranges


@composite
def valid_integer_range(draw):
    boundaries = draw(sampled_from(ranges.RangeBoundaries))
    # Restrict the size of the intervals since that will always be enough to find logic issues
    if boundaries in [
        ranges.RangeBoundaries.INCLUSIVE_EXCLUSIVE,
        ranges.RangeBoundaries.INCLUSIVE_INCLUSIVE,
    ]:
        start = draw(integers(min_value=-5, max_value=5))
    else:
        start = draw(one_of(none(), integers(min_value=-5, max_value=5)))

    if start is None:
        min_end = -5
    elif boundaries == ranges.RangeBoundaries.INCLUSIVE_INCLUSIVE:
        min_end = start
    else:
        min_end = start + 1
    # Give the end a bit more space so we can create intervals if start = 5
    if boundaries in [
        ranges.RangeBoundaries.INCLUSIVE_INCLUSIVE,
        ranges.RangeBoundaries.EXCLUSIVE_INCLUSIVE,
    ]:
        end = draw(integers(min_end, 6))
    else:
        end = draw(one_of(none(), integers(min_end, 6)))

    return ranges.Range(start, end, boundaries=boundaries)


def test_creation():
    assert ranges.Range(
        0, 2, boundaries=ranges.RangeBoundaries.EXCLUSIVE_INCLUSIVE
    ) == ranges.Range(0, 2, boundaries="(]")


@pytest.mark.parametrize(
    "start,end,boundaries",
    [
        (1, 0, ranges.RangeBoundaries.INCLUSIVE_INCLUSIVE),
        (0, 0, ranges.RangeBoundaries.INCLUSIVE_EXCLUSIVE),
        (0, 0, ranges.RangeBoundaries.EXCLUSIVE_INCLUSIVE),
        (0, 0, ranges.RangeBoundaries.EXCLUSIVE_EXCLUSIVE),
        (None, 0, ranges.RangeBoundaries.INCLUSIVE_INCLUSIVE),
        (None, 0, ranges.RangeBoundaries.INCLUSIVE_EXCLUSIVE),
        (None, None, ranges.RangeBoundaries.INCLUSIVE_EXCLUSIVE),
        (0, None, ranges.RangeBoundaries.INCLUSIVE_INCLUSIVE),
        (0, None, ranges.RangeBoundaries.EXCLUSIVE_INCLUSIVE),
        (None, None, ranges.RangeBoundaries.EXCLUSIVE_INCLUSIVE),
    ],
)
def test_validation(start, end, boundaries):
    with pytest.raises(ValueError):
        ranges.Range(start, end, boundaries=boundaries)


@pytest.mark.parametrize(
    "lower,higher",
    [
        ("[0,2)", "[1,3)"),
        ("[0,4)", "[1,3)"),
        ("[0,2)", "[0,4)"),
        ("[0,2)", "[0,None)"),
        ("(None,5)", "[0,4)"),
        ("[0,2)", "[0,2]"),
        ("[0,2]", "(0,2)"),
        ("(0,2)", "(0,2]"),
    ],
)
def test_range_comparison(lower, higher):
    lower_range = _range_from_string(lower)
    higher_range = _range_from_string(higher)

    assert higher_range > lower_range
    assert not (higher_range < lower_range)
    assert higher_range >= lower_range
    assert lower_range < higher_range
    assert lower_range <= higher_range


@pytest.mark.parametrize(
    "start,end,boundaries,item,expected",
    [
        # Basic inclusion
        (0, 2, ranges.RangeBoundaries.INCLUSIVE_INCLUSIVE, 0, True),
        (0, 2, ranges.RangeBoundaries.INCLUSIVE_INCLUSIVE, 1, True),
        (0, 2, ranges.RangeBoundaries.INCLUSIVE_INCLUSIVE, 2, True),
        (0, 2, ranges.RangeBoundaries.INCLUSIVE_INCLUSIVE, 3, False),
        (0, 2, ranges.RangeBoundaries.INCLUSIVE_INCLUSIVE, -1, False),
        # Unset bounds <=> Infinity
        (None, 2, ranges.RangeBoundaries.EXCLUSIVE_INCLUSIVE, -1, True),
        (None, 2, ranges.RangeBoundaries.EXCLUSIVE_INCLUSIVE, 3, False),
        (0, None, ranges.RangeBoundaries.INCLUSIVE_EXCLUSIVE, -1, False),
        (0, None, ranges.RangeBoundaries.INCLUSIVE_EXCLUSIVE, 3, True),
        (None, None, ranges.RangeBoundaries.EXCLUSIVE_EXCLUSIVE, 3, True),
        (None, None, ranges.RangeBoundaries.EXCLUSIVE_EXCLUSIVE, -1, True),
        # Non-integer comparable types
        (
            datetime.date(2020, 1, 1),
            datetime.date(2020, 1, 3),
            ranges.RangeBoundaries.INCLUSIVE_INCLUSIVE,
            datetime.date(2020, 1, 2),
            True,
        ),
        (
            datetime.date(2020, 1, 1),
            datetime.date(2020, 1, 3),
            ranges.RangeBoundaries.INCLUSIVE_INCLUSIVE,
            datetime.date(2019, 1, 1),
            False,
        ),
        # Different boundariess
        (0, 2, ranges.RangeBoundaries.EXCLUSIVE_EXCLUSIVE, 0, False),
        (0, 2, ranges.RangeBoundaries.EXCLUSIVE_EXCLUSIVE, 2, False),
        (0, 2, ranges.RangeBoundaries.EXCLUSIVE_INCLUSIVE, 0, False),
        (0, 2, ranges.RangeBoundaries.EXCLUSIVE_INCLUSIVE, 2, True),
        (0, 2, ranges.RangeBoundaries.INCLUSIVE_EXCLUSIVE, 0, True),
        (0, 2, ranges.RangeBoundaries.INCLUSIVE_EXCLUSIVE, 2, False),
    ],
)
def test_contains(start, end, boundaries, item, expected):
    result = item in ranges.Range(start, end, boundaries=boundaries)
    assert result == expected


def test_default_boundaries():
    subject = ranges.Range(0, 2)

    result = subject.boundaries

    assert result == ranges.RangeBoundaries.INCLUSIVE_EXCLUSIVE


@given(valid_integer_range(), valid_integer_range())
def test_range_is_disjoint(a: ranges.Range[Any], b: ranges.Range[Any]) -> None:
    assert a.intersection(b) is not None or a.is_disjoint(b)


@pytest.mark.parametrize(
    "a_str,b_str,expected_str",
    [
        # Finite intersections
        ("[0,2)", "[1,3)", "[1,2)"),
        ("[0,2]", "[1,3)", "[1,2]"),
        # Interactions with unbounded ranges
        ("[0,None)", "[1,3)", "[1,3)"),
        ("[0,None)", "[2,None)", "[2,None)"),
        ("[0,3)", "[2,None)", "[2,3)"),
        ("(None,3)", "[0,4)", "[0,3)"),
        ("(None,3)", "[0,None)", "[0,3)"),
        # Disjoint ranges
        ("[0,2)", "[2,4)", None),
        ("[0,2)", "[3,4)", None),
        ("(None,2)", "[2,None)", None),
        ("(None,2)", "[3,None)", None),
        # Other range types
        ("(0,2)", "(1,3)", "(1,2)"),
        ("(0,2)", "(2,4)", None),
        ("(0,2]", "(1,3]", "(1,2]"),
        ("(0,2]", "(2,4]", None),
        ("[0,2]", "[1,3]", "[1,2]"),
        ("[0,2]", "[2,4]", "[2,2]"),
        # Mixed range types
        ("(0,2)", "[1,3)", "[1,2)"),
        ("(0,2)", "[-1,1)", "(0,1)"),
        ("(0,3)", "[1,2)", "[1,2)"),
        ("(0,2)", "[2,3)", None),
        ("[0,2]", "(0,2)", "(0,2)"),
        ("(0,2]", "[2,4)", "[2,2]"),
    ],
)
def test_intersection(a_str, b_str, expected_str):
    a = _range_from_string(a_str)
    b = _range_from_string(b_str)
    if expected_str is not None:
        expected = _range_from_string(expected_str)
    else:
        expected = None

    result = a & b

    assert result == expected


@pytest.mark.parametrize(
    "a_str,b_str,expected_str",
    [
        # Finite intersections
        ("[0,2)", "[1,3)", "[0,3)"),
        ("[1,3)", "[0,2)", "[0,3)"),
        # Interactions with unbounded ranges
        ("[1,None)", "[0,3)", "[0,None)"),
        ("[0,None)", "[2,None)", "[0,None)"),
        ("(None,3)", "[0,4)", "(None,4)"),
        ("(None,3)", "[0,None)", "(None,None)"),
        # Adjacent ranges
        ("[0,2)", "[2,4)", "[0,4)"),
        ("[0,2]", "(2,4)", "[0,4)"),
        # Disjoint ranges
        ("[0,2)", "[3,4)", None),
        ("(None,2)", "[3,None)", None),
        # Other range types
        ("(0,2)", "(1,3)", "(0,3)"),
        ("(0,2)", "(2,4)", None),
        ("(0,2]", "(1,3]", "(0,3]"),
        ("(0,2]", "(2,4]", "(0,4]"),
        ("[0,2]", "[1,3]", "[0,3]"),
        ("[0,2]", "[2,4]", "[0,4]"),
        # Mixed range types
        ("(0,2)", "[0,2)", "[0,2)"),
        ("(0,2)", "[2,3)", "(0,3)"),
        ("[0,2]", "(0,2)", "[0,2]"),
        ("[0,2]", "(0,3)", "[0,3)"),
        ("(0,2]", "[2,4)", "(0,4)"),
    ],
)
def test_range_union(a_str, b_str, expected_str):
    a = _range_from_string(a_str)
    b = _range_from_string(b_str)
    if expected_str is not None:
        expected = _range_from_string(expected_str)
    else:
        expected = None

    result = a | b

    assert result == expected


@given(valid_integer_range(), valid_integer_range())
def test_union_and_intersection_are_commutative(
    a: ranges.Range[Any], b: ranges.Range[Any]
) -> None:
    assert a | b == b | a
    assert a & b == b & a


@given(valid_integer_range(), valid_integer_range())
def test_union_and_intersection_are_idempotent(
    a: ranges.Range[Any], b: ranges.Range[Any]
) -> None:
    union = a | b
    assume(union is not None)
    assert union is not None
    assert union & a == a
    assert union & b == b


@given(valid_integer_range(), valid_integer_range())
def test_range_difference_and_intersection_form_partition(
    a: ranges.Range[Any], b: ranges.Range[Any]
) -> None:
    a_difference = a - b
    b_difference = b - a
    intersection = a & b

    assume(a_difference is not None or b_difference is not None)

    if intersection is None:
        assert a_difference == a
        assert b_difference == b
    else:
        if a_difference is not None:
            if isinstance(a_difference, ranges.RangeSet):
                # a contains b
                assert b_difference is None
                assert a_difference.is_disjoint(ranges.RangeSet([intersection]))
                assert a_difference | ranges.RangeSet(
                    [intersection]
                ) == ranges.RangeSet([a])
            else:
                assert a_difference.is_disjoint(intersection)
                assert a_difference | intersection == a

        if b_difference is not None:
            if isinstance(b_difference, ranges.RangeSet):
                # b contains a
                assert a_difference is None
                assert b_difference.is_disjoint(ranges.RangeSet([intersection]))
                assert b_difference | ranges.RangeSet(
                    [intersection]
                ) == ranges.RangeSet([b])
            else:
                assert b_difference.is_disjoint(intersection)
                assert b_difference | intersection == b

        if a_difference is not None and b_difference is not None:
            # Neither interval contains the other
            assert isinstance(a_difference, ranges.Range) and isinstance(
                b_difference, ranges.Range
            )
            assert a_difference & b_difference is None
            assert a_difference.is_disjoint(b_difference)
            assert b_difference.is_disjoint(a_difference)
            # Ignore types here as structuring this to appease mypy would make it v ugly.
            assert (a_difference | intersection | b_difference) == (a | b)  # type: ignore[operator]


def _range_from_string(range_str: str) -> ranges.Range[int]:
    """
    Convenience method to make test declarations clearer.

    Examples:
    [1,2] => ranges.Range(1, 2, boundaries=ranges.RangeBoundaries.INCLUSIVE_INCLUSIVE)
    """
    left_bracket = range_str[0]
    right_bracket = range_str[-1]
    start_str, end_str = range_str[1:-1].split(",")

    boundaries = {
        ("[", "]"): ranges.RangeBoundaries.INCLUSIVE_INCLUSIVE,
        ("[", ")"): ranges.RangeBoundaries.INCLUSIVE_EXCLUSIVE,
        ("(", "]"): ranges.RangeBoundaries.EXCLUSIVE_INCLUSIVE,
        ("(", ")"): ranges.RangeBoundaries.EXCLUSIVE_EXCLUSIVE,
    }[left_bracket, right_bracket]

    if start_str == "None":
        start = None
    else:
        start = int(start_str)

    if end_str == "None":
        end = None
    else:
        end = int(end_str)

    return ranges.Range(start, end, boundaries=boundaries)


def _rangeset_from_string(rangeset_str: str) -> ranges.RangeSet[int]:
    """
    Convenience method to make test declarations clearer.

    Examples:
    {} => ranges.RangeSet()
    {[1,2]} => ranges.RangeSet(
        ranges.Range(1, 2, boundaries=ranges.RangeBoundaries.INCLUSIVE_INCLUSIVE)
    )
    {[1,2], (3,None)} => ranges.RangeSet(
        ranges.Range(1, 2, boundaries=ranges.RangeBoundaries.INCLUSIVE_INCLUSIVE),
        ranges.Range(3, None, boundaries=ranges.RangeBoundaries.EXCLUSIVE_EXCLUSIVE)
    )
    """
    range_strs = re.findall(r"[\[\(][^\]\)]*[^\[\(][\]\)]", rangeset_str[1:-1])
    return ranges.RangeSet([_range_from_string(range_str) for range_str in range_strs])


def test_finite_range():
    subject = ranges.FiniteRange(1, 4)

    assert 3 in subject


@pytest.mark.parametrize(
    "rangeset,expected_string",
    [
        # Empty RangeSets
        (ranges.RangeSet(), "{}"),
        (ranges.RangeSet([]), "{}"),
        # Single item sets
        (ranges.RangeSet([ranges.Range(0, 2)]), "{[0,2)}"),
        (ranges.RangeSet([ranges.Range(0, 3, boundaries="()")]), "{(0,3)}"),
        (ranges.RangeSet([ranges.Range(0, None)]), "{[0,None)}"),
        (
            ranges.RangeSet(
                [
                    ranges.Range(
                        datetime.date(2020, 1, 1),
                        datetime.date(2020, 1, 3),
                    )
                ]
            ),
            "{[2020-01-01,2020-01-03)}",
        ),
        # Multiple disjoint items
        (ranges.RangeSet([ranges.Range(0, 2), ranges.Range(3, 5)]), "{[0,2), [3,5)}"),
        (ranges.RangeSet([ranges.Range(3, 5), ranges.Range(0, 2)]), "{[0,2), [3,5)}"),
        # Overlapping items
        (ranges.RangeSet([ranges.Range(0, 2), ranges.Range(1, 3)]), "{[0,3)}"),
        (ranges.RangeSet([ranges.Range(1, 3), ranges.Range(0, 2)]), "{[0,3)}"),
    ],
)
def test_rangeset_construction(
    rangeset: ranges.RangeSet[Any], expected_string: str
) -> None:
    assert str(rangeset) == expected_string


@given(valid_integer_range(), valid_integer_range())
def test_rangeset_addition(a: ranges.Range[Any], b: ranges.Range[Any]) -> None:
    a_set = ranges.RangeSet([a])
    b_set = ranges.RangeSet([b])

    a_set.add(b)
    b_set.add(a)

    assert a_set == b_set == ranges.RangeSet([a, b])


@pytest.mark.parametrize(
    "rangeset,item,expected_result",
    [
        # Exact match
        (ranges.RangeSet([ranges.Range(0, 5)]), ranges.Range(0, 5), True),
        # Contained match
        (ranges.RangeSet([ranges.Range(0, 5)]), ranges.Range(1, 3), True),
        # Partial match
        (ranges.RangeSet([ranges.Range(0, 5)]), ranges.Range(1, 6), False),
        # Partial match
        (
            ranges.RangeSet([ranges.Range(0, 2), ranges.Range(3, 7)]),
            ranges.Range(1, 6),
            False,
        ),
    ],
)
def test_rangeset_contains_range(rangeset, item, expected_result):
    assert (item in rangeset) == expected_result


@pytest.mark.parametrize(
    "item,expected_result",
    [
        (-1, False),
        (0, True),
        (1, True),
        (2, True),
        (3, False),
        (4, True),
        (5, False),
    ],
)
def test_rangeset_contains_comparable_item(item, expected_result):
    rangeset = _rangeset_from_string("{[0,2], [4,5)}")
    assert (item in rangeset) == expected_result


@pytest.mark.parametrize(
    "rangeset_str, expected_result_str",
    [
        # Gaps
        ("{[0,1), [2,3), [4,None)}", "{(None,0), [1,2), [3,4)}"),
        # Alternative boundaries
        ("{[0,1], [2,3]}", "{(None,0), (1,2), (3,None)}"),
        ("{(0,1), (2,3)}", "{(None,0], [1,2], [3,None)}"),
        # No gaps
        ("{}", "{(None,None)}"),
        ("{[0,1)}", "{(None,0), [1,None)}"),
        ("{[0,None), [2,3), [4,5)}", "{(None,0)}"),
        ("{[0,1), [2,3), (None,5]}", "{(5,None)}"),
    ],
)
def test_rangeset_complement(rangeset_str, expected_result_str):
    rangeset = _rangeset_from_string(rangeset_str)
    assert str(-rangeset) == expected_result_str


@pytest.mark.parametrize(
    "rangeset_str, other_rangeset_str, expected_result_str",
    [
        # Single range rangesets, no contained difference
        ("{[0,100)}", "{[0,200)}", "{}"),
        # Multi range rangeset, some contained differences
        ("{[0,100)}", "{[0,10), [50,60)}", "{[10,50), [60,100)}"),
        # Multi range rangeset, no differences
        ("{[0,10), [50,60)}", "{[0,100)}", "{}"),
        # Multi range rangeset, entirely different
        ("{[20,30), [50,60)}", "{[0,10), [40,50)}", "{[20,30), [50,60)}"),
        # Multi range rangeset, unbounded
        ("{[20,30), [50,None)}", "{[0,10), [50,60)}", "{[20,30), [60,None)}"),
        # Multi range rangeset, numerous leading ranges
        (
            "{(None,5], [10,15), [20,30), [50,None)}",
            "{[25,40), [50,60)}",
            "{(None,5], [10,15), [20,25), [60,None)}",
        ),
        # Alternate boundaries
        ("{[0,100]}", "{(0,100)}", "{[0,0], [100,100]}"),  # INC_INC, EXC_EXC
        ("{(0,100)}", "{(0,100)}", "{}"),  # EXC_EXC, EXC_EXC
        ("{(0,100)}", "{[0,100]}", "{}"),  # EXC_EXC, INC_INC
        ("{[0,100]}", "{[0,100]}", "{}"),  # INC_INC, INC_INC
        ("{[0,100)}", "{[0,100]}", "{}"),  # INC_EXC, INC_INC
        ("{[0,100]}", "{[0,100)}", "{[100,100]}"),  # INC_INC, INC_EXC
        ("{[0,100]}", "{(0,100]}", "{[0,0]}"),  # INC_INC, EXC_INC
        ("{(0,100]}", "{[0,100)}", "{[100,100]}"),  # EXC_INC, INC_EXC
        ("{[0,100)}", "{(0,100]}", "{[0,0]}"),  # INC_EXC, EXC_INC
        ("{[0,100)}", "{[0,100)}", "{}"),  # INC_EXC, INC_EXC
        ("{[0,101)}", "{[0,100]}", "{(100,101)}"),  # INC_EXC + 1, INC_INC
        ("{[0,101]}", "{[0,100]}", "{(100,101]}"),  # INC_INC + 1, INC_INC
        ("{[0,1], [2,5], [7,9]}", "{[0,1), (3,7), [9,10]}", "{[1,1], [2,3], [7,9)}"),
    ],
)
def test_rangeset_difference(rangeset_str, other_rangeset_str, expected_result_str):
    rangeset = _rangeset_from_string(rangeset_str)
    other_rangeset = _rangeset_from_string(other_rangeset_str)
    assert str(rangeset - other_rangeset) == expected_result_str


ONE_DAY = datetime.timedelta(days=1)


class TestBreakPeriodsOnTimestamp:
    @pytest.fixture
    def period(self):
        return ranges.FiniteDatetimeRange(
            datetime.datetime(2021, 1, 1),
            datetime.datetime(2021, 2, 1),
        )

    def test_no_timestamps_returns_period(self, period):
        assert ranges.get_finite_datetime_ranges_from_timestamps(period, []) == [period]

    def test_timestamps_outside_period_ignored(self, period):
        assert ranges.get_finite_datetime_ranges_from_timestamps(
            period,
            [
                period.start - ONE_DAY,
                period.end + ONE_DAY,
            ],
        ) == [period]

    def test_timestamps_at_ends_ignored(self, period):
        assert ranges.get_finite_datetime_ranges_from_timestamps(
            period,
            [
                period.start,
                period.end,
            ],
        ) == [period]

    def test_timestamps_inside_period_cause_period_to_split(self, period):
        splits = [
            period.start + ONE_DAY,
            period.end - ONE_DAY,
        ]
        assert ranges.get_finite_datetime_ranges_from_timestamps(period, splits) == [
            ranges.FiniteDatetimeRange(period.start, splits[0]),
            ranges.FiniteDatetimeRange(splits[0], splits[1]),
            ranges.FiniteDatetimeRange(splits[1], period.end),
        ]

    def test_timestamps_deduplicated(self, period):
        splits = [
            period.start + ONE_DAY,
            period.start + ONE_DAY,
            period.end - ONE_DAY,
            period.end - ONE_DAY,
        ]
        assert ranges.get_finite_datetime_ranges_from_timestamps(period, splits) == [
            ranges.FiniteDatetimeRange(period.start, splits[0]),
            ranges.FiniteDatetimeRange(splits[0], splits[2]),
            ranges.FiniteDatetimeRange(splits[2], period.end),
        ]

    def test_timestamps_sorted(self, period):
        splits = [
            period.end - ONE_DAY,
            period.start + ONE_DAY,
        ]
        assert ranges.get_finite_datetime_ranges_from_timestamps(period, splits) == [
            ranges.FiniteDatetimeRange(period.start, splits[1]),
            ranges.FiniteDatetimeRange(splits[1], splits[0]),
            ranges.FiniteDatetimeRange(splits[0], period.end),
        ]


class TestAnyOverlapping:
    @pytest.mark.parametrize(
        "ranges_",
        [
            [
                ranges.Range(0, 2),
                ranges.Range(1, 3),
            ],
            [
                ranges.Range(
                    0, 2, boundaries=ranges.RangeBoundaries.INCLUSIVE_INCLUSIVE
                ),
                ranges.Range(2, 4),
            ],
        ],
    )
    def test_returns_true_if_and_ranges_overlap(self, ranges_):
        assert ranges.any_overlapping(ranges_)

    @pytest.mark.parametrize(
        "ranges_",
        [
            [
                ranges.Range(0, 2),
                ranges.Range(2, 4),
            ],
            [
                ranges.Range(0, 2),
                ranges.Range(
                    2, 4, boundaries=ranges.RangeBoundaries.EXCLUSIVE_INCLUSIVE
                ),
            ],
        ],
    )
    def test_returns_false_if_no_ranges_overlap(self, ranges_):
        assert not ranges.any_overlapping(ranges_)

    def test_returns_false_for_empty_set_of_ranges(self):
        assert not ranges.any_overlapping([])


class TestFiniteDateRange:
    """
    Test class for methods specific to the the FiniteDateRange subclass.
    """

    def test_days_property_has_correct_value(self):
        """
        As FiniteDateRange boundaries are double inclusive, the days
        property should include the start and end dates in the count.
        """
        range = ranges.FiniteDateRange(
            start=datetime.date(2000, 1, 1),
            end=datetime.date(2000, 1, 2),
        )
        assert range.days == 2

    class TestIntersection:
        def test_overlapping_ranges_will_intersect(self):
            ranges_ = [
                ranges.FiniteDateRange(
                    start=datetime.date(2000, 1, 1),
                    end=datetime.date(2000, 1, 3),
                ),
                ranges.FiniteDateRange(
                    start=datetime.date(2000, 1, 3),
                    end=datetime.date(2000, 1, 5),
                ),
            ]
            assert ranges_[0] & ranges_[1] == ranges.FiniteDateRange(
                start=datetime.date(2000, 1, 3),
                end=datetime.date(2000, 1, 3),
            )

        def test_adjacent_ranges_wont_intersect(self):
            ranges_ = [
                ranges.FiniteDateRange(
                    start=datetime.date(2000, 1, 1),
                    end=datetime.date(2000, 1, 2),
                ),
                ranges.FiniteDateRange(
                    start=datetime.date(2000, 1, 3),
                    end=datetime.date(2000, 1, 4),
                ),
            ]
            assert ranges_[0] & ranges_[1] is None

    class TestIsDisjoint:
        @pytest.mark.parametrize(
            "other",
            [
                ranges.Range(
                    start=datetime.date(2000, 1, 1),
                    end=datetime.date(2000, 1, 2),
                    boundaries=ranges.RangeBoundaries.EXCLUSIVE_INCLUSIVE,
                ),
                ranges.Range(
                    start=datetime.date(2000, 1, 5),
                    end=datetime.date(2000, 1, 6),
                    boundaries=ranges.RangeBoundaries.INCLUSIVE_EXCLUSIVE,
                ),
            ],
        )
        def test_identifies_ranges_that_are_not_disjoint(self, other):
            range = ranges.FiniteDateRange(
                start=datetime.date(2000, 1, 3),
                end=datetime.date(2000, 1, 4),
            )
            assert range.is_disjoint(other) is False

        def test_handles_edge_of_time(self):
            # This test is fairly coupled to knowledge of the is_disjoint implementation here.
            range = ranges.FiniteDateRange(
                start=datetime.date.min,
                end=datetime.date.max,
            )
            # We're not particularly interested in this assertion, we just want to be sure this
            # doesn't error.
            assert range.is_disjoint(range) is False

        @pytest.mark.parametrize(
            "other",
            [
                ranges.Range(
                    start=datetime.date(2000, 1, 1),
                    end=datetime.date(2000, 1, 2),
                    boundaries=ranges.RangeBoundaries.INCLUSIVE_EXCLUSIVE,
                ),
                ranges.Range(
                    start=datetime.date(2000, 1, 5),
                    end=datetime.date(2000, 1, 6),
                    boundaries=ranges.RangeBoundaries.EXCLUSIVE_INCLUSIVE,
                ),
            ],
        )
        def test_identifies_ranges_that_are_disjoint(self, other):
            range = ranges.FiniteDateRange(
                start=datetime.date(2000, 1, 3),
                end=datetime.date(2000, 1, 4),
            )
            assert range.is_disjoint(other) is True

    class TestUnion:
        @pytest.mark.parametrize(
            "range, other",
            [
                (
                    ranges.FiniteDateRange(
                        start=datetime.date(2000, 1, 1),
                        end=datetime.date(2000, 1, 2),
                    ),
                    ranges.FiniteDateRange(
                        start=datetime.date(2000, 1, 3),
                        end=datetime.date(2000, 1, 4),
                    ),
                ),
                (
                    ranges.FiniteDateRange(
                        start=datetime.date(2000, 1, 3),
                        end=datetime.date(2000, 1, 4),
                    ),
                    ranges.FiniteDateRange(
                        start=datetime.date(2000, 1, 1),
                        end=datetime.date(2000, 1, 2),
                    ),
                ),
            ],
        )
        def test_handles_adjacent_ranges(self, range, other):
            """
            As FiniteDateRange boundaries are double inclusive, when two ranges
            end/start on consecutive days they effectively cover a fully contiguous
            period of time and should make a union.
            """
            union = range | other
            assert union == ranges.FiniteDateRange(
                start=datetime.date(2000, 1, 1),
                end=datetime.date(2000, 1, 4),
            )

        def test_handles_many_adjacent_ranges(self):
            """
            As FiniteDateRange boundaries are double inclusive, when two ranges
            end/start on consecutive days they effectively cover a fully contiguous
            period of time and should make a union.

            This should apply with an arbitrary number of adjacent ranges.
            """
            r1 = ranges.FiniteDateRange(
                start=datetime.date(2000, 1, 1),
                end=datetime.date(2000, 1, 2),
            )
            r2 = ranges.FiniteDateRange(
                start=datetime.date(2000, 1, 3),
                end=datetime.date(2000, 1, 5),
            )
            r3 = ranges.FiniteDateRange(
                start=datetime.date(2000, 1, 6),
                end=datetime.date(2000, 1, 8),
            )

            union = r1 | r2 | r3
            assert union == ranges.FiniteDateRange(
                start=datetime.date(2000, 1, 1),
                end=datetime.date(2000, 1, 8),
            )

        def test_range_set_over_many_adjacent_ranges(self):
            """
            Multiple unions should be approximately equivalent to a RangeSet
            """
            r1 = ranges.FiniteDateRange(
                start=datetime.date(2000, 1, 1),
                end=datetime.date(2000, 1, 2),
            )
            r2 = ranges.FiniteDateRange(
                start=datetime.date(2000, 1, 3),
                end=datetime.date(2000, 1, 5),
            )
            r3 = ranges.FiniteDateRange(
                start=datetime.date(2000, 1, 6),
                end=datetime.date(2000, 1, 8),
            )

            range_set = ranges.RangeSet([r1, r2, r3])
            assert (
                ranges.FiniteDateRange(
                    start=datetime.date(2000, 1, 1),
                    end=datetime.date(2000, 1, 8),
                )
                in range_set
            )

        @pytest.mark.parametrize(
            "range, other",
            [
                (
                    ranges.FiniteDateRange(
                        start=datetime.date(2000, 1, 1),
                        end=datetime.date(2000, 1, 2),
                    ),
                    ranges.FiniteDateRange(
                        start=datetime.date(2000, 1, 4),
                        end=datetime.date(2000, 1, 5),
                    ),
                ),
                (
                    ranges.FiniteDateRange(
                        start=datetime.date(2000, 1, 4),
                        end=datetime.date(2000, 1, 5),
                    ),
                    ranges.FiniteDateRange(
                        start=datetime.date(2000, 1, 1),
                        end=datetime.date(2000, 1, 2),
                    ),
                ),
            ],
        )
        def test_handles_disjoint_ranges(self, range, other):
            """
            Disjoint ranges (those with a full clear day between them) should not make
            a union.
            """
            union = range | other
            assert union is None

        @pytest.mark.parametrize(
            "other",
            [
                pytest.param(
                    # This is a complex case, because the behaviour of union orders
                    # the ranges first the union method is called on this param Range
                    # not the FiniteDateRange defined in the test body. The test case
                    # still has value though as it does confirm that we get the desired
                    # behaviour, even if it is not with the expected method being
                    # called.
                    ranges.Range(
                        start=datetime.date(2000, 1, 1),
                        end=datetime.date(2000, 1, 2),
                        boundaries=ranges.RangeBoundaries.INCLUSIVE_EXCLUSIVE,
                    ),
                    id="other_excludes_adjacent_end_boundary",
                ),
                pytest.param(
                    ranges.Range(
                        start=datetime.date(2000, 1, 5),
                        end=datetime.date(2000, 1, 6),
                        boundaries=ranges.RangeBoundaries.EXCLUSIVE_INCLUSIVE,
                    ),
                    id="other_excludes_adjacent_start_boundary",
                ),
            ],
        )
        def test_respects_other_range_boundaries(self, other):
            """
            Disjoint ranges (those with a full clear day between them) should not make
            a union.
            """
            range = ranges.FiniteDateRange(
                start=datetime.date(2000, 1, 3),
                end=datetime.date(2000, 1, 4),
            )
            union = range | other
            assert union is None

        def test_doesnt_extend_union(self):
            """
            A union of ranges should be longer than the sum of it's parts.
            """
            # This is a weird test to include, it is added because this feels like an
            # obvious risk with the implementation I have used.
            range = ranges.FiniteDateRange(
                start=datetime.date(2000, 1, 3),
                end=datetime.date(2000, 1, 4),
            )
            other = ranges.FiniteDateRange(
                start=datetime.date(2000, 1, 3),
                end=datetime.date(2000, 1, 4),
            )
            union = range | other
            assert union == range
