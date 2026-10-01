from orionis.orm.schema.types import StrictDecimal, StrictVarChar, String
from orionis.orm.schema.types._constants import (
    DEFAULT_DECIMAL_PRECISION,
    DEFAULT_DECIMAL_SCALE,
    DEFAULT_STRING_LENGTH,
)
from orionis.test import TestCase

class TestColumnDefaults(TestCase):
    """Verify shared defaults remain valid and consistent across declarations."""

    def testSharedDefaultsDescribeValidStringAndDecimalShapes(self) -> None:
        """Use shared defaults for both generic and strict type declarations.

        Returns
        -------
        None
            Verify positive lengths and a valid shared decimal precision and scale.
        """
        self.assertGreater(DEFAULT_STRING_LENGTH, 0)
        self.assertEqual(String().length, DEFAULT_STRING_LENGTH)
        self.assertEqual(StrictVarChar().length, DEFAULT_STRING_LENGTH)
        self.assertGreater(DEFAULT_DECIMAL_PRECISION, 0)
        self.assertGreaterEqual(DEFAULT_DECIMAL_SCALE, 0)
        self.assertLessEqual(DEFAULT_DECIMAL_SCALE, DEFAULT_DECIMAL_PRECISION)
        decimal = StrictDecimal()
        self.assertEqual(decimal.precision, DEFAULT_DECIMAL_PRECISION)
        self.assertEqual(decimal.scale, DEFAULT_DECIMAL_SCALE)
