from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Generic, Optional, TypeVar

import intervaltree  # type: ignore[import-untyped]

from xocto.types.generic import Comparable


TBoundary = TypeVar("TBoundary", bound=Comparable[Any])
TData = TypeVar("TData")


class Interval(Generic[TBoundary, TData]):
    _start: TBoundary
    _end: TBoundary
    _data: TData
    _interval: Optional[intervaltree.IntervalTree]

    __slots__ = ("_start", "_end", "_data", "_interval")

    def __init__(
        self,
        start: TBoundary,
        end: TBoundary,
        data: TData,
    ) -> None:
        if start > end:
            raise ValueError("interval.start must be <= interval.end")
        self._start = start
        self._end = end
        self._data = data
        self._interval = None

    @property
    def start(self) -> TBoundary:
        return self._start

    @property
    def end(self) -> TBoundary:
        return self._end

    @property
    def data(self) -> TData:
        return self._data

    def __eq__(self, other: Any) -> bool:
        # Do not simply check that fields match here.
        # Using object equivalence allows us to insert the same interval multiple times.
        return other is self


class IntervalTree(Generic[TBoundary, TData]):
    """
    An interval tree.
    https://en.wikipedia.org/wiki/Interval_tree

    An interval is always inclusive-exclusive.

    This allows for efficient querying of intervals overlapping a given interval/point.

    Note that there is some cost to building the tree, so there is a tradeoff here.
    """

    def __init__(
        self, intervals: Optional[Iterable[Interval[TBoundary, TData]]] = None
    ) -> None:
        interval_tree_intervals = [
            intervaltree.Interval(interval.start, interval.end, interval)
            for interval in (intervals or [])
        ]
        for interval_tree_interval, interval in zip(
            interval_tree_intervals, (intervals or [])
        ):
            interval._interval = interval_tree_interval
        self._tree = intervaltree.IntervalTree(interval_tree_intervals)

    def insert(
        self, interval: Interval[TBoundary, TData]
    ) -> Interval[TBoundary, TData]:
        interval_tree_interval = intervaltree.Interval(
            interval.start, interval.end, interval
        )
        interval._interval = interval_tree_interval
        self._tree.add(interval_tree_interval)
        return interval

    def remove(self, interval: Interval[TBoundary, TData]) -> None:
        try:
            self._tree.remove(interval=interval._interval)  # noqa: SLF001
        except ValueError:
            # If the interval wasn't present
            return

    def remove_all(self) -> None:
        self._tree.clear()

    def start(self) -> TBoundary | None:
        if self._tree.is_empty():
            return None
        return self._tree.begin()

    def end(self) -> TBoundary | None:
        if self._tree.is_empty():
            return None
        return self._tree.end()

    def __len__(self) -> int:
        return len(self._tree)

    def is_empty(self) -> bool:
        return self._tree.is_empty()

    def all(self) -> list[Interval[TBoundary, TData]]:
        """
        Return all the intervals within the tree.
        The returned intervals will be sorted.
        """
        return [interval.data for interval in sorted(self._tree.items())]

    def overlapping(
        self, start: TBoundary, end: TBoundary
    ) -> list[Interval[TBoundary, TData]]:
        """
        Return all the intervals overlapping the passed interval.
        The returned intervals will be sorted.
        """
        matching_intervals = self._tree.overlap(start, end)
        return [interval.data for interval in sorted(matching_intervals)]

    def overlapping_point(self, point: Any) -> list[Interval[TBoundary, TData]]:
        """
        Return all the intervals overlapping the passed point.
        The returned intervals will be sorted.
        """
        matching_intervals = self._tree.at(point)
        return [interval.data for interval in sorted(matching_intervals)]
