from __future__ import annotations
from importlib import import_module
from orionis.orm.schema import types as types_module
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.types import (
    ColumnType,
    Enum,
    Integer,
    String,
)
from orionis.test import TestCase

def assert_column_options(
    test_case: TestCase,
    column: ColumnDefinition,
    expected_type: ColumnType,
    **expected_options: object,
) -> None:
    """Verify a typed column's compiler-facing type and constructor options.

    Parameters
    ----------
    test_case : TestCase
        Test case owning the assertions.
    column : ColumnDefinition
        Fresh typed column declaration to inspect.
    expected_type : ColumnType
        Logical type expected by the SQL compiler.
    **expected_options : object
        Expected values of type-specific column options.

    Returns
    -------
    None
        Verify metadata, initial constraint state, and declared option values.
    """
    test_case.assertIsInstance(column, ColumnDefinition)
    test_case.assertIs(column.column_type, expected_type)
    test_case.assertFalse(column.hasDefault())
    test_case.assertFalse(column.is_primary)
    test_case.assertFalse(column.is_nullable)
    test_case.assertFalse(hasattr(column, "__dict__"))
    for name, expected in expected_options.items():
        test_case.assertEqual(getattr(column, name), expected, name)

class TestColumnTypePackage(TestCase):
    """Verify public schema type exports resolve to their owning modules."""

    def testExportsHaveUniqueNamesAndResolveToTheirDefinitions(self) -> None:
        """Resolve every public column type to its implementation class.

        Returns
        -------
        None
            Verify unique exports and identity with each defining module.
        """
        names = types_module.__all__
        self.assertEqual(len(names), len(set(names)))
        for name in names:
            exported = getattr(types_module, name)
            defining = import_module(exported.__module__)
            self.assertIs(exported, getattr(defining, name), name)

class TestTypedColumnLayout(TestCase):
    def testTypedColumnsHaveNoInstanceDictionary(self) -> None:
        """Keep typed column declarations inside their declared slots.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for column in (Integer(), String(), Enum("active", "inactive")):
            with self.subTest(column=type(column).__name__):
                self.assertFalse(hasattr(column, "__dict__"))
                with self.assertRaises(AttributeError):
                    column.unknown_option = True
