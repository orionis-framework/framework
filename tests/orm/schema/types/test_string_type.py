# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Verify ORM schema string type behavior."""

from __future__ import annotations
from orionis.orm.schema.types import (
    String,
)
from orionis.orm.schema.types.column_type import ColumnType
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options


class TestStringOptions(TestCase):
    """Verify String constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            No return value.
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
            No return value.
        """
        self.assertIsNone(String(None).length)
        for length in (0, -1, 1.5, "10"):
            with self.assertRaises(ValueError):
                String(length)  # type: ignore[arg-type]
