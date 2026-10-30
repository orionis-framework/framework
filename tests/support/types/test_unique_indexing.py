from typing import Self
from orionis.support.types.collection import Collection
from orionis.test import TestCase

class TestUniqueIndexing(TestCase):
    """Preserve equality and insertion order while indexing built-in trees."""

    def testNestedBuiltinsAndNumericEquality(self: Self) -> None:
        """
        Index dictionaries independently of key order and numeric spelling.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        first = {"a": [1, {"x", "y"}], "b": b"value"}
        duplicate = {"b": bytearray(b"value"), "a": [True, frozenset({"y", "x"})]}
        other = {"a": (1, {"x", "y"}), "b": b"value"}
        for size in (1, 50):
            result = Collection([first, duplicate, other] * size).unique().all()
            self.assertEqual(result, [first, other])
            self.assertIs(result[0], first)

    def testSelectorsAndUnhashableFieldValues(self: Self) -> None:
        """
        Keep the first representative for explicit and structural keys.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        rows = [{"id": [1], "v": "first"}, {"id": [1], "v": "second"}, {"id": [2]}]
        self.assertEqual(Collection(rows).unique("id").all(), [rows[0], rows[2]])
        self.assertEqual(
            Collection(rows).unique(lambda row: row["id"][0]).all(),
            [rows[0], rows[2]],
        )

    def testCustomEqualityAndCyclesKeepFallback(self: Self) -> None:
        """
        Avoid inventing hashes for arbitrary equality implementations.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """

        class Same:
            __hash__ = None

            def __eq__(self: Self, other: object) -> bool:
                """
                Compare instances using the custom equality fallback.

                Parameters
                ----------
                other : object
                    Object to compare with this instance.

                Returns
                -------
                bool
                    Whether the other value satisfies the custom equality rule.
                """
                return isinstance(other, Same)

        first, second = Same(), Same()
        self.assertEqual(Collection([first, second] * 100).unique().all(), [first])
        cycle = []
        cycle.append(cycle)
        self.assertEqual(len(Collection([cycle, cycle] * 100).unique()), 1)
