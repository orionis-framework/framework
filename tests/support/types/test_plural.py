# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from orionis.support.types.stringable import Stringable
from orionis.test import TestCase


class TestStringablePlural(TestCase):
    """Unit tests for Stringable pluralisation and parse methods."""

    # ----------------------------------------------------------------- plural

    def testPluralReturnsPluralFormByDefault(self) -> None:
        """Return the plural form when count defaults to 2.

        Validates that `plural` applies pluralisation rules and produces
        the expected plural for a regular English noun.

        Returns
        -------
        None
            No return value.
        """
        result = Stringable("cat").plural()
        self.assertEqual(result, Stringable("cats"))

    def testPluralReturnsSingularWhenCountIsOne(self) -> None:
        """Return the singular form when count is 1.

        Validates that `plural` leaves the string unchanged when the
        count argument is 1.

        Returns
        -------
        None
            No return value.
        """
        result = Stringable("cat").plural(1)
        self.assertEqual(result, Stringable("cat"))

    def testPluralAppliesIesRule(self) -> None:
        """Apply the -ies pluralisation rule for words ending in -y.

        Validates that `plural` correctly converts a word ending with
        a consonant followed by -y to the -ies form.

        Returns
        -------
        None
            No return value.
        """
        result = Stringable("baby").plural()
        self.assertEqual(result, Stringable("babies"))

    def testPluralAppliesEsRule(self) -> None:
        """Apply the -es pluralisation rule for words ending in -s.

        Validates that `plural` appends -es for words that end with
        sibilant-like endings such as -s.

        Returns
        -------
        None
            No return value.
        """
        result = Stringable("bus").plural()
        self.assertEqual(str(result), "buses")

    def testPluralWithListCountUsesLength(self) -> None:
        """Use the length of a list to determine pluralisation.

        Validates that `plural` treats a list argument as a count equal
        to its length for the pluralisation decision.

        Returns
        -------
        None
            No return value.
        """
        result = Stringable("apple").plural([1, 2, 3])
        self.assertEqual(result, Stringable("apples"))

    def testPluralWithSingleItemListReturnsSingular(self) -> None:
        """Return the singular form when the list has a single item.

        Validates that `plural` returns the singular form when the list
        argument contains exactly one element.

        Returns
        -------
        None
            No return value.
        """
        result = Stringable("apple").plural([1])
        self.assertEqual(result, Stringable("apple"))

    def testPluralPrependsCountWhenRequested(self) -> None:
        """Prepend the count when prepend_count is True.

        Validates that `plural` with prepend_count=True prefixes the
        resulting string with the count value.

        Returns
        -------
        None
            No return value.
        """
        result = Stringable("cat").plural(3, prepend_count=True)
        self.assertTrue(str(result).startswith("3"))

    def testPluralRaisesTypeErrorOnNonBoolPrependCount(self) -> None:
        """Raise TypeError when prepend_count is not a boolean.

        Ensures `plural` validates the prepend_count argument type
        before applying any pluralisation logic.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(TypeError):
            Stringable("cat").plural(prepend_count="yes")

    def testPluralRaisesTypeErrorOnInvalidCount(self) -> None:
        """Raise TypeError when count is an unsupported type.

        Ensures `plural` validates that the count argument is an integer,
        float, or collection before processing. A plain callable has no
        __len__ and is not numeric, so it triggers the guard.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(TypeError):
            Stringable("cat").plural(lambda: None)

    # --------------------------------------------------------------- singular

    def testSingularConvertsPlural(self) -> None:
        """Convert a regular plural form to its singular.

        Validates that `singular` removes the trailing -s to produce
        the expected singular form.

        Returns
        -------
        None
            No return value.
        """
        result = Stringable("cats").singular()
        self.assertEqual(result, Stringable("cat"))

    def testSingularConvertsIesPlural(self) -> None:
        """Convert an -ies plural to its -y singular form.

        Validates that `singular` correctly applies the reverse of the
        -ies pluralisation rule.

        Returns
        -------
        None
            No return value.
        """
        result = Stringable("babies").singular()
        self.assertEqual(result, Stringable("baby"))

    def testSingularConvertsEsPlural(self) -> None:
        """Convert a word ending in -es to its singular form.

        Validates that `singular` strips the -es suffix from words that
        use that plural ending.

        Returns
        -------
        None
            No return value.
        """
        result = Stringable("buses").singular()
        self.assertEqual(result, Stringable("bus"))

    def testSingularNoChangeOnNonPlural(self) -> None:
        """Return unchanged string for a word that is already singular.

        Ensures `singular` does not incorrectly modify a word that is
        already in singular form and ends with -ss.

        Returns
        -------
        None
            No return value.
        """
        result = Stringable("class").singular()
        self.assertEqual(result, Stringable("class"))

    # ----------------------------------------------------------- pluralStudly

    def testPluralStudlyPluralisesLastWordInStudlyCase(self) -> None:
        """Pluralise the last word of a StudlyCaps string.

        Validates that `pluralStudly` correctly identifies the last word
        in a StudlyCaps string, pluralises it, and reconstructs the
        StudlyCase form.

        Returns
        -------
        None
            No return value.
        """
        result = Stringable("BlogPost").pluralStudly()
        self.assertEqual(result, "BlogPosts")

    def testPluralStudlyReturnsSingularFormAtCountOne(self) -> None:
        """Return the singular form of the last StudlyCase word at count 1.

        Validates that `pluralStudly(1)` leaves the last word of the
        StudlyCaps string in singular form.

        Returns
        -------
        None
            No return value.
        """
        result = Stringable("BlogPost").pluralStudly(1)
        self.assertEqual(result, "BlogPost")

    # ----------------------------------------------------------- pluralPascal

    def testPluralPascalPluralisesLastWordInPascalCase(self) -> None:
        """Pluralise the last word of a PascalCase string.

        Validates that `pluralPascal` correctly identifies the last word
        in a PascalCase string, pluralises it, and reconstructs the
        PascalCase form.

        Returns
        -------
        None
            No return value.
        """
        result = Stringable("UserProfile").pluralPascal()
        self.assertEqual(result, "UserProfiles")

    def testPluralPascalOnEmptyStringReturnsEmpty(self) -> None:
        """Return empty Stringable from an empty input.

        Validates that `pluralPascal` returns an empty Stringable when
        called on an empty string without raising errors.

        Returns
        -------
        None
            No return value.
        """
        result = Stringable("").pluralPascal()
        self.assertEqual(result, Stringable(""))

    def testPluralPascalReturnsSingularFormAtCountOne(self) -> None:
        """Return the singular form of the last PascalCase word at count 1.

        Validates that `pluralPascal(1)` leaves the last word of the
        PascalCase string in singular form.

        Returns
        -------
        None
            No return value.
        """
        result = Stringable("UserProfile").pluralPascal(1)
        self.assertEqual(result, "UserProfile")

    # --------------------------------------------------------- parseCallback

    def testParseCallbackSplitsOnAtSymbol(self) -> None:
        """Split a Class@method string into class and method parts.

        Validates that `parseCallback` correctly splits the callback
        string at the '@' separator and returns a two-element list.

        Returns
        -------
        None
            No return value.
        """
        result = Stringable("MyClass@myMethod").parseCallback()
        self.assertEqual(result, ["MyClass", "myMethod"])

    def testParseCallbackReturnsDefaultMethodWhenNoAtSymbol(self) -> None:
        """Return the default method when no @ separator is present.

        Validates that `parseCallback` returns the full string as the
        class name and the default value as the method name.

        Returns
        -------
        None
            No return value.
        """
        result = Stringable("MyClass").parseCallback("handle")
        self.assertEqual(result, ["MyClass", "handle"])

    def testParseCallbackReturnsNoneMethodWhenNoDefault(self) -> None:
        """Return None as method name when no default and no @ separator.

        Validates that `parseCallback` returns None as the second
        element when no default argument is supplied and no @ is found.

        Returns
        -------
        None
            No return value.
        """
        result = Stringable("MyClass").parseCallback()
        self.assertEqual(result, ["MyClass", None])

    def testParseCallbackRaisesTypeErrorOnNonStringDefault(self) -> None:
        """Raise TypeError when default is not a string or None.

        Ensures `parseCallback` validates the default argument type
        before performing any parsing.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(TypeError):
            Stringable("MyClass").parseCallback(default=42)

    def testParseCallbackSplitsOnlyAtFirstAtSymbol(self) -> None:
        """Split only at the first @ symbol when multiple appear.

        Validates that `parseCallback` uses maxsplit=1 so that a method
        name containing '@' is preserved intact.

        Returns
        -------
        None
            No return value.
        """
        result = Stringable("MyClass@method@extra").parseCallback()
        self.assertEqual(result, ["MyClass", "method@extra"])
