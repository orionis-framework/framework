from orionis.support.types.stringable import Stringable
from orionis.test import TestCase

class TestStringableCase(TestCase):
    """Unit tests for Stringable case-conversion and formatting methods."""

    # ----------------------------------------------------------------- lower

    def testLowerConvertsToLowercase(self):
        """Convert the string to lowercase.

        Validates that `lower` returns a new Stringable containing the
        fully lowercased version of the original string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("HELLO World").lower(), Stringable("hello world"))

    def testLowerOnAlreadyLowercase(self):
        """Return unchanged string when already lowercase.

        Ensures `lower` is idempotent when applied to a string that
        contains no uppercase characters.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("hello").lower(), Stringable("hello"))

    # ----------------------------------------------------------------- upper

    def testUpperConvertsToUppercase(self):
        """Convert the string to uppercase.

        Validates that `upper` returns a new Stringable containing the
        fully uppercased version of the original string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("hello World").upper(), Stringable("HELLO WORLD"))

    def testUpperOnAlreadyUppercase(self):
        """Return unchanged string when already uppercase.

        Ensures `upper` is idempotent when applied to a string that
        contains no lowercase characters.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("HELLO").upper(), Stringable("HELLO"))

    # ------------------------------------------------------------- swapCase

    def testSwapCaseInvertsEachCharacter(self):
        """Swap the case of every cased character.

        Validates that `swapCase` converts lowercase to uppercase and
        vice versa throughout the entire string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(
            Stringable("Hello World").swapCase(),
            Stringable("hELLO wORLD"),
        )

    def testSwapCaseOnMixedContent(self):
        """Swap case while preserving non-cased characters.

        Ensures that numeric digits and punctuation are left unchanged
        while all cased characters have their case inverted.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("aB1!").swapCase()
        self.assertEqual(result, Stringable("Ab1!"))

    # ----------------------------------------------------------------- camel

    def testCamelConvertsFromSnakeCase(self):
        """Convert a snake_case string to camelCase.

        Validates that `camel` correctly transforms underscore-separated
        words into lowerCamelCase format.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("hello_world").camel(), Stringable("helloWorld"))

    def testCamelConvertsFromKebabCase(self):
        """Convert a kebab-case string to camelCase.

        Validates that `camel` correctly handles hyphen-separated words
        and produces lowerCamelCase output.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("hello-world").camel(), Stringable("helloWorld"))

    def testCamelConvertsFromSpaceSeparated(self):
        """Convert a space-separated string to camelCase.

        Ensures `camel` handles space-delimited input and produces the
        correct lowerCamelCase result.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("hello world").camel(), Stringable("helloWorld"))

    def testCamelReturnsEmptyOnEmptyString(self):
        """Return empty Stringable from an empty input.

        Validates that `camel` returns an empty Stringable when called
        on an empty string without raising errors.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("").camel(), Stringable(""))

    # ----------------------------------------------------------------- kebab

    def testKebabConvertsFromCamelCase(self):
        """Convert a camelCase string to kebab-case.

        Validates that `kebab` inserts hyphens at camelCase boundaries
        and lowercases all characters.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("helloWorld").kebab(), Stringable("hello-world"))

    def testKebabConvertsFromSnakeCase(self):
        """Convert a snake_case string to kebab-case.

        Ensures `kebab` replaces underscores with hyphens and returns a
        fully lowercased result.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("hello_world").kebab(), Stringable("hello-world"))

    def testKebabCollapsesMultipleSeparators(self):
        """Collapse multiple consecutive separators into one hyphen.

        Validates that `kebab` removes duplicate separators and produces
        a clean, single-hyphen-separated result.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(
            Stringable("hello  world").kebab(), Stringable("hello-world"),
        )

    # ----------------------------------------------------------------- snake

    def testSnakeConvertsFromCamelCase(self):
        """Convert a camelCase string to snake_case.

        Validates that `snake` inserts underscores at camelCase word
        boundaries and lowercases all characters.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("helloWorld").snake(), Stringable("hello_world"))

    def testSnakeConvertsFromSpaceSeparated(self):
        """Convert a space-separated string to snake_case.

        Ensures `snake` replaces spaces with underscores and lowercases
        all characters.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("hello world").snake(), Stringable("hello_world"))

    def testSnakeWithCustomDelimiter(self):
        """Convert using a custom delimiter instead of an underscore.

        Validates that `snake` correctly uses the provided delimiter
        character instead of the default underscore.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("helloWorld").snake("."), Stringable("hello.world"))

    # ---------------------------------------------------------------- studly

    def testStudlyConvertsToStudlyCase(self):
        """Convert the string to StudlyCase.

        Validates that `studly` capitalises the first letter of each word
        and joins them without any separator.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("hello_world").studly(), Stringable("HelloWorld"))

    def testStudlyFromKebabCase(self):
        """Convert a kebab-case string to StudlyCase.

        Ensures `studly` handles hyphen-separated input and produces
        correct StudlyCase output.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("hello-world").studly(), Stringable("HelloWorld"))

    # ---------------------------------------------------------------- pascal

    def testPascalDelegatesToStudly(self):
        """Produce the same output as studly for PascalCase conversion.

        Validates that `pascal` is an alias for `studly` and yields
        identical results for the same input.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("hello_world")
        self.assertEqual(s.pascal(), s.studly())

    # ------------------------------------------------------------------ slug

    def testSlugConvertsToUrlFriendlyString(self):
        """Generate a URL-friendly slug from the string.

        Validates that `slug` lowercases, removes special characters, and
        joins words with the default hyphen separator.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("Hello World!").slug(), Stringable("hello-world"))

    def testSlugWithCustomSeparator(self):
        """Generate a slug using a custom separator.

        Ensures that `slug` respects the provided separator argument
        instead of defaulting to a hyphen.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(
            Stringable("Hello World").slug("_"), Stringable("hello_world"),
        )

    def testSlugReplacesAtSymbol(self):
        """Replace the at-symbol using the default dictionary.

        Validates that the default dictionary mapping "@" to "at" is
        applied before the slug transformation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("user@example").slug()
        self.assertIn("at", str(result))

    def testSlugRaisesTypeErrorOnNonStringSeparator(self):
        """Raise TypeError when separator is not a string.

        Ensures `slug` validates the separator type before processing the
        string, raising TypeError for invalid input.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").slug(separator=42)

    def testSlugRaisesTypeErrorOnNonDictDictionary(self):
        """Raise TypeError when dictionary argument is not a dict.

        Verifies `slug` enforces the dictionary type constraint on the
        dictionary parameter.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").slug(dictionary="not-a-dict")

    # ----------------------------------------------------------------- title

    def testTitleCapitalisesEachWord(self):
        """Convert the string to title case.

        Validates that `title` capitalises the first letter of every word
        while lowercasing remaining letters.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("hello world").title(), Stringable("Hello World"))

    # --------------------------------------------------------------- headline

    def testHeadlineCapitalisesWords(self):
        """Convert the string to headline case.

        Validates that `headline` capitalises the first letter of each
        word found in the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello world").headline()
        self.assertEqual(result, Stringable("Hello World"))

    def testHeadlineHandlesEmptyString(self):
        """Return empty Stringable from an empty input.

        Ensures `headline` produces an empty Stringable when called on
        an empty string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("").headline(), Stringable(""))

    # --------------------------------------------------------------------- apa

    def testApaCapitalisesFirstWord(self):
        """Capitalise the first word in APA style.

        Validates that `apa` always capitalises the first word regardless
        of its length or membership in the lowercase-word set.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("the quick brown fox").apa()
        self.assertTrue(str(result).startswith("The"))

    def testApaLowercasesShortWords(self):
        """Lowercase short words in the middle per APA rules.

        Ensures `apa` lowercases small words (a, an, and, etc.) that
        appear in non-first, non-last positions.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = str(Stringable("a tale of ice and fire").apa())
        words = result.split()
        # "of" and "and" are in the middle and should be lowercase
        self.assertEqual(words[2], "of")

    def testApaCapitalisesLastWord(self):
        """Capitalise the last word in APA style.

        Validates that `apa` always capitalises the last word, even if it
        would normally be lowercased by the APA rules.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = str(Stringable("to be or not to be").apa())
        words = result.split()
        self.assertEqual(words[-1][0], words[-1][0].upper())

    # --------------------------------------------------------------- ucfirst

    def testUcfirstCapitalisesFirstCharacter(self):
        """Capitalise only the first character of the string.

        Validates that `ucfirst` uppercases the very first character
        while leaving the rest of the string unchanged.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("hello world").ucfirst(), Stringable("Hello world"))

    def testUcfirstOnEmptyString(self):
        """Return empty Stringable from an empty input.

        Ensures `ucfirst` returns an empty Stringable when invoked on
        an empty string without raising errors.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("").ucfirst(), Stringable(""))

    # --------------------------------------------------------------- lcfirst

    def testLcfirstLowercasesFirstCharacter(self):
        """Lowercase only the first character of the string.

        Validates that `lcfirst` lowercases the very first character
        while leaving the rest of the string unchanged.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("Hello World").lcfirst(), Stringable("hello World"))

    def testLcfirstOnEmptyString(self):
        """Return empty Stringable from an empty input.

        Ensures `lcfirst` returns an empty Stringable when invoked on
        an empty string without raising errors.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("").lcfirst(), Stringable(""))

    # ----------------------------------------------------------- convertCase

    def testConvertCaseModeNoneAppliesCaseFold(self):
        """Apply casefold when mode is None.

        Validates that `convertCase` with no mode argument defaults to
        casefolding, which is suitable for case-insensitive comparisons.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("HELLO").convertCase(None)
        self.assertEqual(result, Stringable("hello"))

    def testConvertCaseMode0AppliesCaseFold(self):
        """Apply casefold when mode is 0.

        Validates that `convertCase(0)` applies casefold transformation
        to the string, producing a fully case-folded result.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("HELLO").convertCase(0), Stringable("hello"))

    def testConvertCaseMode1AppliesUppercase(self):
        """Convert to uppercase when mode is 1.

        Validates that `convertCase(1)` returns the fully uppercased
        version of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("hello").convertCase(1), Stringable("HELLO"))

    def testConvertCaseMode2AppliesLowercase(self):
        """Convert to lowercase when mode is 2.

        Validates that `convertCase(2)` returns the fully lowercased
        version of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("HELLO").convertCase(2), Stringable("hello"))

    def testConvertCaseMode3AppliesTitleCase(self):
        """Convert to titlecase when mode is 3.

        Validates that `convertCase(3)` returns the title-cased version
        of the string, capitalising each word.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(
            Stringable("hello world").convertCase(3), Stringable("Hello World"),
        )

    def testConvertCaseRaisesTypeErrorOnNonIntegerMode(self):
        """Raise TypeError when mode is not an integer or None.

        Ensures `convertCase` validates its mode parameter type before
        attempting any transformation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").convertCase("bad")

    # ---------------------------------------------------------- transliterate

    def testTransliterateConvertsAccentedChars(self):
        """Transliterate accented characters to ASCII equivalents.

        Validates that `transliterate` strips diacritics from accented
        characters and returns a clean ASCII string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("café").transliterate()
        self.assertEqual(str(result), "cafe")

    def testTransliterateStrictModeReplacesUnknown(self):
        """Replace non-ASCII characters with the unknown character in strict mode.

        Validates that `transliterate` with strict=True replaces any
        character that cannot be converted with the unknown placeholder.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("日本語").transliterate("?", strict=True)
        self.assertTrue(all(c == "?" or ord(c) < 128 for c in str(result)))

    def testTransliterateRaisesTypeErrorOnMultiCharUnknown(self):
        """Raise TypeError when unknown is not a single character.

        Ensures `transliterate` enforces the single-character constraint
        on the unknown replacement argument.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").transliterate("??")

    # ------------------------------------------------------------------ ascii

    def testAsciiRemovesDiacritics(self):
        """Remove diacritics and non-ASCII characters via normalization.

        Validates that `ascii` uses Unicode NFKD normalization to strip
        accent marks and produce a pure ASCII string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("Héllo Wörld").ascii()
        self.assertEqual(str(result), "Hello World")

    def testAsciiOnPureAsciiInput(self):
        """Return the original string when input is already ASCII.

        Ensures `ascii` is a no-op when the string contains only
        characters within the ASCII range.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("hello").ascii(), Stringable("hello"))
