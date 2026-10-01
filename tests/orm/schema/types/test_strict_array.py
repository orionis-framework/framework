from orionis.orm.schema.types.column_type import ColumnType
from orionis.orm.schema.types.integer import Integer
from orionis.orm.schema.types.strict_array import StrictArray
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options

class TestStrictArrayOptions(TestCase):
    """Verify StrictArray constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            Verify fresh declarations and independent configured metadata.
        """
        item = Integer()
        default = StrictArray(item)
        assert_column_options(
            self,
            default,
            ColumnType.ARRAY,
            item_type=item,
            as_tuple=False,
            dimensions=None,
            zero_indexes=False,
        )
        configured = StrictArray(item, as_tuple=True, dimensions=2, zero_indexes=True)
        assert_column_options(
            self,
            configured,
            ColumnType.ARRAY,
            item_type=item,
            as_tuple=True,
            dimensions=2,
            zero_indexes=True,
        )
        self.assertIsNot(configured, default)
