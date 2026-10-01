from orionis.orm.schema.types.column_type import ColumnType
from orionis.orm.schema.types.strict_real import StrictReal
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options

class TestStrictRealOptions(TestCase):
    """Verify StrictReal constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            Verify fresh declarations and independent configured metadata.
        """
        default = StrictReal()
        assert_column_options(
            self,
            default,
            ColumnType.REAL,
            precision=None,
            as_decimal=False,
            decimal_return_scale=None,
        )
        configured = StrictReal(precision=24, asdecimal=True, decimal_return_scale=5)
        assert_column_options(
            self,
            configured,
            ColumnType.REAL,
            precision=24,
            as_decimal=True,
            decimal_return_scale=5,
        )
        self.assertIsNot(configured, default)
