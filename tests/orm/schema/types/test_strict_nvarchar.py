# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Verify ORM schema strict nvarchar behavior."""

from orionis.orm.schema.types.column_type import ColumnType
from orionis.orm.schema.types.strict_nvarchar import StrictNVarChar
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options


class TestStrictNVarCharOptions(TestCase):
    """Verify StrictNVarChar constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            No return value.
        """
        default = StrictNVarChar()
        assert_column_options(
            self,
            default,
            ColumnType.NVARCHAR,
            length=None,
            collation=None,
        )
        configured = StrictNVarChar(length=80, collation="binary")
        assert_column_options(
            self,
            configured,
            ColumnType.NVARCHAR,
            length=80,
            collation="binary",
        )
        self.assertIsNot(configured, default)
