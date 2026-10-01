from orionis.orm.schema.types.column_type import ColumnType
from orionis.orm.schema.types.numeric import Numeric
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options

class TestNumericOptions(TestCase):
    """Verify Numeric constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            Verify fresh declarations and independent configured metadata.
        """
        default = Numeric()
        assert_column_options(
            self,
            default,
            ColumnType.NUMERIC,
            precision=None,
            scale=None,
            as_decimal=True,
        )
        configured = Numeric(
            precision=14,
            scale=3,
            decimal_return_scale=5,
            asdecimal=False,
        )
        assert_column_options(
            self,
            configured,
            ColumnType.NUMERIC,
            precision=14,
            scale=3,
            decimal_return_scale=5,
            as_decimal=False,
        )
        self.assertIsNot(configured, default)

    def testRejectsInvalidPrecisionAndScalePairs(self) -> None:
        """Reject incomplete, non-integer, and inconsistent numeric shapes.

        Returns
        -------
        None
            Verify constructor guards before column options are created.
        """
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
                Numeric(precision, scale)  # type: ignore[arg-type]
        self.assertEqual(Numeric(4, 0).scale, 0)
