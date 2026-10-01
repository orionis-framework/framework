from orionis.orm.schema.types.column_type import ColumnType
from orionis.orm.schema.types.schema_type import SchemaType
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options

class TestSchemaTypeOptions(TestCase):
    """Verify SchemaType constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            Verify fresh declarations and independent configured metadata.
        """
        default = SchemaType()
        assert_column_options(
            self,
            default,
            ColumnType.SCHEMA_TYPE,
            constraint_name=None,
        )
        configured = SchemaType(name="named_type")
        assert_column_options(
            self,
            configured,
            ColumnType.SCHEMA_TYPE,
            constraint_name="named_type",
        )
        self.assertIsNot(configured, default)
