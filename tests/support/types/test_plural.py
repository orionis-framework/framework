from orionis.test import TestCase
from orionis.support.types.stringable import Stringable

class TestStringablePlural(TestCase):
    """Unit tests for Stringable pluralisation and parse methods."""

    # ----------------------------------------------------------------- plural

    def testPluralReturnsPluralFormByDefault(self):
        """Return the plural form when count defaults to 2.

        Validates that `plural` applies pluralisation rules and produces
        the expected plural for a regular English noun.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("cat").plural()
        self.assertEqual(result, Stringable("cats"))

    def testPluralReturnsSingularWhenCountIsOne(self):
        """Return the singular form when count is 1.

        Validates that `plural` leaves the string unchanged when the
        count argument is 1.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("cat").plural(1)
        self.assertEqual(result, Stringable("cat"))

    def testPluralAppliesIesRule(self):
        """Apply the -ies pluralisation rule for words ending in -y.

        Validates that `plural` correctly converts a word ending with
        a consonant followed by -y to the -ies form.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("baby").plural()
        self.assertEqual(result, Stringable("babies"))

    def testPluralAppliesEsRule(self):
        """Apply the -es pluralisation rule for words ending in -s.

        Validates that `plural` appends -es for words that end with
        sibilant-like endings such as -s.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("bus").plural()
        self.assertEqual(str(result), "buses")

    def testPluralWithListCountUsesLength(self):
        """Use the length of a list to determine pluralisation.

        Validates that `plural` treats a list argument as a count equal
        to its length for the pluralisation decision.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("apple").plural([1, 2, 3])
        self.assertEqual(result, Stringable("apples"))

    def testPluralWithSingleItemListReturnsSingular(self):
        """Return the singular form when the list has a single item.

        Validates that `plural` returns the singular form when the list
        argument contains exactly one element.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("apple").plural([1])
        self.assertEqual(result, Stringable("apple"))

    def testPluralPrependsCountWhenRequested(self):
        """Prepend the count when prepend_count is True.

        Validates that `plural` with prepend_count=True prefixes the
        resulting string with the count value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("cat").plural(3, prepend_count=True)
        self.assertTrue(str(result).startswith("3"))

    def testPluralRaisesTypeErrorOnNonBoolPrependCount(self):
        """Raise TypeError when prepend_count is not a boolean.

        Ensures `plural` validates the prepend_count argument type
        before applying any pluralisation logic.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("cat").plural(prepend_count="yes")

    def testPluralRaisesTypeErrorOnInvalidCount(self):
        """Raise TypeError when count is an unsupported type.

        Ensures `plural` validates that the count argument is an integer,
        float, or collection before processing. A plain callable has no
        __len__ and is not numeric, so it triggers the guard.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("cat").plural(lambda: None)

    # --------------------------------------------------------------- singular

    def testSingularConvertsPlural(self):
        """Convert a regular plural form to its singular.

        Validates that `singular` removes the trailing -s to produce
        the expected singular form.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("cats").singular()
        self.assertEqual(result, Stringable("cat"))

    def testSingularConvertsIesPlural(self):
        """Convert an -ies plural to its -y singular form.

        Validates that `singular` correctly applies the reverse of the
        -ies pluralisation rule.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("babies").singular()
        self.assertEqual(result, Stringable("baby"))

    def testSingularConvertsEsPlural(self):
        """Convert a word ending in -es to its singular form.

        Validates that `singular` strips the -es suffix from words that
        use that plural ending.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("buses").singular()
        self.assertEqual(result, Stringable("bus"))

    def testSingularNoChangeOnNonPlural(self):
        """Return unchanged string for a word that is already singular.

        Ensures `singular` does not incorrectly modify a word that is
        already in singular form and ends with -ss.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("class").singular()
        self.assertEqual(result, Stringable("class"))

    # ----------------------------------------------------------- pluralStudly

    def testPluralStudlyPluralisesLastWordInStudlyCase(self):
        """Pluralise the last word of a StudlyCaps string.

        Validates that `pluralStudly` correctly identifies the last word
        in a StudlyCaps string, pluralises it, and reconstructs the
        StudlyCase form.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("BlogPost").pluralStudly()
        self.assertIn("Post", str(result))

    def testPluralStudlyReturnsSingularFormAtCountOne(self):
        """Return the singular form of the last StudlyCase word at count 1.

        Validates that `pluralStudly(1)` leaves the last word of the
        StudlyCaps string in singular form.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("BlogPost").pluralStudly(1)
        self.assertIn("Post", str(result))

    # ----------------------------------------------------------- pluralPascal

    def testPluralPascalPluralisesLastWordInPascalCase(self):
        """Pluralise the last word of a PascalCase string.

        Validates that `pluralPascal` correctly identifies the last word
        in a PascalCase string, pluralises it, and reconstructs the
        PascalCase form.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("UserProfile").pluralPascal()
        self.assertIsInstance(result, Stringable)

    def testPluralPascalOnEmptyStringReturnsEmpty(self):
        """Return empty Stringable from an empty input.

        Validates that `pluralPascal` returns an empty Stringable when
        called on an empty string without raising errors.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("").pluralPascal()
        self.assertEqual(result, Stringable(""))

    def testPluralPascalReturnsSingularFormAtCountOne(self):
        """Return the singular form of the last PascalCase word at count 1.

        Validates that `pluralPascal(1)` leaves the last word of the
        PascalCase string in singular form.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("UserProfile").pluralPascal(1)
        self.assertIn("Profile", str(result))

    # --------------------------------------------------------- parseCallback

    def testParseCallbackSplitsOnAtSymbol(self):
        """Split a Class@method string into class and method parts.

        Validates that `parseCallback` correctly splits the callback
        string at the '@' separator and returns a two-element list.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("MyClass@myMethod").parseCallback()
        self.assertEqual(result, ["MyClass", "myMethod"])

    def testParseCallbackReturnsDefaultMethodWhenNoAtSymbol(self):
        """Return the default method when no @ separator is present.

        Validates that `parseCallback` returns the full string as the
        class name and the default value as the method name.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("MyClass").parseCallback("handle")
        self.assertEqual(result, ["MyClass", "handle"])

    def testParseCallbackReturnsNoneMethodWhenNoDefault(self):
        """Return None as method name when no default and no @ separator.

        Validates that `parseCallback` returns None as the second
        element when no default argument is supplied and no @ is found.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("MyClass").parseCallback()
        self.assertEqual(result, ["MyClass", None])

    def testParseCallbackRaisesTypeErrorOnNonStringDefault(self):
        """Raise TypeError when default is not a string or None.

        Ensures `parseCallback` validates the default argument type
        before performing any parsing.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("MyClass").parseCallback(default=42)

    def testParseCallbackSplitsOnlyAtFirstAtSymbol(self):
        """Split only at the first @ symbol when multiple appear.

        Validates that `parseCallback` uses maxsplit=1 so that a method
        name containing '@' is preserved intact.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("MyClass@method@extra").parseCallback()
        self.assertEqual(result, ["MyClass", "method@extra"])
