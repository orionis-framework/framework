# ruff: noqa: FBT003, PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Keep established public and external protocol names and signatures.
from importlib import import_module
from orionis.support.types.sentinel import _MISSING_TYPE, MISSING
from orionis.test import TestCase


class TestMissingSentinel(TestCase):
    # ------------------------------------------------ __repr__

    def testReprReturnsMissingString(self) -> None:
        """Return the sentinel string representation.

        Validates that repr of MISSING produces the exact string
        '<MISSING>' for clear debugging output.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(repr(MISSING), "<MISSING>")

    def testReprReturnType(self) -> None:
        """Return a str instance from repr.

        Validates that calling repr on the MISSING sentinel
        produces a value of type str.

        Returns
        -------
        None
            No return value.
        """
        self.assertIsInstance(repr(MISSING), str)

    # ------------------------------------------------ __bool__

    def testBoolIsFalsy(self) -> None:
        """Evaluate as falsy in boolean context.

        Validates that the MISSING sentinel evaluates to False
        when used in a boolean expression.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(MISSING)

    def testBoolReturnsFalse(self) -> None:
        """Return exactly False from bool conversion.

        Validates that calling bool on MISSING returns the
        boolean value False.

        Returns
        -------
        None
            No return value.
        """
        self.assertIs(bool(MISSING), False)

    def testBoolInIfStatement(self) -> None:
        """Behave as falsy in conditional statements.

        Validates that the MISSING sentinel causes the else
        branch to execute in an if statement.

        Returns
        -------
        None
            No return value.
        """
        result = "present" if MISSING else "missing"
        self.assertEqual(result, "missing")

    # ------------------------------------------------ type identity

    def testMissingIsInstanceOfMissingType(self) -> None:
        """Verify MISSING is an instance of _MISSING_TYPE.

        Validates that the module-level MISSING constant is a
        proper instance of the _MISSING_TYPE class.

        Returns
        -------
        None
            No return value.
        """
        self.assertIsInstance(MISSING, _MISSING_TYPE)

    def testMissingIsSingleton(self) -> None:
        """Verify MISSING is stable across imports.

        Validates that importing MISSING always returns the
        same object identity.

        Returns
        -------
        None
            No return value.
        """
        module = import_module("orionis.support.types.sentinel")
        self.assertIs(MISSING, module.MISSING)

    def testNewInstanceIsDifferentObject(self) -> None:
        """Create distinct instances from the class constructor.

        Validates that constructing a new _MISSING_TYPE instance
        produces a different object from the module-level MISSING.

        Returns
        -------
        None
            No return value.
        """
        other = _MISSING_TYPE()
        self.assertIsNot(MISSING, other)

    # ---------------------------------------- comparison behavior

    def testMissingIsNotNone(self) -> None:
        """Distinguish MISSING from None.

        Validates that the MISSING sentinel is not None, ensuring
        it serves as a distinct marker for absent values.

        Returns
        -------
        None
            No return value.
        """
        self.assertIsNot(MISSING, None)
        self.assertNotEqual(MISSING, None)

    def testMissingIsNotFalse(self) -> None:
        """Distinguish MISSING from False.

        Validates that the MISSING sentinel is not the boolean
        False even though it evaluates as falsy.

        Returns
        -------
        None
            No return value.
        """
        self.assertIsNot(MISSING, False)

    def testMissingIsNotZero(self) -> None:
        """Distinguish MISSING from zero.

        Validates that the MISSING sentinel is not equal to zero
        even though both are falsy.

        Returns
        -------
        None
            No return value.
        """
        self.assertNotEqual(MISSING, 0)

    def testMissingIsNotEmptyString(self) -> None:
        """Distinguish MISSING from an empty string.

        Validates that the MISSING sentinel is not equal to an
        empty string even though both are falsy.

        Returns
        -------
        None
            No return value.
        """
        self.assertNotEqual(MISSING, "")

    # ---------------------------------------- usage patterns

    def testUsableAsDefaultArgument(self) -> None:
        """Serve as a default argument sentinel.

        Validates that MISSING can be used as a default parameter
        value and detected via identity comparison.

        Returns
        -------
        None
            No return value.
        """

        def func(value: object = MISSING) -> bool:
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

    def testUsableAsDefaultWithNone(self) -> None:
        """Distinguish MISSING from explicit None argument.

        Validates that passing None as an argument is detected
        as different from the MISSING default.

        Returns
        -------
        None
            No return value.
        """

        def func(value: object = MISSING) -> bool:
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

    def testUsableInDictionaryAsValue(self) -> None:
        """Store MISSING as a dictionary value.

        Validates that MISSING can be stored and retrieved from
        a dictionary while maintaining identity.

        Returns
        -------
        None
            No return value.
        """
        d = {"key": MISSING}
        self.assertIs(d["key"], MISSING)

    def testUsableInListContainment(self) -> None:
        """Check MISSING membership in a list.

        Validates that the `in` operator correctly detects MISSING
        inside a list.

        Returns
        -------
        None
            No return value.
        """
        items = [1, None, MISSING, "x"]
        self.assertIn(MISSING, items)
