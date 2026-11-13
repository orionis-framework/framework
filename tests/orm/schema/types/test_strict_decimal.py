# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Verify ORM schema strict decimal behavior."""

from __future__ import annotations
from orionis.orm.schema.types import (
    StrictDecimal,
)
from orionis.orm.schema.types.column_type import ColumnType
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options


class TestStrictDecimalOptions(TestCase):
    """Verify StrictDecimal constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            No return value.
        """
        default = StrictDecimal()
        assert_column_options(
            self,
            default,
            ColumnType.DECIMAL,
            precision=10,
            scale=2,
            as_decimal=True,
        )
        configured = StrictDecimal(
            precision=14,
            scale=3,
            decimal_return_scale=5,
            asdecimal=False,
        )
        assert_column_options(
            self,
            configured,
            ColumnType.DECIMAL,
            precision=14,
            scale=3,
            decimal_return_scale=5,
            as_decimal=False,
        )
        self.assertIsNot(configured, default)

    def testSupportsUnspecifiedShapeAndRejectsInvalidPairs(self) -> None:
        """Allow an unspecified shape while rejecting inconsistent pairs.

        Returns
        -------
        None
            No return value.
        """
        self.assertIsNone(StrictDecimal(None, None).precision)
        shapes = (
            (None, 2),
            (4, None),
            (0, 0),
            (-1, 0),
            (2, -1),
            (2, 3),
            (2, 5),
            (2.5, 1),
            (4, "1"),
        )
        for precision, scale in shapes:
            with self.assertRaises(ValueError):
                StrictDecimal(precision, scale)  # type: ignore[arg-type]
