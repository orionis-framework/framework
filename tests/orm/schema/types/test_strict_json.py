from orionis.orm.schema.types.column_type import ColumnType
from orionis.orm.schema.types.strict_json import StrictJson
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options

class TestStrictJsonOptions(TestCase):
    """Verify StrictJson constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            Verify fresh declarations and independent configured metadata.
        """
        default = StrictJson()
        assert_column_options(
            self,
            default,
            ColumnType.JSON,
            none_as_null=False,
        )
        configured = StrictJson(none_as_null=True)
        assert_column_options(
            self,
            configured,
            ColumnType.JSON,
            none_as_null=True,
        )
        self.assertIsNot(configured, default)
