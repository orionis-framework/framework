from orionis.orm.schema.types.column_type import ColumnType
from orionis.orm.schema.types.strict_nchar import StrictNChar
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options

class TestStrictNCharOptions(TestCase):
    """Verify StrictNChar constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            Verify fresh declarations and independent configured metadata.
        """
        default = StrictNChar()
        assert_column_options(
            self,
            default,
            ColumnType.NCHAR,
            length=None,
            collation=None,
        )
        configured = StrictNChar(length=80, collation="binary")
        assert_column_options(
            self,
            configured,
            ColumnType.NCHAR,
            length=80,
            collation="binary",
        )
        self.assertIsNot(configured, default)
