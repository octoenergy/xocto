from typing import Any, Protocol, TypeVar


T = TypeVar("T", covariant=True)


class Comparable(Protocol[T]):
    """
    A way of describing an object that can be compared to another using some basic operations.
    """

    def __eq__(self, other: Any) -> bool: ...

    def __lt__(self, other: Any) -> bool: ...

    def __le__(self, other: Any) -> bool: ...

    def __gt__(self, other: Any) -> bool: ...

    def __ge__(self, other: Any) -> bool: ...
