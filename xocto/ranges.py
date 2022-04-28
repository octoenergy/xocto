from __future__ import annotations

import datetime
import enum
import functools
import itertools
import operator
from typing import Generic, Iterable, Iterator, List, Optional, Sequence, TypeVar, Union, cast

from . import types


class RangeBoundaries(enum.Enum):
    EXCLUSIVE_EXCLUSIVE = "()"
    EXCLUSIVE_INCLUSIVE = "(]"
    INCLUSIVE_EXCLUSIVE = "[)"
    INCLUSIVE_INCLUSIVE = "[]"

    @classmethod
    def from_bounds(cls, left_exclusive: bool, right_exclusive: bool) -> "RangeBoundaries":
        """
        Convenience method to get the relevant boundary type by specifiying the exclusivity of each
        end.
        """
        return {
            (True, True): RangeBoundaries.EXCLUSIVE_EXCLUSIVE,
            (True, False): RangeBoundaries.EXCLUSIVE_INCLUSIVE,
            (False, True): RangeBoundaries.INCLUSIVE_EXCLUSIVE,
            (False, False): RangeBoundaries.INCLUSIVE_INCLUSIVE,
        }[(left_exclusive, right_exclusive)]


T = TypeVar("T", bound=types.Comparable)


@functools.total_ordering
class Range(Generic[T]):
    """
    The basic concept of an range of some sort of comparable item, specified by its endpoints
    and boundaries (whether the endpoints are inclusive or exclusive). This class provides some
    useful helpers for working with ranges.

    Usage:

    * Ranges are declared by specifying their endpoints and boundaries. If the boundaries is
      omitted, then they are inclusive-exclusive by default

        >>> Range(0, 2, boundaries=RangeBoundaries.EXCLUSIVE_INCLUSIVE)
        <Range: (0,2]>
        >>> Range(0, 2, boundaries="[]")
        <Range: [0,2]>
        >>> r = Range(0, 2)
        >>> print(f"{r}")
        "[0,2)"

    * If an endpoint is set as None, then that means that the range is effectively infinite.
      Infinite ranges must have exclusive bounds for the infinite ends. We provide the continuum
      to the continnum
      helper to get an unbounded range.

        >>> Range(0, None)
        <Range: [0, None)
        >>> Range(0, None, boundaries="[]")  # Invalid
        >>> Range.continuum()  # Helper function
        <Range: (None, None)>

    * Ranges can be declared for any comparable type

        >>> int_erval: Range[int] = Range(0, 2)
        >>> date_erval: Range[date] = Range(date(2020, 1, 1), date(2020, 6, 6))
        >>> string_erval: Range[str] = Range("ardvark", "zebra")  # Uses lexical ordering

    * Ranges are themselves comparable. Two ranges are ordered by their start, with their end used
      to break ties

        >>> sorted([Range(1, 4), Range(0, 5)])
        [<Range: [0,5)>, <Range: [1,4)>]
        >>> sorted([Range(1, 2), Range(None, 2)])
        [<Range: [None,2)>, <Range: [1,2)>]
        >>> sorted([Range(3, 5), Range(3, 4)])
        [<Range: [3,4)>, <Range: [4,5)>]
        >>> sorted([Range(0, 2, boundaries=b) for b in RangeBoundaries])
        [<Range: [0,2)>, <Range: [0,2]>, <Range: (0,2)>, <Range: (0,2]>]

    * The `in` operator is provided to check if an item of the range type is within the
      the range

        >>> 0 in Range(0, 2)
        True
        >>> 2 in Range(0, 2)
        False
        >>> date(2020, 1, 1) in Range(date(2020, 1, 2), date(2020, 1, 5))
        False

    * The `intersection` function (which is aliased to the and (&) operator) will return the
      overlap of two ranges, or None if they are disjoint
        >>> Range(0, 2).intersection(Range(1, 4))
        <Range: [1,2)>
        >>> Range(1, 2) & Range(3, 4)
        None

    * The `is_disjoint` function will tell you if two ranges are disjoint
        >>> Range(0, 2).is_disjoint(Range(3, 5))
        True
        >>> Range(0, 2).is_disjoint(Range(2, 5))  # Since the default is not right-inclusive
        True

    * The `union` function (which is aliased to the or (|) operator), will return a range which
      covers two overlapping (or adjacent) ranges, or None if they are disjoint.
        >>> Range(0, 2).union(Range(1, 3))
        <Range: [0,3)>
        >>> Range(0, 2) | Range(2, 4)
        <Range: [0,4)>
        >>> Range(0, 2) | Range(3, 4)
        None
        >>> Range(0, 2) | Range(2, 4, boundaries="(]")
        None

    * The `difference` function (which is aliased to the subtraction (-) operator), will return a
      range which contains the bit of this range which is not covered by the other range, or a
      rangeset which contains the bits of this range which are not covered (or None if the other
      range covers this one).
        >>> Range(0, 4) - Range(2, 4)
        <Range: [0,2)>
        >>> Range(0, 4) - Range(2, 3)
        <RangeSet: {[0,2), [3,4)}>
        >>> Range(0, 4) - Range(0, 5)
        None
    """

    __slots__ = [
        "start",
        "end",
        "boundaries",
        "_is_left_exclusive",
        "_is_left_inclusive",
        "_is_right_exclusive",
        "_is_right_inclusive",
    ]

    def __init__(
        self,
        start: Optional[T],
        end: Optional[T],
        *,
        boundaries: Union[str, RangeBoundaries] = RangeBoundaries.INCLUSIVE_EXCLUSIVE,
    ):
        """
        Validate that the provided start and end values create a valid range for the boundaries.

        Also set some convenience properties for internal use.
        """
        self.start = start
        self.end = end
        # Make sure that we are dealing with an enum in case the class was constructed with the
        # string representation of the boundaries
        self.boundaries: RangeBoundaries = RangeBoundaries(boundaries)

        self._is_left_exclusive = self.boundaries in [
            RangeBoundaries.EXCLUSIVE_EXCLUSIVE,
            RangeBoundaries.EXCLUSIVE_INCLUSIVE,
        ]
        self._is_right_exclusive = self.boundaries in [
            RangeBoundaries.EXCLUSIVE_EXCLUSIVE,
            RangeBoundaries.INCLUSIVE_EXCLUSIVE,
        ]
        self._is_left_inclusive = not self._is_left_exclusive
        self._is_right_inclusive = not self._is_right_exclusive

        if self.start is None:
            if self._is_left_inclusive:
                raise ValueError("Range with unbounded start must be left-exclusive")
        elif self.end is None:
            if self._is_right_inclusive:
                raise ValueError("Ranges with unbounded ends must be right-inclusive")
        else:
            check_op = {
                RangeBoundaries.EXCLUSIVE_EXCLUSIVE: operator.lt,
                RangeBoundaries.EXCLUSIVE_INCLUSIVE: operator.lt,
                RangeBoundaries.INCLUSIVE_EXCLUSIVE: operator.lt,
                RangeBoundaries.INCLUSIVE_INCLUSIVE: operator.le,
            }[self.boundaries]
            if not check_op(self.start, self.end):
                raise ValueError("Invalid boundaries for range")

    @classmethod
    def continuum(cls) -> Range:
        """
        Return a range representing the continnum.
        """
        return cls(None, None, boundaries="()")

    def __str__(self) -> str:
        if self._is_left_exclusive:
            lbracket = "("
        else:
            lbracket = "["

        if self._is_right_exclusive:
            rbracket = ")"
        else:
            rbracket = "]"

        return f"{lbracket}{self.start},{self.end}{rbracket}"

    def __repr__(self) -> str:
        return f"<Range: {str(self)}>"

    def __hash__(self) -> int:
        return hash((self.start, self.end, self.boundaries))

    def __eq__(self, other) -> bool:
        if not isinstance(other, Range):
            return False

        return (self.start, self.end, self.boundaries) == (
            other.start,
            other.end,
            other.boundaries,
        )

    def __lt__(self, other: "Range[T]") -> bool:
        if self.start == other.start:
            if self._is_left_exclusive and not other._is_left_exclusive:
                return False

            if (not self._is_left_exclusive) and other._is_left_exclusive:
                return True

            if self.end == other.end:
                if self._is_right_exclusive and not other._is_right_exclusive:
                    return True

                return False
            else:
                # If one endpoint is None then that range is greater, otherwise compare them
                return (other.end is None) or (self.end is not None and self.end < other.end)
        else:
            # If one endpoint is None then that range is lesser, otherwise compare them
            return (self.start is None) or (other.start is not None and self.start < other.start)

    def __contains__(self, item: T) -> bool:
        """
        Check if the provided item is inside the range.
        """
        return self._is_inside_left_bound(item) and self._is_inside_right_bound(item)

    def _is_inside_left_bound(self, item: T) -> bool:
        """
        Check if the provided item is inside our left bound.
        """
        if self.start is None:
            return True
        elif self._is_left_exclusive:
            return item > self.start
        else:
            return item >= self.start

    def _is_inside_right_bound(self, item: T) -> bool:
        """
        Check if the provided item is inside our right bound.
        """
        if self.end is None:
            return True
        elif self._is_right_exclusive:
            return item < self.end
        else:
            return item <= self.end

    def is_disjoint(self, other: "Range[T]") -> bool:
        """
        Test whether the two ranges are disjoint.
        """
        if self.end is not None and other.start is not None:
            if not (
                self._is_inside_right_bound(other.start) and other._is_inside_left_bound(self.end)
            ):
                return True

        if self.start is not None and other.end is not None:
            if not (
                self._is_inside_left_bound(other.end) and other._is_inside_right_bound(self.start)
            ):
                return True

        return False

    def intersection(self, other: "Range[T]") -> Optional["Range[T]"]:
        """
        Return the intersection of the two ranges if it exists, or None if they are disjoint.
        """
        if self.is_disjoint(other):
            return None

        range_l, range_r = (self, other) if self < other else (other, self)

        # Since we have sorted the two ranges, the left will always be determined by range_r, but
        # the right depends on whether range_l contains range_r or not.
        #
        # This has the effect of making the intersection prefer an inclusive right boundary to an
        # equivalent exclusive one (e.g. [0,2] is preferred over [0,3))

        if range_l.end is not None and range_r._is_inside_right_bound(range_l.end):
            end: Optional[T] = range_l.end
            right_exclusive = range_l._is_right_exclusive
        else:
            end = range_r.end
            right_exclusive = range_r._is_right_exclusive

        boundaries = RangeBoundaries.from_bounds(range_r._is_left_exclusive, right_exclusive)

        return Range(range_r.start, end, boundaries=boundaries)

    def union(self, other: "Range[T]") -> Optional["Range[T]"]:
        """
        If two ranges overlap (or are adjacent), return an range covering the two ranges. If the
        two ranges are disjoint, return None.
        """
        range_l, range_r = (self, other) if self < other else (other, self)

        if range_l.is_disjoint(range_r) and not (
            range_l.end == range_r.start
            and (range_l._is_right_inclusive or range_r._is_left_inclusive)
        ):
            return None

        # Since we have sorted the two ranges, the left will always be determined by range_l, but
        # the right depends on whether range_l contains range_r or not.
        #
        # This has the effect of making the resulting union prefer an exclusive right boundary to
        # the equivalent inclusive one (e.g. [0,3) is preferred over [0,2]).
        if range_r.end is not None and range_l._is_inside_right_bound(range_r.end):
            end = range_l.end
            right_exclusive = range_l._is_right_exclusive
        else:
            end = range_r.end
            right_exclusive = range_r._is_right_exclusive

        boundaries = RangeBoundaries.from_bounds(range_l._is_left_exclusive, right_exclusive)

        return Range(range_l.start, end, boundaries=boundaries)

    def difference(self, other: "Range[T]") -> Optional[Union["Range[T]", "RangeSet[T]"]]:
        """
        Return a range or rangeset consisting of the bits of this range that do not intersect the
        other range (or None if this range is covered by the other range).
        """
        if self.is_disjoint(other):
            return self

        if (self.start is None and other.start is not None) or (
            self.start is not None
            and other.start is not None
            and not other._is_inside_left_bound(self.start)
            and self._is_inside_left_bound(other.start)
        ):
            boundaries = RangeBoundaries.from_bounds(
                self._is_left_exclusive, other._is_left_inclusive
            )
            lower_part: Optional["Range[T]"] = Range(
                self.start, other.start, boundaries=boundaries
            )
        else:
            lower_part = None

        if (self.end is None and other.end is not None) or (
            self.end is not None
            and other.end is not None
            and not other._is_inside_right_bound(self.end)
            and self._is_inside_right_bound(other.end)
        ):
            boundaries = RangeBoundaries.from_bounds(
                other._is_right_inclusive, self._is_right_exclusive
            )
            upper_part: Optional["Range[T]"] = Range(other.end, self.end, boundaries=boundaries)
        else:
            upper_part = None

        if lower_part is None and upper_part is None:
            return None
        elif lower_part is not None and upper_part is not None:
            return RangeSet([lower_part, upper_part])
        else:
            return lower_part or upper_part

    def __and__(self, other: "Range[T]") -> Optional["Range[T]"]:
        """
        Wrapper for intersection to allow the & operator to be used.
        """
        return self.intersection(other)

    def __or__(self, other: "Range[T]") -> Optional["Range[T]"]:
        """
        Wrapper for union to allow the | operator to be used.
        """
        return self.union(other)

    def __sub__(self, other: "Range[T]") -> Optional[Union["Range[T]", "RangeSet[T]"]]:
        """
        Wrapper for difference to allow the - operator to be used.
        """
        return self.difference(other)

    def is_left_finite(self) -> bool:
        return self.start is not None

    def is_right_finite(self) -> bool:
        return self.end is not None

    def is_finite(self) -> bool:
        return self.is_left_finite() and self.is_right_finite()


# Type aliases for common range types
DatetimeRange = Range[datetime.datetime]


class FiniteRange(Range[T]):
    """
    A FiniteRange represents a range that MUST have finite endpoints (i.e. they cannot be None).

    This is mostly to add type checking, as we can specify that functions require a finite range
    and then skip checking if the endpoints are None.
    """

    start: T
    end: T

    def intersection(self, other: Range[T]) -> Optional["FiniteRange[T]"]:
        """
        Intersections with finite ranges will always be finite.
        """
        return cast("FiniteRange[T]", super().intersection(other))

    def __and__(self, other: Range[T]) -> Optional["FiniteRange[T]"]:
        return self.intersection(other)


class HalfFiniteRange(Range[T]):
    """
    This is also for type-checking, but represents a very common range type in Kraken (possibly
    the most common).

    Specifically, ranges that MUST have a finite inclusive left endpoint and a (possibly infinite)
    exclusive right endpoint.

    However LeftFiniteInclusiveRightExclusiveRange is a bit of a mouthful so we're going with
    HalfFiniteRange.
    """

    start: T
    boundaries = RangeBoundaries.INCLUSIVE_EXCLUSIVE

    def intersection(self, other: Range[T]) -> Optional["HalfFiniteRange[T]"]:
        """
        Intersections with half finite ranges will always be half finite.
        """
        return cast("HalfFiniteRange[T]", super().intersection(other))

    def __and__(self, other: Range[T]) -> Optional["HalfFiniteRange[T]"]:
        return self.intersection(other)


class RangeSet(Generic[T]):
    """
    A RangeSet represents an ordered set of disjoint ranges. It is constructed from an iterable of
    Ranges (which can be omited to create an empty RangeSet):

        >>> RangeSet()  # empty RangeSet
        <RangeSet: {}>
        >>> rs = RangeSet([Range(0, 1), Range(2, 4)])  # Single iterable of ranges
        >>> print(f"{rs}")
        "{[0,1), [2, 4)}"

    Overlapping Ranges are condensed when they are added to a set:

        >>> RangeSet([Range(0, 3), Range(2, 4)]) == RangeSet([Range(0, 4)])
        True
    """

    def __init__(self, source_ranges: Optional[Iterable[Range[T]]] = None):
        if source_ranges is None:
            # We need to type this as a Sequence so that it is covariant
            self._ranges: Sequence[Range[T]] = []
        else:
            self._ranges = self._condense_range_list(source_ranges)

    def __str__(self) -> str:
        ranges = ", ".join(str(r) for r in self._ranges)
        return f"{{{ranges}}}"

    def __repr__(self) -> str:
        return f"<RangeSet: {str(self)}>"

    def __eq__(self, other) -> bool:
        if not isinstance(other, RangeSet):
            return False

        return self._ranges == other._ranges

    def add(self, item: Range[T]):
        self._ranges = self._condense_range_list(itertools.chain(self._ranges, [item]))

    def _condense_range_list(self, source_ranges: Iterable[Range[T]]) -> List[Range[T]]:
        """
        Given an iterable of source ranges, return a sorted list of ranges where the ranges have
        been condensed into the smalles amount of disjoint ranges that matches the input.

        For example:

            * [[0,4), [1, 5), [7,9)] -> [[0,5), [7,9)]
        """
        # By sorting the source ranges we can check for overlaps by just looking at whether
        # there is an overlap with the most recent range we added
        ranges: List[Range[T]] = []
        for current_range in sorted(source_ranges):
            if not ranges:
                ranges.append(current_range)
                continue

            previous_range = ranges.pop()
            if (union := previous_range | current_range) is not None:
                ranges.append(union)
            else:
                ranges.extend([previous_range, current_range])

        return ranges

    def discard(self, item: Range[T]):
        """
        Discarding a range from a range set is equivalent to "cutting away" all the intersections
        of that range with the rangeset.
        """
        ranges: List[Range[T]] = []
        for r in self._ranges:
            difference = r - item
            if difference is None:
                continue
            if isinstance(difference, RangeSet):
                ranges.extend(difference._ranges)
            else:
                ranges.append(difference)

        self._ranges = self._condense_range_list(ranges)

    def pop(self) -> Range[T]:
        """
        Remove and return an arbitrary set element.

        Raises KeyError if the set is empty.
        """
        try:
            elem = self._ranges[0]
        except IndexError:
            raise KeyError

        self.discard(elem)
        return elem

    def __contains__(self, item: Range[T] | T) -> bool:
        """
        Note that this doesn't require exact matching - the target item just has to be inside one
        of the ranges in the set.
        """
        if isinstance(item, Range):
            return self.contains_range(item)
        else:
            return self.contains_item(item)

    def contains_range(self, range: Range[T]) -> bool:
        """Check a Range is fully contained within another Range within this RanegSet."""
        return any((r & range) == range for r in self._ranges)

    def contains_item(self, item: T) -> bool:
        """Check if an item is contained by any Range within this RangeSet."""
        return any(item in range_ for range_ in self)

    def is_disjoint(self, other: "RangeSet[T]") -> bool:
        """
        Check whether this RangeSet is disjoint from the other one.
        """
        return all(a.is_disjoint(b) for a in self._ranges for b in other._ranges)

    def __iter__(self) -> Iterator[Range[T]]:
        yield from self._ranges

    def __len__(self) -> int:
        """
        This isn't particularly useful for consumers, but makes equality work nicely.
        """
        return len(self._ranges)

    def intersection(self, other: Range[T] | RangeSet[T]) -> "RangeSet[T]":
        """
        Return the intersection of this RangeSet and the other Range or RangeSet.
        """
        if isinstance(other, Range):
            other_ranges: Iterable[Range[T]] = [other]
        else:
            other_ranges = other

        return RangeSet(
            intersection
            for r, s in itertools.product(self._ranges, other_ranges)
            if (intersection := r & s) is not None
        )

    def union(self, other: "RangeSet[T]") -> "RangeSet[T]":
        return RangeSet(itertools.chain(self._ranges, other._ranges))

    def __and__(self, other: "RangeSet[T]") -> "RangeSet[T]":
        """
        Wrapper for intersection to allow the & operator to be used.
        """
        return self.intersection(other)

    def __or__(self, other: "RangeSet[T]") -> "RangeSet[T]":
        """
        Wrapper for union to allow the | operator to be used.
        """
        return self.union(other)

    def is_finite(self) -> bool:
        return all([r.is_finite() for r in self._ranges])

    def complement(self) -> RangeSet[T]:
        """
        Get a rangeset representing the ranges between the ranges in this rangeset and infinite
        left and right bounds.
        """
        complement = []

        if not self:
            infinite_range: Range = Range(
                None, None, boundaries=RangeBoundaries.EXCLUSIVE_EXCLUSIVE
            )
            return RangeSet([infinite_range])

        if (first_range := self._ranges[0]).is_left_finite():
            complement.append(
                Range(
                    None,
                    first_range.start,
                    boundaries=RangeBoundaries.from_bounds(
                        left_exclusive=True,
                        right_exclusive=(not first_range._is_left_exclusive),
                    ),
                )
            )

        for preceeding_range, current_range in zip(self._ranges[:-1], self._ranges[1:]):

            complement.append(
                Range(
                    preceeding_range.end,
                    current_range.start,
                    boundaries=RangeBoundaries.from_bounds(
                        left_exclusive=(not preceeding_range._is_right_exclusive),
                        right_exclusive=(not current_range._is_left_exclusive),
                    ),
                )
            )

        if (last_range := self._ranges[-1]).is_right_finite():
            complement.append(
                Range(
                    last_range.end,
                    None,
                    boundaries=RangeBoundaries.from_bounds(
                        left_exclusive=(not last_range._is_right_exclusive),
                        right_exclusive=True,
                    ),
                )
            )

        return RangeSet(complement)

    def __neg__(self) -> RangeSet[T]:
        return self.complement()

    def __bool__(self) -> bool:
        return bool(len(self))

    def difference(self, other: RangeSet[T]) -> RangeSet[T]:
        """
        Return a rangeset consisting of the bits of this rangeset that do not intersect the other
        rangeset.
        """
        return self & (-other)

    def __sub__(self, other: RangeSet[T]) -> RangeSet[T]:
        return self.difference(other)


class FiniteRangeSet(RangeSet[T]):
    """
    This subclass is useful when dealing with finite intervals as we can offer stronger guarantees
    than we can get with normal RangeSets - mostly around intersections being finite etc.
    """

    _ranges: Sequence[FiniteRange[T]]

    def __iter__(self) -> Iterator[FiniteRange[T]]:
        yield from self._ranges

    def intersection(self, other: Range[T] | RangeSet[T]) -> "FiniteRangeSet[T]":
        return cast("FiniteRangeSet[T]", super().intersection(other))

    def pop(self) -> FiniteRange[T]:
        """
        Remove and return an arbitrary set element.

        Raises KeyError if the set is empty.
        """
        return cast(FiniteRange[T], super().pop())

    def __and__(self, other: RangeSet[T]) -> "FiniteRangeSet[T]":
        return self.intersection(other)


class FiniteDatetimeRange(FiniteRange[datetime.datetime]):
    """
    This subclass is a helper for a common usecase for ranges - representing finite intervals
    of time.
    """

    def __init__(self, start: datetime.datetime, end: datetime.datetime):
        """
        Force the boundaries of the range to be [).
        """
        super().__init__(start, end, boundaries=RangeBoundaries.INCLUSIVE_EXCLUSIVE)

    def intersection(self, other: Range[datetime.datetime]) -> Optional["FiniteDatetimeRange"]:
        """
        Intersections with finite ranges will always be finite.
        """
        base_intersection = super().intersection(other)
        if base_intersection is None:
            return None

        assert base_intersection.boundaries == RangeBoundaries.INCLUSIVE_EXCLUSIVE
        return FiniteDatetimeRange(base_intersection.start, base_intersection.end)

    def __and__(self, other: Range[datetime.datetime]) -> Optional["FiniteDatetimeRange"]:
        return self.intersection(other)

    @property
    def days(self) -> int:
        """
        Return the number of days between the start and end of the range.
        """
        return (self.end - self.start).days

    @property
    def seconds(self) -> int:
        """
        Return the number of seconds between the start and end of the range.
        """
        return int((self.end - self.start).total_seconds())


class FiniteDateRange(FiniteRange[datetime.date]):
    """
    This subclass is a helper for a common usecase for ranges - representing finite intervals
    of whole days.
    """

    def __init__(self, start: datetime.date, end: datetime.date):
        """
        Force the boundaries of the range to be [].
        """
        super().__init__(start, end, boundaries=RangeBoundaries.INCLUSIVE_INCLUSIVE)

    def intersection(self, other: Range[datetime.date]) -> Optional["FiniteDateRange"]:
        """
        Intersections with finite ranges will always be finite.
        """
        base_intersection = super().intersection(other)
        if base_intersection is None:
            return None

        assert base_intersection.boundaries == RangeBoundaries.INCLUSIVE_INCLUSIVE
        return FiniteDateRange(base_intersection.start, base_intersection.end)

    def __and__(self, other: Range[datetime.date]) -> Optional["FiniteDateRange"]:
        return self.intersection(other)

    @property
    def days(self) -> int:
        """
        Return the number of days between the start and end of the range.
        """
        return (self.end - self.start).days


def get_finite_datetime_ranges_from_timestamps(
    finite_datetime_range: FiniteDatetimeRange,
    timestamps,
) -> Sequence[FiniteDatetimeRange]:
    """
    Given a datetime range and some timestamps, cut that period into
    multiple points whenever one of the timestamps falls within it.

    Sorts and deduplicates the timestamps first.

    Example:

    - Input:
        - period: ("2021-09-01 00:00:00", "2021-10-01 00:00:00")
        - timestamps: ["2021-09-10 00:00:00", "2021-09-16 00:00:00", "2021-09-23 00:00:00"]
    - Return:
        [
            ("2021-09-01 00:00:00", "2021-09-10 00:00:00"),
            ("2021-09-10 00:00:00", "2021-09-16 00:00:00"),
            ("2021-09-16 00:00:00", "2021-09-23 00:00:00"),
            ("2021-09-23 00:00:00", "2021-10-01 00:00:00"),
        ]
    """
    timestamps_in_range = sorted(
        {timestamp for timestamp in timestamps if timestamp in finite_datetime_range}
    )

    return [
        FiniteDatetimeRange(start, end)
        for start, end in zip(
            [finite_datetime_range.start, *timestamps_in_range],
            [*timestamps_in_range, finite_datetime_range.end],
        )
        # We don't need to split when a timestamp is exactly at the start
        # or end of the period.
        if start != end
    ]
