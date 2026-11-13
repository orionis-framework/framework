# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Protect collection boundary values and constructor argument forwarding."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from orionis.support.types.collection import Collection
from orionis.support.types.contracts.collection import ICollection
from orionis.test import TestCase

if TYPE_CHECKING:
    from collections.abc import Callable


class _WrappedCollection(Protocol):
    """Describe the storage used by the independent contract adapter."""

    wrapped: Collection


def _delegate(name: str) -> Callable[..., object]:
    """Implement one collection contract operation through a contained collection."""

    def delegated(
        self: _WrappedCollection,
        *args: object,
        **kwargs: object,
    ) -> object:
        """Forward an operation without inheriting the concrete collection type."""
        return getattr(self.wrapped, name)(*args, **kwargs)

    return delegated


_AlternativeCollection = type(
    "_AlternativeCollection",
    (ICollection,),
    {name: _delegate(name) for name in ICollection.__abstractmethods__},
)


class TestCollectionRegressions(TestCase):
    """Exercise documented collection behavior using real containers."""

    def testMissingRemovalReturnsNoneWithoutChangingItems(self) -> None:
        """Treat absent indices and mapping keys as an empty removal."""
        for items, key in (([], 0), ([1], 5), ({"present": 1}, "absent")):
            with self.subTest(items=items, key=key):
                collection = Collection(items.copy())
                self.assertIsNone(collection.pull(key))
                self.assertEqual(collection.all(), items)
        self.assertIsNone(Collection().shift())

    def testZeroRandomCountReturnsEmptyCollection(self) -> None:
        """A zero-size sample follows the collection-returning count contract."""
        collection = Collection([1, 2, 3])
        result = collection.random(0)
        self.assertIs(result, collection)
        self.assertEqual(result.all(), [])

    def testMapIntoForwardsConstructorKeywordArguments(self) -> None:
        """Forward the same caller arguments to constructors and named factories."""
        result = Collection([b"one", b"two"]).mapInto(str, encoding="ascii")
        self.assertEqual(result.all(), ["one", "two"])

    def testAcceptsOtherCollectionContractImplementations(self) -> None:
        """Consume the all() contract instead of requiring a concrete subclass."""
        other = _AlternativeCollection()
        other.wrapped = Collection([2, 3])
        cases = (
            ("diff", Collection([1, 2]), (other,), [1]),
            ("merge", Collection([1]), (other,), [1, 2, 3]),
            ("zip", Collection([1, 2]), (other,), [[1, 2], [2, 3]]),
            ("whereIn", Collection([{"id": 1}, {"id": 2}]), ("id", other), [{"id": 2}]),
            (
                "whereNotIn",
                Collection([{"id": 1}, {"id": 2}]),
                ("id", other),
                [{"id": 1}],
            ),
        )
        for method, collection, arguments, expected in cases:
            with self.subTest(method=method):
                self.assertEqual(
                    getattr(collection, method)(*arguments).all(),
                    expected,
                )

    def testAggregatesUseOnlyValuesFromTheRequestedKey(self) -> None:
        """Distinguish no selected values from no requested selector."""
        for method in ("min", "max", "sum", "avg"):
            with self.subTest(method=method, key="missing"):
                self.assertEqual(
                    getattr(Collection([{"value": 9}]), method)("missing"),
                    0,
                )
            with self.subTest(method=method, key=""):
                self.assertEqual(getattr(Collection([{"": 3}]), method)(""), 3)

    def testEmptyMappingResultsKeepTheirMappingShape(self) -> None:
        """Keep the documented dictionary result even when there are no groups."""
        self.assertEqual(Collection().groupBy("kind").all(), {})
