from orionis.orm.schema.types.column_type import ColumnType
from orionis.orm.schema.types.interval import Interval
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options

class TestIntervalOptions(TestCase):
    """Verify Interval constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            Verify fresh declarations and independent configured metadata.
        """
        default = Interval()
        assert_column_options(
            self,
            default,
            ColumnType.INTERVAL,
            native=True,
            second_precision=None,
            day_precision=None,
        )
        configured = Interval(native=False, second_precision=6, day_precision=3)
        assert_column_options(
            self,
            configured,
            ColumnType.INTERVAL,
            native=False,
            second_precision=6,
            day_precision=3,
        )
        self.assertIsNot(configured, default)
