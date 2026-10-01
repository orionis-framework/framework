from dataclasses import FrozenInstanceError
from orionis.orm.schema.constraints.foreign_reference import ForeignReference
from orionis.test import TestCase

class TestForeignReference(TestCase):
    """Verify parsing and the immutable foreign-key reference contract."""

    def testParsePreservesTheQualifiedReference(self) -> None:
        """Parse and round-trip a qualified table and column name.

        Returns
        -------
        None
            Verify parsed fields, equality, and the qualified representation.
        """
        reference = ForeignReference.parse("companies.company_id")
        self.assertEqual(reference.table, "companies")
        self.assertEqual(reference.column, "company_id")
        self.assertEqual(reference.qualified(), "companies.company_id")
        self.assertEqual(reference, ForeignReference("companies", "company_id"))

    def testParseRejectsMissingExtraAndNonStringSegments(self) -> None:
        """Reject references without exactly two non-empty string segments.

        Returns
        -------
        None
            Verify malformed and non-string inputs raise ValueError.
        """
        for value in ("", "companies", ".id", "companies.", "a.b.c", None, 7):
            with self.assertRaises(ValueError):
                ForeignReference.parse(value)  # type: ignore[arg-type]

    def testReferencesAreImmutableAndHashable(self) -> None:
        """Keep reference value objects immutable and dictionary-free.

        Returns
        -------
        None
            Verify equivalent references share hashing and reject mutation.
        """
        reference = ForeignReference("companies", "id")
        self.assertEqual(
            {reference, ForeignReference.parse("companies.id")},
            {reference},
        )
        self.assertFalse(hasattr(reference, "__dict__"))
        attribute = "table"
        with self.assertRaises(FrozenInstanceError):
            setattr(reference, attribute, "other")
