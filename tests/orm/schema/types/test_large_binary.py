from orionis.orm.schema.types.column_type import ColumnType
from orionis.orm.schema.types.large_binary import LargeBinary
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options

class TestLargeBinaryOptions(TestCase):
    """Verify LargeBinary constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            Verify fresh declarations and independent configured metadata.
        """
        default = LargeBinary()
        assert_column_options(
            self,
            default,
            ColumnType.LARGE_BINARY,
            length=None,
        )
        configured = LargeBinary(length=64)
        assert_column_options(
            self,
            configured,
            ColumnType.LARGE_BINARY,
            length=64,
        )
        self.assertIsNot(configured, default)

    def testRejectsNonPositiveAndNonIntegerLengths(self) -> None:
        """Reject invalid binary lengths while allowing an unspecified length.

        Returns
        -------
        None
            Verify the constructor's optional positive-integer length contract.
        """
        self.assertIsNone(LargeBinary(None).length)
        for length in (0, -1, 1.5, "10"):
            with self.assertRaises(ValueError):
                LargeBinary(length)  # type: ignore[arg-type]
