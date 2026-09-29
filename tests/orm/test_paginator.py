from __future__ import annotations
import json
from orionis.orm.collections.paginator import Paginator
from orionis.support.types.collection import Collection
from orionis.test import TestCase

class TestPaginator(TestCase):

    def _make(self, total: int, page: int, per_page: int) -> Paginator:
        """Build a paginator with dictionary items for serialization.

        Parameters
        ----------
        total : int
            Value supplied for ``total``.
        page : int
            Value supplied for ``page``.
        per_page : int
            Value supplied for ``per_page``.

        Returns
        -------
        Paginator
            Value produced by the helper.
        """
        return Paginator(
            items=Collection([{"id": 1}, {"id": 2}]),
            total=total,
            page=page,
            per_page=per_page,
        )

    def testMetadataDerivation(self) -> None:
        """Derive lastPage and navigation flags from the metadata.

        Validates the pagination arithmetic.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        paginator = self._make(total=5, page=2, per_page=2)
        self.assertEqual(paginator.lastPage, 3)
        self.assertTrue(paginator.hasNext)
        self.assertTrue(paginator.hasPrevious)
        self.assertEqual(len(paginator), 2)

    def testBoundaryPages(self) -> None:
        """Report navigation flags correctly on boundary pages.

        Validates the first and last page flags.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        first = self._make(total=4, page=1, per_page=2)
        self.assertFalse(first.hasPrevious)
        self.assertTrue(first.hasNext)

        last = self._make(total=4, page=2, per_page=2)
        self.assertTrue(last.hasPrevious)
        self.assertFalse(last.hasNext)

    def testEmptyResultKeepsOnePage(self) -> None:
        """Keep lastPage at one for empty result sets.

        Validates the empty pagination floor.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        paginator = Paginator(
            items=Collection([]),
            total=0,
            page=1,
            per_page=10,
        )
        self.assertEqual(paginator.lastPage, 1)
        self.assertFalse(paginator.hasNext)

    def testInvalidPageArgumentsRaise(self) -> None:
        """Raise ValueError for non-positive page arguments.

        Validates the constructor guards.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            self._make(total=1, page=0, per_page=2)
        with self.assertRaises(ValueError):
            self._make(total=1, page=1, per_page=0)

    def testSerialization(self) -> None:
        """Serialize items and metadata into dict and JSON forms.

        Validates the serialization contract.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        paginator = self._make(total=5, page=1, per_page=2)
        data = paginator.toDict()
        self.assertEqual(data["total"], 5)
        self.assertEqual(data["items"], [{"id": 1}, {"id": 2}])
        decoded = json.loads(paginator.toJson())
        self.assertEqual(decoded["lastPage"], 3)
