from orionis.orm.schema.types.column_type import ColumnType
from orionis.orm.schema.types.unicode import Unicode
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options

class TestUnicodeOptions(TestCase):
    """Verify Unicode constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            Verify fresh declarations and independent configured metadata.
        """
        default = Unicode()
        assert_column_options(
            self,
            default,
            ColumnType.UNICODE,
            length=None,
            collation=None,
        )
        configured = Unicode(length=80, collation="binary")
        assert_column_options(
            self,
            configured,
            ColumnType.UNICODE,
            length=80,
            collation="binary",
        )
        self.assertIsNot(configured, default)
