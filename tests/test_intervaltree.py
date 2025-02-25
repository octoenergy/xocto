import pytest

from xocto.intervaltree import Interval, IntervalTree


class TestIntervalTree:
    class TestStart:
        def test_returns_none_if_tree_is_empty(self):
            assert IntervalTree().start() is None

        def test_returns_start_if_tree_is_not_empty(self):
            tree = IntervalTree(
                [
                    Interval(1, 2, "red"),
                    Interval(2, 3, "green"),
                    Interval(0, 1, "blue"),
                ]
            )
            assert tree.start() == 0

    class TestEnd:
        def test_returns_none_if_tree_is_empty(self):
            assert IntervalTree().end() is None

        def test_returns_end_if_tree_is_not_empty(self):
            tree = IntervalTree(
                [
                    Interval(1, 2, "red"),
                    Interval(2, 3, "green"),
                    Interval(0, 1, "blue"),
                ]
            )
            assert tree.end() == 3

    class TestLen:
        def test_returns_0_for_empty_tree(self):
            assert len(IntervalTree()) == 0

        def test_returns_length_of_tree(self):
            tree = IntervalTree(
                [
                    Interval(1, 2, "red"),
                    Interval(2, 3, "green"),
                    Interval(0, 1, "blue"),
                ]
            )
            assert len(tree) == 3

    class TestIsEmpty:
        def test_returns_true_if_tree_is_empty(self):
            assert IntervalTree().is_empty()

        def test_returns_false_if_tree_is_not_empty(self):
            tree = IntervalTree([Interval(0, 1, "red")])
            assert not tree.is_empty()

    class TestAll:
        def test_returns_all_the_intervals_sorted(self):
            tree = IntervalTree(
                [
                    Interval(1, 2, "red"),
                    Interval(2, 3, "green"),
                    Interval(0, 1, "blue"),
                ]
            )
            assert _as_tuples(tree.all()) == [
                (0, 1, "blue"),
                (1, 2, "red"),
                (2, 3, "green"),
            ]

    class TestInsert:
        def test_inserts_into_tree(self):
            tree = IntervalTree()
            assert tree.is_empty()

            tree.insert(Interval(0, 1, "red"))

            assert _as_tuples(tree.all()) == [(0, 1, "red")]

        def test_can_insert_same_interval_twice_with_different_data(self):
            tree = IntervalTree()
            assert tree.is_empty()

            tree.insert(Interval(0, 1, "red"))
            tree.insert(Interval(0, 1, "blue"))

            assert len(tree) == 2
            assert set(_as_tuples(tree.all())) == {(0, 1, "red"), (0, 1, "blue")}

        def test_can_insert_same_interval_twice_with_equal_data(self):
            tree = IntervalTree()
            assert tree.is_empty()

            tree.insert(Interval(0, 1, "red"))
            tree.insert(Interval(0, 1, "red"))

            assert len(tree) == 2
            assert set(_as_tuples(tree.all())) == {(0, 1, "red"), (0, 1, "red")}

    class TestRemove:
        def test_removes_from_tree(self):
            tree = IntervalTree()
            interval_red = tree.insert(Interval(0, 1, "red"))
            tree.insert(Interval(0, 1, "blue"))
            assert len(tree) == 2

            tree.remove(interval_red)
            assert len(tree) == 1
            assert _as_tuples(tree.all()) == [(0, 1, "blue")]

        def test_only_removes_matching_interval(self):
            tree = IntervalTree()
            interval_red_1 = tree.insert(Interval(0, 1, "red"))
            tree.insert(Interval(0, 1, "red"))
            assert len(tree) == 2

            tree.remove(interval_red_1)

            assert len(tree) == 1
            assert _as_tuples(tree.all()) == [(0, 1, "red")]

        def test_does_not_error_if_interval_does_not_exist_in_tree(self):
            tree = IntervalTree()
            interval = tree.insert(Interval(0, 1, "red"))
            assert not tree.is_empty()

            tree.remove(interval)
            assert tree.is_empty()

            # Does not error.
            tree.remove(interval)

    class TestOverlapping:
        @pytest.mark.parametrize(
            "start, end, expected_results",
            [
                [0, 0, []],
                [3, 3, []],
                [
                    0,
                    2,
                    [
                        (0, 1, "blue"),
                        (1, 2, "red"),
                    ],
                ],
                [
                    1,
                    3,
                    [
                        (1, 2, "red"),
                        (2, 3, "green"),
                    ],
                ],
                [
                    0.5,
                    2.5,
                    [
                        (0, 1, "blue"),
                        (1, 2, "red"),
                        (2, 3, "green"),
                    ],
                ],
            ],
        )
        def test_returns_intervals_overlapping_the_query(
            self, start, end, expected_results
        ):
            tree = IntervalTree(
                [
                    Interval(1, 2, "red"),
                    Interval(2, 3, "green"),
                    Interval(0, 1, "blue"),
                ]
            )
            assert _as_tuples(tree.overlapping(start, end)) == expected_results

    class TestOverlappingPoint:
        @pytest.mark.parametrize(
            "point, expected_results",
            [
                [0, [(0, 1, "blue")]],
                [3, []],
                [1.5, [(1, 2, "red")]],
            ],
        )
        def test_returns_intervals_overlapping_the_query(self, point, expected_results):
            tree = IntervalTree(
                [
                    Interval(1, 2, "red"),
                    Interval(2, 3, "green"),
                    Interval(0, 1, "blue"),
                ]
            )
            assert _as_tuples(tree.overlapping_point(point)) == expected_results


def _as_tuples(intervals):
    return [(interval.start, interval.end, interval.data) for interval in intervals]
