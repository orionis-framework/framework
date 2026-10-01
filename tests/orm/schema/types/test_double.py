from orionis.orm.schema.types.column_type import ColumnType
from orionis.orm.schema.types.double import Double
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options

class TestDoubleOptions(TestCase):
    """Verify Double constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            Verify fresh declarations and independent configured metadata.
        """
        default = Double()
        assert_column_options(
            self,
            default,
            ColumnType.DOUBLE,
            precision=None,
            as_decimal=False,
            decimal_return_scale=None,
        )
        configured = Double(precision=24, asdecimal=True, decimal_return_scale=5)
        assert_column_options(
            self,
            configured,
            ColumnType.DOUBLE,
            precision=24,
            as_decimal=True,
            decimal_return_scale=5,
        )
        self.assertIsNot(configured, default)
