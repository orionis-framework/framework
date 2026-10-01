from orionis.orm.schema.types.column_type import ColumnType
from orionis.orm.schema.types.strict_var_binary import StrictVarBinary
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options

class TestStrictVarBinaryOptions(TestCase):
    """Verify StrictVarBinary constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            Verify fresh declarations and independent configured metadata.
        """
        default = StrictVarBinary()
        assert_column_options(
            self,
            default,
            ColumnType.VARBINARY,
            length=None,
        )
        configured = StrictVarBinary(length=64)
        assert_column_options(
            self,
            configured,
            ColumnType.VARBINARY,
            length=64,
        )
        self.assertIsNot(configured, default)
