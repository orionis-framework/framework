# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Verify ORM schema unicode text behavior."""

from orionis.orm.schema.types.column_type import ColumnType
from orionis.orm.schema.types.unicode_text import UnicodeText
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options


class TestUnicodeTextOptions(TestCase):
    """Verify UnicodeText constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            No return value.
        """
        default = UnicodeText()
        assert_column_options(
            self,
            default,
            ColumnType.UNICODE_TEXT,
            length=None,
            collation=None,
        )
        configured = UnicodeText(length=80, collation="binary")
        assert_column_options(
            self,
            configured,
            ColumnType.UNICODE_TEXT,
            length=80,
            collation="binary",
        )
        self.assertIsNot(configured, default)
