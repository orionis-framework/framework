from orionis.orm.schema.types.column_type import ColumnType
from orionis.orm.schema.types.strict_varchar import StrictVarChar
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options

class TestStrictVarCharOptions(TestCase):
    """Verify StrictVarChar constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            Verify fresh declarations and independent configured metadata.
        """
        default = StrictVarChar()
        assert_column_options(
            self,
            default,
            ColumnType.VARCHAR,
            length=255,
            collation=None,
        )
        configured = StrictVarChar(length=80, collation="binary")
        assert_column_options(
            self,
            configured,
            ColumnType.VARCHAR,
            length=80,
            collation="binary",
        )
        self.assertIsNot(configured, default)
