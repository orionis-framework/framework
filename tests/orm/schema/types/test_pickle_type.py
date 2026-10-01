from orionis.orm.schema.types.column_type import ColumnType
from orionis.orm.schema.types.pickle_type import PickleType
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options

class TestPickleTypeOptions(TestCase):
    """Verify PickleType constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            Verify fresh declarations and independent configured metadata.
        """
        marker = object()
        default = PickleType()
        assert_column_options(
            self,
            default,
            ColumnType.PICKLE_TYPE,
            protocol=5,
            pickler=None,
            impl=None,
        )
        configured = PickleType(protocol=4, pickler=marker, impl=marker)
        assert_column_options(
            self,
            configured,
            ColumnType.PICKLE_TYPE,
            protocol=4,
            pickler=marker,
            impl=marker,
        )
        self.assertIsNot(configured, default)
