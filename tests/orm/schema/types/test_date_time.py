from orionis.orm.schema.types.column_type import ColumnType
from orionis.orm.schema.types.date_time import DateTime
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options

class TestDateTimeOptions(TestCase):
    """Verify DateTime constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            Verify fresh declarations and independent configured metadata.
        """
        default = DateTime()
        assert_column_options(
            self,
            default,
            ColumnType.DATETIME,
            timezone=False,
        )
        configured = DateTime(timezone=True)
        assert_column_options(
            self,
            configured,
            ColumnType.DATETIME,
            timezone=True,
        )
        self.assertIsNot(configured, default)
