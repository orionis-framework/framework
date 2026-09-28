from __future__ import annotations
from copy import copy
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.column.options import ColumnOptions
from orionis.orm.schema.constraints import ForeignReference
from orionis.orm.schema.types import (
    ColumnType,
    Enum,
    Integer,
    StrictDecimal,
    String,
)
from orionis.test import TestCase

class TestColumnDefinitions(TestCase):

    def testTypedColumnsHaveNoInstanceDictionary(self) -> None:
        """Keep typed column declarations inside their declared slots."""
        for column in (Integer(), String(), Enum("active", "inactive")):
            with self.subTest(column=type(column).__name__):
                self.assertFalse(hasattr(column, "__dict__"))
                with self.assertRaises(AttributeError):
                    column.unknown_option = True

    def testCopyPreservesAbsentAndExplicitDefaults(self) -> None:
        """Copy declarations without changing their default semantics."""
        original = Integer().primary().autoIncrement()
        duplicate = copy(original)
        duplicate.nullable()
        self.assertTrue(duplicate.is_primary)
        self.assertFalse(duplicate.hasDefault())
        self.assertFalse(original.is_nullable)
        self.assertTrue(copy(String().default(None)).hasDefault())

    def testCustomOptionsRemainIndependentFromDefaultColumns(self) -> None:
        """Preserve explicit options without changing later declarations."""
        configured = ColumnDefinition(
            ColumnType.STRING,
            ColumnOptions(length=80, collation="utf8", as_uuid=False),
        )
        default = ColumnDefinition(ColumnType.STRING)
        self.assertEqual(configured.length, 80)
        self.assertEqual(configured.collation, "utf8")
        self.assertFalse(configured.as_uuid)
        self.assertIsNone(default.length)
        self.assertIsNone(default.collation)
        self.assertTrue(default.as_uuid)

    # ── Fluent constraints ────────────────────────────────────────────────────

    def testFluentConstraintsChainAndFlag(self) -> None:
        """
        Chain every fluent constraint and verify the resulting flags.

        Validates the fluent API contract of column definitions.
        """
        column = (
            Integer()
            .primary()
            .autoIncrement()
            .unique()
            .index()
            .nullable()
        )
        self.assertTrue(column.is_primary)
        self.assertTrue(column.is_auto_increment)
        self.assertTrue(column.is_unique)
        self.assertTrue(column.has_index)
        self.assertTrue(column.is_nullable)

    def testDefaultDistinguishesNoneFromAbsent(self) -> None:
        """
        Distinguish a None default from the absence of a default.

        Validates the sentinel-based default tracking.
        """
        plain = Integer()
        self.assertFalse(plain.hasDefault())
        with_none = Integer().default(None)
        self.assertTrue(with_none.hasDefault())
        self.assertIsNone(with_none.default_value)

    def testForeignParsesQualifiedReference(self) -> None:
        """
        Parse a table.column reference into a value object.

        Validates the foreign key declaration.
        """
        column = Integer().foreign("companies.id")
        self.assertEqual(
            column.foreign_ref,
            ForeignReference(table="companies", column="id"),
        )
        self.assertEqual(column.foreign_ref.qualified(), "companies.id")

    def testForeignRejectsMalformedReference(self) -> None:
        """
        Raise ValueError for malformed foreign references.

        Validates the reference format guard.
        """
        with self.assertRaises(ValueError):
            Integer().foreign("companies")
        with self.assertRaises(ValueError):
            Integer().foreign("a.b.c")

    # ── Type parameters ───────────────────────────────────────────────────────

    def testStringCarriesLength(self) -> None:
        """
        Store the declared length on string columns.

        Validates the string length parameter.
        """
        self.assertEqual(String(120).length, 120)
        self.assertEqual(String().length, 255)

    def testStringRejectsInvalidLength(self) -> None:
        """
        Raise ValueError for non-positive string lengths.

        Validates the length guard.
        """
        with self.assertRaises(ValueError):
            String(0)

    def testDecimalCarriesPrecisionAndScale(self) -> None:
        """
        Store precision and scale on decimal columns.

        Validates the decimal shape parameters.
        """
        column = StrictDecimal(12, 4)
        self.assertEqual(column.precision, 12)
        self.assertEqual(column.scale, 4)

    def testDecimalRejectsInconsistentShape(self) -> None:
        """
        Raise ValueError when the scale exceeds the precision.

        Validates the decimal shape guard.
        """
        with self.assertRaises(ValueError):
            StrictDecimal(2, 5)

    def testEnumRequiresValues(self) -> None:
        """
        Require at least one non-empty enum value.

        Validates the enum value guard.
        """
        column = Enum("draft", "published")
        self.assertEqual(column.enum_values, ("draft", "published"))
        self.assertIs(column.column_type, ColumnType.ENUM)
        with self.assertRaises(ValueError):
            Enum()
