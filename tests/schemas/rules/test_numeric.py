from decimal import Decimal
from types import SimpleNamespace
from orionis.schemas.rules.between import Between
from orionis.schemas.rules.decimal_places import DecimalPlaces
from orionis.schemas.rules.different import Different
from orionis.schemas.rules.greater_than_or_equal_field import GreaterThanOrEqualField
from orionis.schemas.rules.integer import Integer
from orionis.schemas.rules.less_than_or_equal_field import LessThanOrEqualField
from orionis.schemas.rules.max_digits import MaxDigits
from orionis.test import TestCase

# Shared owner instance for rules that never inspect sibling fields.
_OWNER = object()

class TestBetween(TestCase):

    def testNumbersAreComparedByMagnitude(self) -> None:
        """
        Return True when a number falls inside the inclusive range.

        Validates that both bounds are part of the accepted set.
        """
        rule = Between(1, 10)
        for value in (1, 5, 10, 2.5):
            self.assertTrue(rule.enforce("qty", value, _OWNER))

    def testNumbersOutsideRangeFail(self) -> None:
        """
        Return False when a number falls outside the inclusive range.

        Validates that values on either side of the bounds are rejected.
        """
        rule = Between(1, 10)
        self.assertFalse(rule.enforce("qty", 0, _OWNER))
        self.assertFalse(rule.enforce("qty", 11, _OWNER))

    def testStringsAndCollectionsAreComparedByLength(self) -> None:
        """
        Return True when a string or collection length fits the range.

        Validates the size semantics applied to sized values.
        """
        rule = Between(2, 4)
        self.assertTrue(rule.enforce("tag", "abc", _OWNER))
        self.assertTrue(rule.enforce("tag", [1, 2], _OWNER))
        self.assertFalse(rule.enforce("tag", "a", _OWNER))
        self.assertFalse(rule.enforce("tag", [1, 2, 3, 4, 5], _OWNER))

    def testUnmeasurableValuePasses(self) -> None:
        """
        Return True when the value carries no comparable size.

        Validates that type reporting is delegated to the type layer.
        """
        rule = Between(1, 10)
        self.assertTrue(rule.enforce("qty", None, _OWNER))
        self.assertTrue(rule.enforce("qty", True, _OWNER))

    def testImpossibleRangeRaises(self) -> None:
        """
        Raise ValueError when the minimum exceeds the maximum.

        Validates that an empty range is rejected at construction time.
        """
        with self.assertRaises(ValueError):
            Between(10, 1)

class TestGreaterThanOrEqualField(TestCase):

    def testValueAboveOrEqualSiblingPasses(self) -> None:
        """
        Return True when the value reaches the compared field.

        Validates that the bound is inclusive.
        """
        rule = GreaterThanOrEqualField("minimum")
        instance = SimpleNamespace(minimum=5)
        self.assertTrue(rule.enforce("maximum", 5, instance))
        self.assertTrue(rule.enforce("maximum", 9, instance))

    def testValueBelowSiblingFails(self) -> None:
        """
        Return False when the value is under the compared field.

        Validates that the sibling value acts as a lower bound.
        """
        rule = GreaterThanOrEqualField("minimum")
        self.assertFalse(rule.enforce("maximum", 1, SimpleNamespace(minimum=5)))

    def testLengthSemanticsApplyToStrings(self) -> None:
        """
        Compare strings by length instead of lexicographic order.

        Validates that both operands share the same size semantics.
        """
        rule = GreaterThanOrEqualField("short")
        instance = SimpleNamespace(short="ab")
        self.assertTrue(rule.enforce("long", "abcd", instance))
        self.assertFalse(rule.enforce("long", "a", instance))

    def testMissingSiblingPasses(self) -> None:
        """
        Return True when the compared field is absent or unmeasurable.

        Validates that type reporting is delegated to the type layer.
        """
        rule = GreaterThanOrEqualField("minimum")
        self.assertTrue(rule.enforce("maximum", 1, SimpleNamespace()))
        self.assertTrue(rule.enforce("maximum", None, SimpleNamespace(minimum=5)))

class TestLessThanOrEqualField(TestCase):

    def testValueBelowOrEqualSiblingPasses(self) -> None:
        """
        Return True when the value stays under the compared field.

        Validates that the bound is inclusive.
        """
        rule = LessThanOrEqualField("maximum")
        instance = SimpleNamespace(maximum=5)
        self.assertTrue(rule.enforce("minimum", 5, instance))
        self.assertTrue(rule.enforce("minimum", 1, instance))

    def testValueAboveSiblingFails(self) -> None:
        """
        Return False when the value exceeds the compared field.

        Validates that the sibling value acts as an upper bound.
        """
        rule = LessThanOrEqualField("maximum")
        self.assertFalse(rule.enforce("minimum", 9, SimpleNamespace(maximum=5)))

    def testMissingSiblingPasses(self) -> None:
        """
        Return True when the compared field is absent or unmeasurable.

        Validates that type reporting is delegated to the type layer.
        """
        rule = LessThanOrEqualField("maximum")
        self.assertTrue(rule.enforce("minimum", 1, SimpleNamespace()))

class TestDecimalPlaces(TestCase):

    def testExactNumberOfPlacesPasses(self) -> None:
        """
        Return True when the value carries exactly the required places.

        Validates that trailing zeros are preserved by the textual form.
        """
        rule = DecimalPlaces(2)
        self.assertTrue(rule.enforce("price", "10.50", _OWNER))
        self.assertTrue(rule.enforce("price", Decimal("0.01"), _OWNER))

    def testWrongNumberOfPlacesFails(self) -> None:
        """
        Return False when the number of decimal places differs.

        Validates that both fewer and more places are rejected.
        """
        rule = DecimalPlaces(2)
        self.assertFalse(rule.enforce("price", "10.5", _OWNER))
        self.assertFalse(rule.enforce("price", "10.500", _OWNER))

    def testRangeAcceptsEveryCountInside(self) -> None:
        """
        Return True for any number of places within the inclusive range.

        Validates that supplying a maximum widens the accepted set.
        """
        rule = DecimalPlaces(2, 4)
        for value in ("1.00", "1.000", "1.0000"):
            self.assertTrue(rule.enforce("price", value, _OWNER))
        self.assertFalse(rule.enforce("price", "1.0", _OWNER))

    def testIntegerValueHasNoPlaces(self) -> None:
        """
        Return True for whole numbers only when zero places are required.

        Validates that integers report no decimal places.
        """
        self.assertTrue(DecimalPlaces(0).enforce("price", 10, _OWNER))
        self.assertFalse(DecimalPlaces(2).enforce("price", 10, _OWNER))

    def testNonNumericValuesFail(self) -> None:
        """
        Return False when the value is not numeric.

        Validates that booleans, free text and unrelated types are
        rejected instead of silently passing.
        """
        rule = DecimalPlaces(2)
        for value in (True, "abc", None, [1]):
            self.assertFalse(rule.enforce("price", value, _OWNER))

    def testInvalidBoundsRaise(self) -> None:
        """
        Raise ValueError when the bounds are negative or unordered.

        Validates the configuration check performed at construction time.
        """
        with self.assertRaises(ValueError):
            DecimalPlaces(-1)
        with self.assertRaises(ValueError):
            DecimalPlaces(4, 2)

class TestInteger(TestCase):

    def testWholeNumbersPass(self) -> None:
        """
        Return True for integers and for floats without a fraction.

        Validates the accepted numeric forms.
        """
        rule = Integer()
        for value in (0, 42, -7, 5.0):
            self.assertTrue(rule.enforce("qty", value, _OWNER))

    def testNumericStringsPass(self) -> None:
        """
        Return True for optionally signed sequences of digits.

        Validates that textual integers are accepted.
        """
        rule = Integer()
        for value in ("42", "-42", "+42"):
            self.assertTrue(rule.enforce("qty", value, _OWNER))

    def testFractionalAndForeignValuesFail(self) -> None:
        """
        Return False when the value is not a whole number.

        Validates that fractions, booleans and free text are rejected.
        """
        rule = Integer()
        for value in (5.5, "4.2", "abc", "", True, None, [1]):
            self.assertFalse(rule.enforce("qty", value, _OWNER))

class TestMaxDigits(TestCase):

    def testValuesWithinLimitPass(self) -> None:
        """
        Return True when the digit count stays within the limit.

        Validates that the sign is excluded from the count.
        """
        rule = MaxDigits(5)
        self.assertTrue(rule.enforce("code", 12345, _OWNER))
        self.assertTrue(rule.enforce("code", -1234, _OWNER))
        self.assertTrue(rule.enforce("code", "+123", _OWNER))

    def testValuesAboveLimitFail(self) -> None:
        """
        Return False when the digit count exceeds the limit.

        Validates that longer numbers are rejected in both forms.
        """
        rule = MaxDigits(4)
        self.assertFalse(rule.enforce("code", 12345, _OWNER))
        self.assertFalse(rule.enforce("code", "-12345", _OWNER))

    def testForeignValuesFail(self) -> None:
        """
        Return False when the value is not an integer or digit string.

        Validates that booleans, floats and empty text are rejected.
        """
        rule = MaxDigits(5)
        for value in (True, 1.5, "", None):
            self.assertFalse(rule.enforce("code", value, _OWNER))

    def testNonPositiveLimitRaises(self) -> None:
        """
        Raise ValueError when the configured limit is below one.

        Validates that an unsatisfiable limit is rejected early.
        """
        with self.assertRaises(ValueError):
            MaxDigits(0)

class TestDifferent(TestCase):

    def testDistinctValuePasses(self) -> None:
        """
        Return True when the value differs from every forbidden value.

        Validates the success path across several forbidden entries.
        """
        rule = Different(1, 2, 3)
        self.assertTrue(rule.enforce("qty", 4, _OWNER))

    def testForbiddenValueFails(self) -> None:
        """
        Return False when the value equals one of the forbidden values.

        Validates that a single match rejects the value.
        """
        rule = Different("draft", "archived")
        self.assertFalse(rule.enforce("status", "draft", _OWNER))
        self.assertFalse(rule.enforce("status", "archived", _OWNER))

    def testUnhashableValuesAreSupported(self) -> None:
        """
        Compare unhashable values through equality instead of membership.

        Validates that lists and dicts can be used as forbidden values.
        """
        rule = Different([1, 2])
        self.assertFalse(rule.enforce("items", [1, 2], _OWNER))
        self.assertTrue(rule.enforce("items", [1, 3], _OWNER))

    def testEmptyConfigurationRaises(self) -> None:
        """
        Raise ValueError when no forbidden value is supplied.

        Validates that the rule refuses a configuration with no effect.
        """
        with self.assertRaises(ValueError):
            Different()
