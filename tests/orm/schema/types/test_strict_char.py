from orionis.orm.schema.types.column_type import ColumnType
from orionis.orm.schema.types.strict_char import StrictChar
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options

class TestStrictCharOptions(TestCase):
    """Verify StrictChar constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            Verify fresh declarations and independent configured metadata.
        """
        default = StrictChar()
        assert_column_options(
            self,
            default,
            ColumnType.CHAR,
            length=None,
            collation=None,
        )
        configured = StrictChar(length=80, collation="binary")
        assert_column_options(
            self,
            configured,
            ColumnType.CHAR,
            length=80,
            collation="binary",
        )
        self.assertIsNot(configured, default)
