# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Verify ORM schema strict timestamp behavior."""

from orionis.orm.schema.types.column_type import ColumnType
from orionis.orm.schema.types.strict_timestamp import StrictTimestamp
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options


class TestStrictTimestampOptions(TestCase):
    """Verify StrictTimestamp constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            No return value.
        """
        default = StrictTimestamp()
        assert_column_options(
            self,
            default,
            ColumnType.TIMESTAMP,
            timezone=False,
        )
        configured = StrictTimestamp(timezone=True)
        assert_column_options(
            self,
            configured,
            ColumnType.TIMESTAMP,
            timezone=True,
        )
        self.assertIsNot(configured, default)
