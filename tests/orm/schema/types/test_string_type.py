from __future__ import annotations
from orionis.orm.schema.types import (
    String,
)
from orionis.orm.schema.types.column_type import ColumnType
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options

class TestString(TestCase):
    def testStringCarriesLength(self) -> None:
        """Store the declared length on string columns.

        Validates the string length parameter.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(String(120).length, 120)
        self.assertEqual(String().length, 255)

    def testStringRejectsInvalidLength(self) -> None:
        """Raise ValueError for non-positive string lengths.

        Validates the length guard.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            String(0)

class TestStringOptions(TestCase):
    """Verify String constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            Verify fresh declarations and independent configured metadata.
        """
        default = String()
        assert_column_options(
            self,
            default,
            ColumnType.STRING,
            length=255,
            collation=None,
        )
        configured = String(length=80, collation="binary")
        assert_column_options(
            self,
            configured,
            ColumnType.STRING,
            length=80,
            collation="binary",
        )
        self.assertIsNot(configured, default)

    def testSupportsUnspecifiedLengthAndRejectsInvalidValues(self) -> None:
        """Allow unbounded strings and reject invalid declared lengths.

        Returns
        -------
        None
            Verify unspecified, negative, and non-integer length cases.
        """
        self.assertIsNone(String(None).length)
        for length in (-1, 1.5, "10"):
            with self.assertRaises(ValueError):
                String(length)  # type: ignore[arg-type]
