# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Verify ORM schema match type behavior."""

from orionis.orm.schema.types.column_type import ColumnType
from orionis.orm.schema.types.match_type import MatchType
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options


class TestMatchTypeOptions(TestCase):
    """Verify MatchType constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            No return value.
        """
        default = MatchType()
        assert_column_options(
            self,
            default,
            ColumnType.MATCH_TYPE,
        )
        configured = MatchType().primary().autoIncrement().default(None)
        self.assertTrue(configured.is_primary)
        self.assertTrue(configured.is_auto_increment)
        self.assertTrue(configured.hasDefault())
        self.assertFalse(default.is_primary)
        self.assertFalse(default.hasDefault())
