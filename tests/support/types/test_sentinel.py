from orionis.support.types.sentinel import _MISSING_TYPE, MISSING
from orionis.test import TestCase

class TestMissingSentinel(TestCase):

    # ------------------------------------------------ __repr__

    def testReprReturnsMissingString(self):
        """Return the sentinel string representation.

        Validates that repr of MISSING produces the exact string
        '<MISSING>' for clear debugging output.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(repr(MISSING), "<MISSING>")

    def testReprReturnType(self):
        """Return a str instance from repr.

        Validates that calling repr on the MISSING sentinel
        produces a value of type str.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsInstance(repr(MISSING), str)

    # ------------------------------------------------ __bool__

    def testBoolIsFalsy(self):
        """Evaluate as falsy in boolean context.

        Validates that the MISSING sentinel evaluates to False
        when used in a boolean expression.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(MISSING)

    def testBoolReturnsFalse(self):
        """Return exactly False from bool conversion.

        Validates that calling bool on MISSING returns the
        boolean value False.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIs(bool(MISSING), False)

    def testBoolInIfStatement(self):
        """Behave as falsy in conditional statements.

        Validates that the MISSING sentinel causes the else
        branch to execute in an if statement.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = "present" if MISSING else "missing"
        self.assertEqual(result, "missing")

    # ------------------------------------------------ type identity

    def testMissingIsInstanceOfMissingType(self):
        """Verify MISSING is an instance of _MISSING_TYPE.

        Validates that the module-level MISSING constant is a
        proper instance of the _MISSING_TYPE class.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsInstance(MISSING, _MISSING_TYPE)

    def testMissingIsSingleton(self):
        """Verify MISSING is stable across imports.

        Validates that importing MISSING always returns the
        same object identity.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        from orionis.support.types.sentinel import MISSING as REIMPORTED
        self.assertIs(MISSING, REIMPORTED)

    def testNewInstanceIsDifferentObject(self):
        """Create distinct instances from the class constructor.

        Validates that constructing a new _MISSING_TYPE instance
        produces a different object from the module-level MISSING.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        other = _MISSING_TYPE()
        self.assertIsNot(MISSING, other)

    # ---------------------------------------- comparison behavior

    def testMissingIsNotNone(self):
        """Distinguish MISSING from None.

        Validates that the MISSING sentinel is not None, ensuring
        it serves as a distinct marker for absent values.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsNot(MISSING, None)
        self.assertNotEqual(MISSING, None)

    def testMissingIsNotFalse(self):
        """Distinguish MISSING from False.

        Validates that the MISSING sentinel is not the boolean
        False even though it evaluates as falsy.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsNot(MISSING, False)

    def testMissingIsNotZero(self):
        """Distinguish MISSING from zero.

        Validates that the MISSING sentinel is not equal to zero
        even though both are falsy.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertNotEqual(MISSING, 0)

    def testMissingIsNotEmptyString(self):
        """Distinguish MISSING from an empty string.

        Validates that the MISSING sentinel is not equal to an
        empty string even though both are falsy.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertNotEqual(MISSING, "")

    # ---------------------------------------- usage patterns

    def testUsableAsDefaultArgument(self):
        """Serve as a default argument sentinel.

        Validates that MISSING can be used as a default parameter
        value and detected via identity comparison.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """

        def func(value=MISSING):
            """Check whether the supplied value is the missing sentinel.

            Parameters
            ----------
            value : object
                Value supplied for ``value``.

            Returns
            -------
            object
                Value produced by the helper.
            """
            return value is MISSING
        self.assertTrue(func())
        self.assertFalse(func(42))

    def testUsableAsDefaultWithNone(self):
        """Distinguish MISSING from explicit None argument.

        Validates that passing None as an argument is detected
        as different from the MISSING default.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """

        def func(value=MISSING):
            """Check whether the supplied value is the missing sentinel.

            Parameters
            ----------
            value : object
                Value supplied for ``value``.

            Returns
            -------
            object
                Value produced by the helper.
            """
            return value is MISSING
        self.assertFalse(func(None))

    def testUsableInDictionaryAsValue(self):
        """Store MISSING as a dictionary value.

        Validates that MISSING can be stored and retrieved from
        a dictionary while maintaining identity.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = {"key": MISSING}
        self.assertIs(d["key"], MISSING)

    def testUsableInListContainment(self):
        """Check MISSING membership in a list.

        Validates that the `in` operator correctly detects MISSING
        inside a list.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        items = [1, None, MISSING, "x"]
        self.assertIn(MISSING, items)
