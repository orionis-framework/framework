from orionis.orm.schema.types.column_type import ColumnType
from orionis.orm.schema.types.strict_small_int import StrictSmallInt
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options

class TestStrictSmallIntOptions(TestCase):
    """Verify StrictSmallInt constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            Verify fresh declarations and independent configured metadata.
        """
        default = StrictSmallInt()
        assert_column_options(
            self,
            default,
            ColumnType.SMALLINT,
        )
        configured = StrictSmallInt().primary().autoIncrement().default(None)
        self.assertTrue(configured.is_primary)
        self.assertTrue(configured.is_auto_increment)
        self.assertTrue(configured.hasDefault())
        self.assertFalse(default.is_primary)
        self.assertFalse(default.hasDefault())
