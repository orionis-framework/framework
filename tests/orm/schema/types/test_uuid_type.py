from orionis.orm.schema.types.column_type import ColumnType
from orionis.orm.schema.types.uuid_type import Uuid
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options

class TestUuidOptions(TestCase):
    """Verify Uuid constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            Verify fresh declarations and independent configured metadata.
        """
        default = Uuid()
        assert_column_options(
            self,
            default,
            ColumnType.UUID,
            as_uuid=True,
            native_uuid=True,
        )
        configured = Uuid(as_uuid=False, native_uuid=False)
        assert_column_options(
            self,
            configured,
            ColumnType.UUID,
            as_uuid=False,
            native_uuid=False,
        )
        self.assertIsNot(configured, default)
