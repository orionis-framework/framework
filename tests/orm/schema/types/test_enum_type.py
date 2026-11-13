# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Verify ORM schema enum type behavior."""

from __future__ import annotations
from orionis.orm.schema.types import (
    ColumnType,
    Enum,
)
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options


class TestEnumOptions(TestCase):
    """Verify Enum constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            No return value.
        """
        default = Enum("draft", "published")
        assert_column_options(
            self,
            default,
            ColumnType.ENUM,
            enum_values=("draft", "published"),
            native_enum=True,
            create_constraint=False,
        )
        configured = Enum(
            "queued",
            "ready",
            name="states",
            create_constraint=True,
            native_enum=False,
            length=20,
            validate_strings=True,
        )
        assert_column_options(
            self,
            configured,
            ColumnType.ENUM,
            enum_values=("queued", "ready"),
            enum_name="states",
            create_constraint=True,
            native_enum=False,
            length=20,
            validate_strings=True,
        )
        self.assertIsNot(configured, default)

    def testRejectsEmptyAndNonStringEnumValues(self) -> None:
        """Reject enum entries that cannot describe a non-empty string value.

        Returns
        -------
        None
            No return value.
        """
        for values in ((), ("",), ("valid", ""), ("valid", None), (7,)):
            with self.assertRaises(ValueError):
                Enum(*values)  # type: ignore[arg-type]
