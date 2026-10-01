from orionis.orm.schema.types.column_type import ColumnType
from orionis.orm.schema.types.text import Text
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options

class TestTextOptions(TestCase):
    """Verify Text constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            Verify fresh declarations and independent configured metadata.
        """
        default = Text()
        assert_column_options(
            self,
            default,
            ColumnType.TEXT,
            length=None,
            collation=None,
        )
        configured = Text(length=80, collation="binary")
        assert_column_options(
            self,
            configured,
            ColumnType.TEXT,
            length=80,
            collation="binary",
        )
        self.assertIsNot(configured, default)
