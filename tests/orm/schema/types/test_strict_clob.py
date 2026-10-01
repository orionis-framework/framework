from orionis.orm.schema.types.column_type import ColumnType
from orionis.orm.schema.types.strict_clob import StrictClob
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options

class TestStrictClobOptions(TestCase):
    """Verify StrictClob constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            Verify fresh declarations and independent configured metadata.
        """
        default = StrictClob()
        assert_column_options(
            self,
            default,
            ColumnType.CLOB,
            length=None,
            collation=None,
        )
        configured = StrictClob(length=80, collation="binary")
        assert_column_options(
            self,
            configured,
            ColumnType.CLOB,
            length=80,
            collation="binary",
        )
        self.assertIsNot(configured, default)
