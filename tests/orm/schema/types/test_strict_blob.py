from orionis.orm.schema.types.column_type import ColumnType
from orionis.orm.schema.types.strict_blob import StrictBlob
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options

class TestStrictBlobOptions(TestCase):
    """Verify StrictBlob constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            Verify fresh declarations and independent configured metadata.
        """
        default = StrictBlob()
        assert_column_options(
            self,
            default,
            ColumnType.BLOB,
            length=None,
        )
        configured = StrictBlob(length=64)
        assert_column_options(
            self,
            configured,
            ColumnType.BLOB,
            length=64,
        )
        self.assertIsNot(configured, default)
