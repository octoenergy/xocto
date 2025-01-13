from __future__ import annotations

import copy
import datetime
import re
import zoneinfo
from typing import Any

import pytest
from hypothesis import assume, given
from hypothesis.strategies import composite, integers, none, one_of, sampled_from

from xocto import localtime, ranges


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


class TestRange:
    def test_creation(self):
        assert ranges.Range(
            0, 2, boundaries=ranges.RangeBoundaries.EXCLUSIVE_INCLUSIVE
        ) == ranges.Range(0, 2, boundaries="(]")

    def test_is_immutable(self):
        r = ranges.Range(0, 2, boundaries=ranges.RangeBoundaries.EXCLUSIVE_INCLUSIVE)
        with pytest.raises(AttributeError, match="Can't set attributes"):
            r.start = 1

    def test_additional_attributes_cant_be_created(self):
        r = ranges.Range(0, 2, boundaries=ranges.RangeBoundaries.EXCLUSIVE_INCLUSIVE)
        with pytest.raises(
            AttributeError, match="'Range' object has no attribute 'something_else'"
        ):
            r.something_else = 1

    def test_does_not_have_instance_dictionary(self):
        r = ranges.Range(0, 2, boundaries=ranges.RangeBoundaries.EXCLUSIVE_INCLUSIVE)
        assert not hasattr(r, "__dict__")

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
    def test_validation(self, start, end, boundaries):
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
    def test_range_comparison(self, lower, higher):
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
    def test_contains(self, start, end, boundaries, item, expected):
        result = item in ranges.Range(start, end, boundaries=boundaries)
        assert result == expected

    def test_default_boundaries(self):
        subject = ranges.Range(0, 2)

        result = subject.boundaries

        assert result == ranges.RangeBoundaries.INCLUSIVE_EXCLUSIVE

    @given(valid_integer_range(), valid_integer_range())
    def test_range_is_disjoint(
        self, a: ranges.Range[Any], b: ranges.Range[Any]
    ) -> None:
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
    def test_intersection(self, a_str, b_str, expected_str):
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
    def test_range_union(self, a_str, b_str, expected_str):
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
        self, a: ranges.Range[Any], b: ranges.Range[Any]
    ) -> None:
        assert a | b == b | a
        assert a & b == b & a

    @given(valid_integer_range(), valid_integer_range())
    def test_union_and_intersection_are_idempotent(
        self, a: ranges.Range[Any], b: ranges.Range[Any]
    ) -> None:
        union = a | b
        assume(union is not None)
        assert union is not None
        assert union & a == a
        assert union & b == b

    @given(valid_integer_range(), valid_integer_range())
    def test_range_difference_and_intersection_form_partition(
        self, a: ranges.Range[Any], b: ranges.Range[Any]
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

    class TestCopy:
        def test_range_copy(self):
            r1 = ranges.Range(1, 2)
            r2 = copy.copy(r1)
            assert r1 == r2

        def test_range_deepcopy(self):
            r1 = ranges.Range(1, 2)
            r2 = copy.deepcopy(r1)
            assert r1 == r2

        @pytest.mark.parametrize(
            "obj",
            [
                ranges.Range(1, 2),
                ranges.FiniteDateRange(
                    datetime.date(2000, 1, 1), datetime.date(2000, 1, 2)
                ),
                ranges.FiniteDatetimeRange(
                    datetime.datetime(2000, 1, 1), datetime.datetime(2000, 1, 2)
                ),
                ranges.HalfFiniteRange(1, 2),
            ],
            ids=("range", "date_range", "datetime_range", "half_finite_range"),
        )
        def test_copies(self, obj):
            assert obj == copy.copy(obj) == copy.deepcopy(obj)


class TestRangeSet:
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
            (
                ranges.RangeSet([ranges.Range(0, 2), ranges.Range(3, 5)]),
                "{[0,2), [3,5)}",
            ),
            (
                ranges.RangeSet([ranges.Range(3, 5), ranges.Range(0, 2)]),
                "{[0,2), [3,5)}",
            ),
            # Overlapping items
            (ranges.RangeSet([ranges.Range(0, 2), ranges.Range(1, 3)]), "{[0,3)}"),
            (ranges.RangeSet([ranges.Range(1, 3), ranges.Range(0, 2)]), "{[0,3)}"),
        ],
    )
    def test_rangeset_construction(
        self, rangeset: ranges.RangeSet[Any], expected_string: str
    ) -> None:
        assert str(rangeset) == expected_string

    @given(valid_integer_range(), valid_integer_range())
    def test_rangeset_addition(
        self, a: ranges.Range[Any], b: ranges.Range[Any]
    ) -> None:
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
    def test_rangeset_contains_range(self, rangeset, item, expected_result):
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
    def test_rangeset_contains_comparable_item(self, item, expected_result):
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
    def test_rangeset_complement(self, rangeset_str, expected_result_str):
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
            (
                "{[0,1], [2,5], [7,9]}",
                "{[0,1), (3,7), [9,10]}",
                "{[1,1], [2,3], [7,9)}",
            ),
        ],
    )
    def test_rangeset_difference(
        self, rangeset_str, other_rangeset_str, expected_result_str
    ):
        rangeset = _rangeset_from_string(rangeset_str)
        other_rangeset = _rangeset_from_string(other_rangeset_str)
        assert str(rangeset - other_rangeset) == expected_result_str


class TestHalfFiniteRange:
    def test_creation_uses_expected_defaults(self):
        r = ranges.HalfFiniteRange(0)
        assert 0 == r.start
        assert r.end is None
        assert ranges.RangeBoundaries.INCLUSIVE_EXCLUSIVE == r.boundaries

    def test_creation(self):
        r = ranges.HalfFiniteRange(1, 2)
        assert 1 == r.start
        assert 2 == r.end

    def test_does_not_have_instance_dictionary(self):
        r = ranges.HalfFiniteRange(0, 2)
        assert not hasattr(r, "__dict__")


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
    def test_does_not_modify_ranges(self):
        # The implementation of `any_overlapping` relies on sorting.
        # Let's make sure that the ranges passed in are unchanged.
        ranges_ = [
            ranges.Range(1, 2),
            ranges.Range(0, 1),
        ]
        ranges_copy = ranges_.copy()
        assert not ranges.any_overlapping(ranges_)
        assert ranges_ == ranges_copy

    @pytest.mark.parametrize(
        "ranges_",
        [
            [
                ranges.Range(0, 2),
                ranges.Range(1, 3),
            ],
            [
                ranges.Range(0, 2),
                ranges.Range(
                    4, 5
                ),  # Added this to ensure the overlapping ranges are not adjacent.
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
        assert ranges.any_overlapping(reversed(ranges_))

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
        assert not ranges.any_overlapping(reversed(ranges_))

    def test_returns_false_for_empty_set_of_ranges(self):
        assert not ranges.any_overlapping([])


class TestAnyGaps:
    def test_does_not_modify_ranges(self):
        # The implementation of `any_gaps` relies on sorting.
        # Let's make sure that the ranges passed in are unchanged.
        ranges_ = [
            ranges.Range(1, 2),
            ranges.Range(0, 1),
        ]
        ranges_copy = ranges_.copy()
        assert not ranges.any_gaps(ranges_)
        assert ranges_ == ranges_copy

    @pytest.mark.parametrize(
        "ranges_",
        [
            [
                ranges.Range(0, 1),
                ranges.Range(2, 3),
            ],
            [
                ranges.Range(
                    0, 1, boundaries=ranges.RangeBoundaries.INCLUSIVE_EXCLUSIVE
                ),
                ranges.Range(
                    1, 2, boundaries=ranges.RangeBoundaries.EXCLUSIVE_INCLUSIVE
                ),
            ],
            [
                ranges.Range(0, 2),
                ranges.Range(4, 6),
                ranges.Range(1, 3),
            ],
        ],
    )
    def test_returns_true_if_gaps(self, ranges_):
        assert ranges.any_gaps(ranges_)
        assert ranges.any_gaps(reversed(ranges_))

    @pytest.mark.parametrize(
        "ranges_",
        [
            [
                ranges.Range(0, 1),
                ranges.Range(1, 2),
            ],
            [
                ranges.Range(
                    0, 1, boundaries=ranges.RangeBoundaries.EXCLUSIVE_INCLUSIVE
                ),
                ranges.Range(
                    1, 2, boundaries=ranges.RangeBoundaries.EXCLUSIVE_INCLUSIVE
                ),
            ],
            [
                ranges.Range(0, 2),
                ranges.Range(1, 3),
            ],
            [
                ranges.Range(0, 3),
                ranges.Range(1, 2),
            ],
            [
                ranges.Range(0, 5),
                ranges.Range(1, 2),
                ranges.Range(3, 4),
            ],
            [
                ranges.Range(0, 2),
                ranges.Range(4, 6),
                ranges.Range(2, 4),
            ],
        ],
    )
    def test_returns_false_if_no_gaps(self, ranges_):
        assert not ranges.any_gaps(ranges_)
        assert not ranges.any_gaps(reversed(ranges_))

    def test_returns_false_for_empty_set_of_ranges(self):
        assert not ranges.any_gaps([])


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

    class TestIn:
        def test_finite_range(self):
            subject = ranges.FiniteRange(1, 4)

            assert 3 in subject


class TestFiniteDatetimeRange:
    class TestUnion:
        def test_union_of_touching_ranges(self):
            range = ranges.FiniteDatetimeRange(
                start=datetime.datetime(2000, 1, 1),
                end=datetime.datetime(2000, 1, 2),
            )
            other = ranges.FiniteDatetimeRange(
                start=datetime.datetime(2000, 1, 2),
                end=datetime.datetime(2000, 1, 3),
            )

            union = range | other

            assert union == ranges.FiniteDatetimeRange(
                start=datetime.datetime(2000, 1, 1),
                end=datetime.datetime(2000, 1, 3),
            )

        def test_union_of_disjoint_ranges(self):
            range = ranges.FiniteDateRange(
                start=datetime.datetime(2000, 1, 1),
                end=datetime.datetime(2000, 1, 2),
            )
            other = ranges.FiniteDatetimeRange(
                start=datetime.datetime(2020, 1, 1),
                end=datetime.datetime(2020, 1, 2),
            )

            assert range | other is None

        def test_union_of_overlapping_ranges(self):
            range = ranges.FiniteDatetimeRange(
                start=datetime.datetime(2000, 1, 1),
                end=datetime.datetime(2000, 1, 3),
            )
            other = ranges.FiniteDatetimeRange(
                start=datetime.datetime(2000, 1, 2),
                end=datetime.datetime(2000, 1, 4),
            )

            union = range | other

            assert union == ranges.FiniteDatetimeRange(
                start=datetime.datetime(2000, 1, 1),
                end=datetime.datetime(2000, 1, 4),
            )

    class TestLocalize:
        def test_converts_timezone(self):
            # Create a datetime range in Sydney, which is
            # 7 hours ahead of Dubai (target timezone).
            source_tz = zoneinfo.ZoneInfo("Australia/Sydney")  # GMT+11
            target_tz = zoneinfo.ZoneInfo("Asia/Dubai")  # GMT+4

            dt_range = ranges.FiniteDatetimeRange(
                datetime.datetime(2020, 1, 1, hour=7, tzinfo=source_tz),
                datetime.datetime(2020, 1, 10, hour=7, tzinfo=source_tz),
            )

            assert dt_range.localize(target_tz) == ranges.FiniteDatetimeRange(
                datetime.datetime(2020, 1, 1, tzinfo=target_tz),
                datetime.datetime(2020, 1, 10, tzinfo=target_tz),
            )

        def test_errors_converting_over_dst_gain_hour(self):
            utc_tz = zoneinfo.ZoneInfo("UTC")
            london_tz = zoneinfo.ZoneInfo("Europe/London")

            # Create a range in London over the hour that is "gained"
            # when Daylight Savings Time (DST) starts - at 1AM.
            #
            # Note: this is allowed by datetime but not a realistic
            # example - "1AM" here doesn't actually exist in GBR.
            dt_range = ranges.FiniteDatetimeRange(
                datetime.datetime(2020, 3, 29, hour=1, tzinfo=london_tz),
                datetime.datetime(2020, 3, 29, hour=2, tzinfo=london_tz),
            )

            # Converting to UTC should error due to the period being
            # empty: removing the "fake hour" means 2AM => 1AM.
            with pytest.raises(ValueError):
                assert dt_range.localize(utc_tz)

        def test_errors_converting_over_dst_loss_hour(self):
            utc_tz = zoneinfo.ZoneInfo("UTC")
            london_tz = zoneinfo.ZoneInfo("Europe/London")

            # Create a range in UTC over the hour before Daylight Savings
            # Time (DST) ends - at 2AM.
            dt_range = ranges.FiniteDatetimeRange(
                datetime.datetime(2020, 10, 25, hour=0, tzinfo=utc_tz),
                datetime.datetime(2020, 10, 25, hour=1, tzinfo=utc_tz),
            )

            # Converting to London timezone should error due to the period
            # being empty: both times map to 1AM.
            with pytest.raises(ValueError):
                assert dt_range.localize(london_tz)

        def test_errors_if_naive(self):
            tz = zoneinfo.ZoneInfo("Europe/London")

            with pytest.raises(ValueError) as exc_info:
                ranges.FiniteDatetimeRange(
                    datetime.datetime(2020, 1, 1),
                    datetime.datetime(2020, 1, 10),
                ).localize(tz)

            assert "naive" in str(exc_info.value)

    class TestAsDateRange:
        def test_returns_date_range(self):
            dt_range = ranges.FiniteDatetimeRange(
                datetime.datetime(2020, 1, 1),
                datetime.datetime(2020, 1, 10),
            )

            assert dt_range.as_date_range() == ranges.FiniteDateRange(
                datetime.date(2020, 1, 1),
                datetime.date(2020, 1, 9),
            )

        def test_errors_if_different_timezones(self):
            dt_range = ranges.FiniteDatetimeRange(
                datetime.datetime(2020, 1, 1, tzinfo=zoneinfo.ZoneInfo("Asia/Dubai")),
                datetime.datetime(
                    2020, 1, 10, tzinfo=zoneinfo.ZoneInfo("Australia/Sydney")
                ),
            )

            with pytest.raises(ValueError) as exc_info:
                dt_range.as_date_range()

            assert "Start and end in different timezones" in str(exc_info.value)

        def test_errors_if_start_not_midnight(self):
            dt_range = ranges.FiniteDatetimeRange(
                datetime.datetime(2020, 1, 1, hour=1),
                datetime.datetime(2020, 1, 10),
            )

            with pytest.raises(ValueError) as exc_info:
                dt_range.as_date_range()

            assert "Start of range is not midnight-aligned" in str(exc_info.value)

        def test_errors_if_end_not_midnight(self):
            dt_range = ranges.FiniteDatetimeRange(
                datetime.datetime(2020, 1, 1),
                datetime.datetime(2020, 1, 10, hour=1),
            )

            with pytest.raises(ValueError) as exc_info:
                dt_range.as_date_range()

            assert "End of range is not midnight-aligned" in str(exc_info.value)


class TestAsFiniteDatetimePeriods:
    def test_converts(self):
        actually_finite_range = ranges.DatetimeRange(
            datetime.datetime(2020, 1, 1),
            datetime.datetime(2020, 1, 5),
        )

        results = list(
            ranges.as_finite_datetime_periods(
                [actually_finite_range],
            )
        )

        assert results == [
            ranges.FiniteDatetimeRange(
                actually_finite_range.start,
                actually_finite_range.end,
            )
        ]

    def test_errors_if_infinite(self):
        with pytest.raises(ValueError) as exc_info:
            ranges.as_finite_datetime_periods(
                [
                    ranges.DatetimeRange(datetime.datetime(2020, 1, 1), None),
                ],
            )

        assert "Period is not finite at start or end or both" in str(exc_info.value)


class TestIterateOverMonths:
    @pytest.mark.parametrize(
        "row",
        [
            {
                "period": ranges.FiniteDatetimeRange(
                    datetime.datetime(2023, 6, 12, tzinfo=localtime.UTC),
                    datetime.datetime(2023, 6, 26, tzinfo=localtime.UTC),
                ),
                "expected": [
                    ranges.FiniteDatetimeRange(
                        datetime.datetime(2023, 6, 12, tzinfo=localtime.UTC),
                        datetime.datetime(2023, 6, 26, tzinfo=localtime.UTC),
                    )
                ],
                "id": "within-one-month",
            },
            {
                "period": ranges.FiniteDatetimeRange(
                    datetime.datetime(2021, 5, 12, tzinfo=localtime.UTC),
                    datetime.datetime(2021, 6, 26, tzinfo=localtime.UTC),
                ),
                "expected": [
                    ranges.FiniteDatetimeRange(
                        datetime.datetime(2021, 5, 12, tzinfo=localtime.UTC),
                        datetime.datetime(2021, 6, 1, tzinfo=localtime.UTC),
                    ),
                    ranges.FiniteDatetimeRange(
                        datetime.datetime(2021, 6, 1, tzinfo=localtime.UTC),
                        datetime.datetime(2021, 6, 26, tzinfo=localtime.UTC),
                    ),
                ],
                "id": "spanning-two-months",
            },
            {
                "period": ranges.FiniteDatetimeRange(
                    datetime.datetime(2021, 4, 12, tzinfo=localtime.UTC),
                    datetime.datetime(2021, 6, 26, tzinfo=localtime.UTC),
                ),
                "expected": [
                    ranges.FiniteDatetimeRange(
                        datetime.datetime(2021, 4, 12, tzinfo=localtime.UTC),
                        datetime.datetime(2021, 5, 1, tzinfo=localtime.UTC),
                    ),
                    ranges.FiniteDatetimeRange(
                        datetime.datetime(2021, 5, 1, tzinfo=localtime.UTC),
                        datetime.datetime(2021, 6, 1, tzinfo=localtime.UTC),
                    ),
                    ranges.FiniteDatetimeRange(
                        datetime.datetime(2021, 6, 1, tzinfo=localtime.UTC),
                        datetime.datetime(2021, 6, 26, tzinfo=localtime.UTC),
                    ),
                ],
                "id": "spanning-three-months",
            },
            {
                "period": ranges.FiniteDatetimeRange(
                    datetime.datetime(2021, 1, 31, 0, 0, tzinfo=localtime.UTC),
                    datetime.datetime(2022, 2, 1, 0, 0, tzinfo=localtime.UTC),
                ),
                "expected": [
                    ranges.FiniteDatetimeRange(
                        datetime.datetime(2021, 1, 31, 0, 0, tzinfo=localtime.UTC),
                        datetime.datetime(2021, 2, 1, 0, 0, tzinfo=localtime.UTC),
                    ),
                    ranges.FiniteDatetimeRange(
                        datetime.datetime(2021, 2, 1, 0, 0, tzinfo=localtime.UTC),
                        datetime.datetime(2021, 3, 1, 0, 0, tzinfo=localtime.UTC),
                    ),
                    ranges.FiniteDatetimeRange(
                        datetime.datetime(2021, 3, 1, 0, 0, tzinfo=localtime.UTC),
                        datetime.datetime(2021, 4, 1, 0, 0, tzinfo=localtime.UTC),
                    ),
                    ranges.FiniteDatetimeRange(
                        datetime.datetime(2021, 4, 1, 0, 0, tzinfo=localtime.UTC),
                        datetime.datetime(2021, 5, 1, 0, 0, tzinfo=localtime.UTC),
                    ),
                    ranges.FiniteDatetimeRange(
                        datetime.datetime(2021, 5, 1, 0, 0, tzinfo=localtime.UTC),
                        datetime.datetime(2021, 6, 1, 0, 0, tzinfo=localtime.UTC),
                    ),
                    ranges.FiniteDatetimeRange(
                        datetime.datetime(2021, 6, 1, 0, 0, tzinfo=localtime.UTC),
                        datetime.datetime(2021, 7, 1, 0, 0, tzinfo=localtime.UTC),
                    ),
                    ranges.FiniteDatetimeRange(
                        datetime.datetime(2021, 7, 1, 0, 0, tzinfo=localtime.UTC),
                        datetime.datetime(2021, 8, 1, 0, 0, tzinfo=localtime.UTC),
                    ),
                    ranges.FiniteDatetimeRange(
                        datetime.datetime(2021, 8, 1, 0, 0, tzinfo=localtime.UTC),
                        datetime.datetime(2021, 9, 1, 0, 0, tzinfo=localtime.UTC),
                    ),
                    ranges.FiniteDatetimeRange(
                        datetime.datetime(2021, 9, 1, 0, 0, tzinfo=localtime.UTC),
                        datetime.datetime(2021, 10, 1, 0, 0, tzinfo=localtime.UTC),
                    ),
                    ranges.FiniteDatetimeRange(
                        datetime.datetime(2021, 10, 1, 0, 0, tzinfo=localtime.UTC),
                        datetime.datetime(2021, 11, 1, 0, 0, tzinfo=localtime.UTC),
                    ),
                    ranges.FiniteDatetimeRange(
                        datetime.datetime(2021, 11, 1, 0, 0, tzinfo=localtime.UTC),
                        datetime.datetime(2021, 12, 1, 0, 0, tzinfo=localtime.UTC),
                    ),
                    ranges.FiniteDatetimeRange(
                        datetime.datetime(2021, 12, 1, 0, 0, tzinfo=localtime.UTC),
                        datetime.datetime(2022, 1, 1, 0, 0, tzinfo=localtime.UTC),
                    ),
                    ranges.FiniteDatetimeRange(
                        datetime.datetime(2022, 1, 1, 0, 0, tzinfo=localtime.UTC),
                        datetime.datetime(2022, 2, 1, 0, 0, tzinfo=localtime.UTC),
                    ),
                ],
                "id": "spanning-thirteen-months",
            },
        ],
        ids=lambda row: row["id"],
    )
    def test_yields_correct_ranges(self, row):
        result = list(
            ranges.iterate_over_months(period=row["period"], tz=localtime.UTC)
        )

        assert result == row["expected"]


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
