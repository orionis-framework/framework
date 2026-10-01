from __future__ import annotations
import json
from orionis.orm.collections.paginator import Paginator
from orionis.support.types.collection import Collection
from orionis.test import TestCase

class TestPaginator(TestCase):
    def _makePaginator(self, total: int, page: int, per_page: int) -> Paginator:
        """Build a paginator with dictionary items for serialization.

        Parameters
        ----------
        total : int
            Total number of rows.
        page : int
            Current page number.
        per_page : int
            Number of items per page.

        Returns
        -------
        Paginator
            Page containing two dictionary items.
        """
        return Paginator(
            items=Collection([{"id": 1}, {"id": 2}]),
            total=total,
            page=page,
            per_page=per_page,
        )

    def testMetadataDerivation(self) -> None:
        """Derive the last page and navigation flags from the metadata.

        Returns
        -------
        None
            Verify the pagination arithmetic and page length.
        """
        paginator = self._makePaginator(total=5, page=2, per_page=2)
        self.assertEqual(paginator.lastPage, 3)
        self.assertTrue(paginator.hasNext)
        self.assertTrue(paginator.hasPrevious)
        self.assertEqual(len(paginator), 2)

    def testBoundaryPages(self) -> None:
        """Report navigation flags correctly on boundary pages.

        Returns
        -------
        None
            Verify navigation from the first and last pages.
        """
        first = self._makePaginator(total=4, page=1, per_page=2)
        self.assertFalse(first.hasPrevious)
        self.assertTrue(first.hasNext)

        last = self._makePaginator(total=4, page=2, per_page=2)
        self.assertTrue(last.hasPrevious)
        self.assertFalse(last.hasNext)

    def testEmptyResultKeepsOnePage(self) -> None:
        """Keep the last page at one for empty result sets.

        Returns
        -------
        None
            Verify the empty pagination floor.
        """
        paginator = Paginator(items=Collection([]), total=0, page=1, per_page=10)
        self.assertEqual(paginator.lastPage, 1)
        self.assertFalse(paginator.hasNext)

    def testInvalidPageArgumentsRaise(self) -> None:
        """Reject non-positive page arguments.

        Returns
        -------
        None
            Verify the constructor rejects zero and negative values.
        """
        for invalid in (0, -1):
            with self.assertRaises(ValueError):
                self._makePaginator(total=1, page=invalid, per_page=2)
            with self.assertRaises(ValueError):
                self._makePaginator(total=1, page=1, per_page=invalid)

    def testRejectsBooleanAndNonIntegerPageArguments(self) -> None:
        """Reject boolean and non-integer page arguments.

        Returns
        -------
        None
            Verify neither page argument accepts coerced values.
        """
        for invalid in (True, False, 1.5, "1", None):
            with self.assertRaises(ValueError):
                self._makePaginator(
                    total=1,
                    page=invalid,  # type: ignore[arg-type]
                    per_page=2,
                )
            with self.assertRaises(ValueError):
                self._makePaginator(
                    total=1,
                    page=1,
                    per_page=invalid,  # type: ignore[arg-type]
                )

    def testKeepsItemsAndNormalizesNegativeTotals(self) -> None:
        """Keep the supplied collection and normalize negative totals.

        Returns
        -------
        None
            Verify stored metadata and the developer representation.
        """
        items = Collection([{"id": 1}])
        paginator = Paginator(items, total=-2, page=1, per_page=3)
        self.assertIs(paginator.items, items)
        self.assertEqual(paginator.total, 0)
        self.assertEqual(paginator.page, 1)
        self.assertEqual(paginator.perPage, 3)
        self.assertEqual(repr(paginator), "<Paginator page=1 perPage=3 total=0>")

    def testSerialization(self) -> None:
        """Serialize items and metadata into dictionary and JSON forms.

        Returns
        -------
        None
            Verify all pagination fields survive serialization.
        """
        paginator = self._makePaginator(total=5, page=1, per_page=2)
        expected = {
            "items": [{"id": 1}, {"id": 2}],
            "total": 5,
            "page": 1,
            "perPage": 2,
            "lastPage": 3,
            "hasNext": True,
            "hasPrevious": False,
        }
        self.assertEqual(paginator.toDict(), expected)
        self.assertEqual(json.loads(paginator.toJson(sort_keys=True)), expected)

class TestPaginationArithmetic(TestCase):
    """Check terminal guards and execution-context isolation."""

    def testPaginationUsesExactIntegerArithmetic(self) -> None:
        """Keep page counts exact beyond floating-point integer precision.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        paginator = Paginator(Collection(), total=2**60 + 1, page=1, per_page=2)
        self.assertEqual(paginator.lastPage, 2**59 + 1)
        self.assertTrue(paginator.hasNext)
        self.assertFalse(paginator.hasPrevious)
