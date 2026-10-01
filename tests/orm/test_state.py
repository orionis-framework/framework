from __future__ import annotations
from orionis.orm import Integer, Model, String
from orionis.test import TestCase

class _Note(Model):
    id = Integer().primary()
    title = String()
    body = String().nullable()
    timestamps = False

class TestModelState(TestCase):
    def _hydrated(self) -> _Note:
        """Build a hydrated model mimicking a database row.

        Returns
        -------
        _Note
            Value produced by the helper.
        """
        return _Note._newFromDatabase({"id": 1, "title": "a", "body": None})

    def testFreshInstanceTracksEveryAssignmentAsDirty(self) -> None:
        """Track attributes of unsaved models as dirty.

        Validates dirty detection for new keys.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        note = _Note({"title": "draft"})
        self.assertTrue(note.isDirty())
        self.assertEqual(note.getDirty(), {"title": "draft"})

    def testHydratedInstanceStartsClean(self) -> None:
        """Start hydrated models with a clean state.

        Validates the original snapshot taken at hydration.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        note = self._hydrated()
        self.assertTrue(note.isClean())
        self.assertEqual(note.getDirty(), {})

    def testDirtyDetectionPerAttribute(self) -> None:
        """Restrict dirty checks to specific attributes.

        Validates the attribute-scoped dirty queries.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        note = self._hydrated()
        note.title = "b"
        self.assertTrue(note.isDirty("title"))
        self.assertFalse(note.isDirty("body"))
        self.assertTrue(note.isClean("body"))
        self.assertFalse(note.isClean("title"))

    def testRevertingValueClearsDirtyState(self) -> None:
        """Clear the dirty state when the original value is restored.

        Validates value-based (not event-based) dirty tracking.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        note = self._hydrated()
        note.title = "changed"
        note.title = "a"
        self.assertTrue(note.isClean())

    def testGetOriginalReturnsSnapshotAndValues(self) -> None:
        """Serve the original snapshot wholly or per attribute.

        Validates getOriginal in both forms.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        note = self._hydrated()
        note.title = "b"
        self.assertEqual(note.getOriginal("title"), "a")
        self.assertEqual(note.getOriginal("missing", "x"), "x")
        snapshot = note.getOriginal()
        self.assertEqual(snapshot["title"], "a")

    def testSyncOriginalAdoptsCurrentValues(self) -> None:
        """Adopt the current values as the new original snapshot.

        Validates the syncOriginal contract.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        note = self._hydrated()
        note.title = "b"
        result = note.syncOriginal()
        self.assertIs(result, note)
        self.assertTrue(note.isClean())
        self.assertEqual(note.getOriginal("title"), "b")

    def testWasChangedAndGetChangesReflectLastSave(self) -> None:
        """Report the changes written by the last save only.

        Validates the changes bookkeeping without persistence.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        note = self._hydrated()
        self.assertFalse(note.wasChanged())
        self.assertEqual(note.getChanges(), {})
        # Simulate the bookkeeping performed by a successful save.
        note._changes = {"title": "b"}
        self.assertTrue(note.wasChanged())
        self.assertTrue(note.wasChanged("title"))
        self.assertFalse(note.wasChanged("body"))
        self.assertEqual(note.getChanges(), {"title": "b"})

class _Record(Model):
    id = Integer().primary()
    name = String()
    timestamps = False

class _ComparisonGuard:
    """Reject comparisons to an attribute outside the requested selection."""

    def __ne__(self, other: object) -> bool:
        """Raise if the caller evaluates this attribute.

        Parameters
        ----------
        other : object
            Value supplied for ``other``.

        Returns
        -------
        bool
            Value produced by the helper.

        Raises
        ------
        AssertionError
            Raised by this helper to exercise the failure path.
        """
        error_msg = f"Unexpected comparison with {type(other).__name__}."
        raise AssertionError(error_msg)

class TestModelHotPaths(TestCase):
    """Exercise attribute state and serialization without database access."""

    def testSelectedDirtyCheckDoesNotCompareUnrequestedAttributes(self) -> None:
        """Inspect only the requested attributes, including missing keys.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        record = _Record._newFromDatabase({"id": 1, "name": "before"})
        record.setAttribute("unrelated", _ComparisonGuard())
        self.assertFalse(record.isDirty("name", "missing"))
        record.name = "after"
        self.assertTrue(record.isDirty("missing", "name"))

    def testDirtyCheckStopsAtFirstChange(self) -> None:
        """Return after the first changed attribute without comparing the rest.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        record = _Record({"name": "changed"})
        record.setAttribute("unrelated", _ComparisonGuard())
        self.assertTrue(record.isDirty())

    def testMissingAndNoneRemainDistinct(self) -> None:
        """Track newly assigned null values and ignore absent attributes.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        record = _Record()
        self.assertFalse(record.isDirty("name"))
        record.name = None
        self.assertTrue(record.isDirty("name"))
        record.syncOriginal()
        self.assertTrue(record.isClean())
