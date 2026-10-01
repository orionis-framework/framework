from orionis.orm.schema.types.boolean import Boolean
from orionis.orm.schema.types.column_type import ColumnType
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options

class TestBooleanOptions(TestCase):
    """Verify Boolean constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            Verify fresh declarations and independent configured metadata.
        """
        default = Boolean()
        assert_column_options(
            self,
            default,
            ColumnType.BOOLEAN,
            create_constraint=False,
            constraint_name=None,
        )
        configured = Boolean(create_constraint=True, name="active_check")
        assert_column_options(
            self,
            configured,
            ColumnType.BOOLEAN,
            create_constraint=True,
            constraint_name="active_check",
        )
        self.assertIsNot(configured, default)
