from __future__ import annotations
from orionis.orm.schema.types import (
    StrictDecimal,
)
from orionis.orm.schema.types.column_type import ColumnType
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options

class TestStrictDecimal(TestCase):
    def testDecimalCarriesPrecisionAndScale(self) -> None:
        """Store precision and scale on decimal columns.

        Validates the decimal shape parameters.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        column = StrictDecimal(12, 4)
        self.assertEqual(column.precision, 12)
        self.assertEqual(column.scale, 4)

    def testDecimalRejectsInconsistentShape(self) -> None:
        """Raise ValueError when the scale exceeds the precision.

        Validates the decimal shape guard.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            StrictDecimal(2, 5)

class TestStrictDecimalOptions(TestCase):
    """Verify StrictDecimal constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            Verify fresh declarations and independent configured metadata.
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
            Verify all precision and scale validation branches.
        """
        self.assertIsNone(StrictDecimal(None, None).precision)
        shapes = (
            (None, 2),
            (4, None),
            (0, 0),
            (-1, 0),
            (2, -1),
            (2, 3),
            (2.5, 1),
            (4, "1"),
        )
        for precision, scale in shapes:
            with self.assertRaises(ValueError):
                StrictDecimal(precision, scale)  # type: ignore[arg-type]
