from orionis.orm.schema.types.big_integer import BigInteger
from orionis.orm.schema.types.column_type import ColumnType
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options

class TestBigIntegerOptions(TestCase):
    """Verify BigInteger constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            Verify fresh declarations and independent configured metadata.
        """
        default = BigInteger()
        assert_column_options(
            self,
            default,
            ColumnType.BIG_INTEGER,
        )
        configured = BigInteger().primary().autoIncrement().default(None)
        self.assertTrue(configured.is_primary)
        self.assertTrue(configured.is_auto_increment)
        self.assertTrue(configured.hasDefault())
        self.assertFalse(default.is_primary)
        self.assertFalse(default.hasDefault())
