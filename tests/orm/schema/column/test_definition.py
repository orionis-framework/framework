from __future__ import annotations
from copy import copy
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.column.options import ColumnOptions
from orionis.orm.schema.constraints import ForeignReference
from orionis.orm.schema.types import (
    ColumnType,
    Integer,
    String,
)
from orionis.test import TestCase

class TestColumnDefinitions(TestCase):

    def testCopyPreservesAbsentAndExplicitDefaults(self) -> None:
        """Copy declarations without changing their default semantics.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        original = Integer().primary().autoIncrement()
        duplicate = copy(original)
        duplicate.nullable()
        self.assertTrue(duplicate.is_primary)
        self.assertFalse(duplicate.hasDefault())
        self.assertFalse(original.is_nullable)
        self.assertTrue(copy(String().default(None)).hasDefault())

    def testCustomOptionsRemainIndependentFromDefaultColumns(self) -> None:
        """Preserve explicit options without changing later declarations.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
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

    def testFluentConstraintsChainAndFlag(self) -> None:
        """Chain every fluent constraint and verify the resulting flags.

        Validates the fluent API contract of column definitions.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        column = Integer().primary().autoIncrement().unique().index().nullable()
        self.assertTrue(column.is_primary)
        self.assertTrue(column.is_auto_increment)
        self.assertTrue(column.is_unique)
        self.assertTrue(column.has_index)
        self.assertTrue(column.is_nullable)

    def testDefaultDistinguishesNoneFromAbsent(self) -> None:
        """Distinguish a None default from the absence of a default.

        Validates the sentinel-based default tracking.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        plain = Integer()
        self.assertFalse(plain.hasDefault())
        with_none = Integer().default(None)
        self.assertTrue(with_none.hasDefault())
        self.assertIsNone(with_none.default_value)

    def testForeignParsesQualifiedReference(self) -> None:
        """Parse a table.column reference into a value object.

        Validates the foreign key declaration.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        column = Integer().foreign("companies.id")
        self.assertEqual(
            column.foreign_ref,
            ForeignReference(table="companies", column="id"),
        )
        self.assertEqual(column.foreign_ref.qualified(), "companies.id")

    def testForeignRejectsMalformedReference(self) -> None:
        """Raise ValueError for malformed foreign references.

        Validates the reference format guard.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            Integer().foreign("companies")
        with self.assertRaises(ValueError):
            Integer().foreign("a.b.c")
