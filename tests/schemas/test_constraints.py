from orionis.schemas.constraints import (
    GreaterThan,
    GreaterThanOrEqual,
    LessThan,
    LessThanOrEqual,
    MaxLength,
    MinLength,
    MultipleOf,
    Pattern,
    StrongPassword,
    TimezoneAware,
    TimezoneNaive,
)
from orionis.schemas.meta.constraint import ConstraintMetadata
from orionis.schemas.meta.validation import ValidationMetadata
from orionis.test import TestCase

class TestConstraints(TestCase):

    # ------------------------------------------------------------------ GreaterThan

    def testGreaterThanStoresValue(self) -> None:
        """Instantiate GreaterThan and verify the value attribute.

        Validates that the constructor stores the provided numeric lower
        bound on the ``value`` attribute.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = GreaterThan(10)
        self.assertEqual(c.value, 10)

    def testGreaterThanDefaultMessageIsNone(self) -> None:
        """Confirm the default message of GreaterThan is None.

        Validates that when no message keyword argument is supplied the
        message attribute defaults to None.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = GreaterThan(5)
        self.assertIsNone(c.message)

    def testGreaterThanAcceptsCustomMessage(self) -> None:
        """Accept a custom message keyword argument on GreaterThan.

        Validates that the message attribute is populated when an
        explicit message string is provided.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = GreaterThan(0, message="Must be positive.")
        self.assertEqual(c.message, "Must be positive.")

    def testGreaterThanIsConstraintMetadata(self) -> None:
        """Confirm GreaterThan inherits from ConstraintMetadata.

        Validates the class hierarchy so the framework's isinstance
        checks classify it correctly.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsInstance(GreaterThan(1), ConstraintMetadata)
        self.assertIsInstance(GreaterThan(1), ValidationMetadata)

    def testGreaterThanAcceptsFloat(self) -> None:
        """Accept a float as the value argument of GreaterThan.

        Validates that float bounds are stored without alteration.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = GreaterThan(3.14)
        self.assertAlmostEqual(c.value, 3.14)

    # -------------------------------------------------------------- GreaterThanOrEqual

    def testGreaterThanOrEqualStoresValue(self) -> None:
        """Instantiate GreaterThanOrEqual and verify the value attribute.

        Validates that the inclusive lower bound is stored correctly.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = GreaterThanOrEqual(0)
        self.assertEqual(c.value, 0)

    def testGreaterThanOrEqualIsConstraintMetadata(self) -> None:
        """Confirm GreaterThanOrEqual inherits from ConstraintMetadata.

        Validates the class hierarchy for isinstance checks.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsInstance(GreaterThanOrEqual(0), ConstraintMetadata)

    # ------------------------------------------------------------------ LessThan

    def testLessThanStoresValue(self) -> None:
        """Instantiate LessThan and verify the value attribute.

        Validates that the exclusive upper bound is stored correctly.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = LessThan(100)
        self.assertEqual(c.value, 100)

    def testLessThanIsConstraintMetadata(self) -> None:
        """Confirm LessThan inherits from ConstraintMetadata.

        Validates the class hierarchy for isinstance checks.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsInstance(LessThan(100), ConstraintMetadata)

    # ---------------------------------------------------------------- LessThanOrEqual

    def testLessThanOrEqualStoresValue(self) -> None:
        """Instantiate LessThanOrEqual and verify the value attribute.

        Validates that the inclusive upper bound is stored correctly.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = LessThanOrEqual(99)
        self.assertEqual(c.value, 99)

    def testLessThanOrEqualIsConstraintMetadata(self) -> None:
        """Confirm LessThanOrEqual inherits from ConstraintMetadata.

        Validates the class hierarchy for isinstance checks.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsInstance(LessThanOrEqual(99), ConstraintMetadata)

    # ------------------------------------------------------------------ MultipleOf

    def testMultipleOfStoresValue(self) -> None:
        """Instantiate MultipleOf and verify the value attribute.

        Validates that the divisor is stored without alteration.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = MultipleOf(5)
        self.assertEqual(c.value, 5)

    def testMultipleOfAcceptsFloat(self) -> None:
        """Accept a float divisor in MultipleOf.

        Validates that float divisors are stored correctly.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = MultipleOf(0.5)
        self.assertAlmostEqual(c.value, 0.5)

    def testMultipleOfIsConstraintMetadata(self) -> None:
        """Confirm MultipleOf inherits from ConstraintMetadata.

        Validates the class hierarchy for isinstance checks.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsInstance(MultipleOf(5), ConstraintMetadata)

    # -------------------------------------------------------------------- Pattern

    def testPatternStoresRegex(self) -> None:
        """Instantiate Pattern and verify the regex attribute.

        Validates that the regular expression string is stored as-is.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Pattern(r"^\d{3}-\d{2}-\d{4}$")
        self.assertEqual(c.regex, r"^\d{3}-\d{2}-\d{4}$")

    def testPatternDefaultMessageIsNone(self) -> None:
        """Confirm the default message of Pattern is None.

        Validates that the message attribute defaults to None when
        not provided.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Pattern(r".*")
        self.assertIsNone(c.message)

    def testPatternIsConstraintMetadata(self) -> None:
        """Confirm Pattern inherits from ConstraintMetadata.

        Validates the class hierarchy for isinstance checks.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsInstance(Pattern(r".*"), ConstraintMetadata)

    # ------------------------------------------------------------------ MinLength

    def testMinLengthStoresValue(self) -> None:
        """Instantiate MinLength and verify the value attribute.

        Validates that the minimum length integer is stored correctly.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = MinLength(3)
        self.assertEqual(c.value, 3)

    def testMinLengthIsConstraintMetadata(self) -> None:
        """Confirm MinLength inherits from ConstraintMetadata.

        Validates the class hierarchy for isinstance checks.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsInstance(MinLength(1), ConstraintMetadata)

    # ------------------------------------------------------------------ MaxLength

    def testMaxLengthStoresValue(self) -> None:
        """Instantiate MaxLength and verify the value attribute.

        Validates that the maximum length integer is stored correctly.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = MaxLength(255)
        self.assertEqual(c.value, 255)

    def testMaxLengthIsConstraintMetadata(self) -> None:
        """Confirm MaxLength inherits from ConstraintMetadata.

        Validates the class hierarchy for isinstance checks.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsInstance(MaxLength(255), ConstraintMetadata)

    # ---------------------------------------------------------------- TimezoneAware

    def testTimezoneAwareDefaultMessageIsNone(self) -> None:
        """Confirm the default message of TimezoneAware is None.

        Validates that the message attribute defaults to None when
        no message keyword argument is supplied.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = TimezoneAware()
        self.assertIsNone(c.message)

    def testTimezoneAwareIsConstraintMetadata(self) -> None:
        """Confirm TimezoneAware inherits from ConstraintMetadata.

        Validates the class hierarchy for isinstance checks.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsInstance(TimezoneAware(), ConstraintMetadata)

    # ---------------------------------------------------------------- TimezoneNaive

    def testTimezoneNaiveDefaultMessageIsNone(self) -> None:
        """Confirm the default message of TimezoneNaive is None.

        Validates that the message attribute defaults to None when
        no message keyword argument is supplied.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = TimezoneNaive()
        self.assertIsNone(c.message)

    def testTimezoneNaiveIsConstraintMetadata(self) -> None:
        """Confirm TimezoneNaive inherits from ConstraintMetadata.

        Validates the class hierarchy for isinstance checks.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsInstance(TimezoneNaive(), ConstraintMetadata)

    # ---------------------------------------------------------------- StrongPassword

    def testStrongPasswordIsImportedFromConstraints(self) -> None:
        """Confirm StrongPassword is accessible from the constraints module.

        Validates that the public API exports StrongPassword as expected.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(callable(StrongPassword))

    # --------------------------------------------------------------- frozen / immutable

    def testConstraintInstancesAreFrozen(self) -> None:
        """Confirm that constraint dataclass instances are immutable.

        Validates that attempting to mutate a constraint attribute raises
        an exception as required by the frozen dataclass contract.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = GreaterThan(5)
        with self.assertRaises(AttributeError):
            c.value = 10  # type: ignore[misc]

    def testConstraintsEqualityByValue(self) -> None:
        """Verify equality between constraint instances with the same value.

        Validates that two constraint instances carrying identical data
        compare as equal (frozen dataclass __eq__ by value).

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(GreaterThan(10), GreaterThan(10))
        self.assertNotEqual(GreaterThan(10), GreaterThan(20))
        self.assertNotEqual(LessThan(5), GreaterThan(5))
