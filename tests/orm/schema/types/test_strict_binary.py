# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Verify ORM schema strict binary behavior."""

from orionis.orm.schema.types.column_type import ColumnType
from orionis.orm.schema.types.strict_binary import StrictBinary
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options


class TestStrictBinaryOptions(TestCase):
    """Verify StrictBinary constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            No return value.
        """
        default = StrictBinary()
        assert_column_options(
            self,
            default,
            ColumnType.BINARY,
            length=None,
        )
        configured = StrictBinary(length=64)
        assert_column_options(
            self,
            configured,
            ColumnType.BINARY,
            length=64,
        )
        self.assertIsNot(configured, default)
