from orionis.orm.schema.types.column_type import ColumnType
from orionis.orm.schema.types.strict_double_precision import StrictDoublePrecision
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options

class TestStrictDoublePrecisionOptions(TestCase):
    """Verify StrictDoublePrecision constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            Verify fresh declarations and independent configured metadata.
        """
        default = StrictDoublePrecision()
        assert_column_options(
            self,
            default,
            ColumnType.DOUBLE_PRECISION,
            precision=None,
            as_decimal=False,
            decimal_return_scale=None,
        )
        configured = StrictDoublePrecision(
            precision=24,
            asdecimal=True,
            decimal_return_scale=5,
        )
        assert_column_options(
            self,
            configured,
            ColumnType.DOUBLE_PRECISION,
            precision=24,
            as_decimal=True,
            decimal_return_scale=5,
        )
        self.assertIsNot(configured, default)
