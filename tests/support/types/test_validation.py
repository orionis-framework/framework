from orionis.test import TestCase
from orionis.support.types.stringable import Stringable

class TestStringableValidation(TestCase):
    """Unit tests for Stringable type-check and validation methods."""

    # --------------------------------------------------------------- isEmpty

    def testIsEmptyReturnsTrueForEmptyString(self):
        """Return True when the string has zero length.

        Validates that `isEmpty` correctly identifies an empty Stringable
        instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable("").isEmpty())

    def testIsEmptyReturnsFalseForNonEmptyString(self):
        """Return False when the string has at least one character.

        Ensures `isEmpty` correctly determines that a non-empty
        Stringable is not empty.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(Stringable("hello").isEmpty())

    # ------------------------------------------------------------- isNotEmpty

    def testIsNotEmptyReturnsTrueForNonEmpty(self):
        """Return True when the string contains at least one character.

        Validates that `isNotEmpty` correctly identifies a non-empty
        Stringable instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable("hello").isNotEmpty())

    def testIsNotEmptyReturnsFalseForEmpty(self):
        """Return False when the string is empty.

        Ensures `isNotEmpty` returns False when the Stringable has no
        characters.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(Stringable("").isNotEmpty())

    # ---------------------------------------------------------------- exactly

    def testExactlyReturnsTrueForIdenticalString(self):
        """Return True when the string matches exactly.

        Validates that `exactly` returns True when the provided value is
        identical to the current string content.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable("hello").exactly("hello"))

    def testExactlyReturnsFalseForDifferentString(self):
        """Return False when the string does not match.

        Ensures `exactly` returns False when the provided value differs
        from the current string, including differences in casing.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(Stringable("hello").exactly("Hello"))

    def testExactlyRaisesTypeErrorOnNonString(self):
        """Raise TypeError when value is not a string.

        Ensures `exactly` validates the type of its argument before
        performing any comparison.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").exactly(42)

    # --------------------------------------------------------------- endsWith

    def testEndsWithReturnsTrueWhenStringEndsWithNeedle(self):
        """Return True when the string ends with the given substring.

        Validates that `endsWith` correctly identifies when the string
        terminates with the provided needle.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable("hello.py").endsWith(".py"))

    def testEndsWithReturnsFalseWhenNotMatching(self):
        """Return False when the string does not end with the needle.

        Ensures `endsWith` returns False when none of the provided
        needles match the end of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(Stringable("hello.py").endsWith(".txt"))

    def testEndsWithAcceptsMultipleNeedles(self):
        """Return True when any needle in an iterable matches.

        Validates that `endsWith` accepts an iterable of needles and
        returns True if any one of them matches the string's end.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable("hello.py").endsWith([".py", ".txt"]))

    # ------------------------------------------------------------- startsWith

    def testStartsWithReturnsTrueWhenStringStartsWithNeedle(self):
        """Return True when the string starts with the given substring.

        Validates that `startsWith` correctly identifies when the string
        begins with the provided needle.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable("hello world").startsWith("hello"))

    def testStartsWithReturnsFalseWhenNotMatching(self):
        """Return False when the string does not start with the needle.

        Ensures `startsWith` returns False when none of the provided
        needles match the beginning of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(Stringable("hello world").startsWith("world"))

    def testStartsWithAcceptsListOfNeedles(self):
        """Return True when any needle from a list matches the start.

        Validates that `startsWith` accepts a list of needles and returns
        True if any one of them matches the beginning of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable("hello world").startsWith(["hi", "hello"]))

    def testStartsWithRaisesTypeErrorOnNonString(self):
        """Raise TypeError when a needle in the list is not a string.

        Ensures `startsWith` validates each needle in the list for the
        string type constraint.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").startsWith([1, "hi"])

    # ---------------------------------------------------------- doesntStartWith

    def testDoesntStartWithReturnsTrueWhenNoMatch(self):
        """Return True when the string does not start with any needle.

        Validates that `doesntStartWith` returns True when none of the
        provided needles match the beginning of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable("hello").doesntStartWith("world"))

    def testDoesntStartWithReturnsFalseWhenMatchFound(self):
        """Return False when the string does start with a needle.

        Ensures `doesntStartWith` returns False when the string begins
        with one of the provided needles.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(Stringable("hello").doesntStartWith("hello"))

    # ----------------------------------------------------------- doesntEndWith

    def testDoesntEndWithReturnsTrueWhenNoMatch(self):
        """Return True when the string does not end with any needle.

        Validates that `doesntEndWith` returns True when none of the
        provided needles match the end of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable("hello.py").doesntEndWith(".txt"))

    def testDoesntEndWithReturnsFalseWhenMatchFound(self):
        """Return False when the string does end with a needle.

        Ensures `doesntEndWith` returns False when the string terminates
        with one of the provided needles.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(Stringable("hello.py").doesntEndWith(".py"))

    # --------------------------------------------------------------- contains

    def testContainsReturnsTrueWhenNeedleFound(self):
        """Return True when the string contains the needle.

        Validates that `contains` correctly identifies the presence of
        the needle within the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable("hello world").contains("world"))

    def testContainsReturnsFalseWhenNeedleAbsent(self):
        """Return False when the needle is not present.

        Ensures `contains` returns False when the needle cannot be found
        anywhere in the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(Stringable("hello world").contains("xyz"))

    def testContainsIgnoreCase(self):
        """Perform case-insensitive search when ignore_case is True.

        Validates that `contains` with ignore_case=True finds the needle
        regardless of letter casing differences.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(
            Stringable("Hello World").contains("world", ignore_case=True),
        )

    def testContainsAcceptsMultipleNeedles(self):
        """Return True when any needle from an iterable is found.

        Validates that `contains` with a list of needles returns True
        when any one of them is present in the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable("hello world").contains(["xyz", "hello"]))

    def testContainsRaisesTypeErrorOnInvalidType(self):
        """Raise TypeError when needles is not a string or iterable.

        Ensures `contains` validates the type of the needles argument
        before attempting the search.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").contains(42)

    # ---------------------------------------------------------- doesntContain

    def testDoesntContainReturnsTrueWhenAbsent(self):
        """Return True when the string does not contain any needle.

        Validates that `doesntContain` returns True when none of the
        provided needles are found in the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable("hello world").doesntContain("xyz"))

    def testDoesntContainReturnsFalseWhenNeedleFound(self):
        """Return False when the string contains the needle.

        Ensures `doesntContain` returns False when the string contains
        at least one of the provided needles.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(Stringable("hello world").doesntContain("hello"))

    # ------------------------------------------------------------- containsAll

    def testContainsAllReturnsTrueWhenAllPresent(self):
        """Return True when the string contains all specified needles.

        Validates that `containsAll` returns True only when every needle
        in the list is found within the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(
            Stringable("hello world foo").containsAll(["hello", "world", "foo"]),
        )

    def testContainsAllReturnsFalseWhenAnyMissing(self):
        """Return False when any needle is absent from the string.

        Ensures `containsAll` returns False when at least one needle
        cannot be found in the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(
            Stringable("hello world").containsAll(["hello", "xyz"]),
        )

    def testContainsAllRaisesTypeErrorOnNonList(self):
        """Raise TypeError when needles is not a list.

        Ensures `containsAll` enforces the list type constraint on the
        needles parameter.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").containsAll("hello")

    def testContainsAllRaisesValueErrorOnEmptyList(self):
        """Raise ValueError when needles list is empty.

        Ensures `containsAll` validates that the needles list is not
        empty before performing any checks.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            Stringable("hello").containsAll([])

    # ---------------------------------------------------------------- isAlnum

    def testIsAlnumReturnsTrueForAlphanumericString(self):
        """Return True when all characters are alphanumeric.

        Validates that `isAlnum` returns True for a string containing
        only letters and digits.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable("Hello123").isAlnum())

    def testIsAlnumReturnsFalseWhenSpecialCharsPresent(self):
        """Return False when the string contains non-alphanumeric characters.

        Ensures `isAlnum` returns False when any character in the string
        is not a letter or digit.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(Stringable("Hello!").isAlnum())

    # ---------------------------------------------------------------- isAlpha

    def testIsAlphaReturnsTrueForAlphabeticString(self):
        """Return True when all characters are alphabetic.

        Validates that `isAlpha` returns True for a string containing
        only letters.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable("Hello").isAlpha())

    def testIsAlphaReturnsFalseWhenDigitsPresent(self):
        """Return False when the string contains numeric characters.

        Ensures `isAlpha` returns False when any character in the string
        is a digit.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(Stringable("Hello1").isAlpha())

    # -------------------------------------------------------------- isDecimal

    def testIsDecimalReturnsTrueForDecimalString(self):
        """Return True when all characters are decimal digits.

        Validates that `isDecimal` returns True for a string composed
        entirely of decimal digit characters.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable("12345").isDecimal())

    def testIsDecimalReturnsFalseForNonDecimal(self):
        """Return False when the string contains non-decimal characters.

        Ensures `isDecimal` returns False when any character is not a
        decimal digit.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(Stringable("123.45").isDecimal())

    # ---------------------------------------------------------------- isDigit

    def testIsDigitReturnsTrueForDigitString(self):
        """Return True when all characters are digit characters.

        Validates that `isDigit` returns True for a string containing
        only digit characters.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable("123").isDigit())

    def testIsDigitReturnsFalseForMixedString(self):
        """Return False when the string contains non-digit characters.

        Ensures `isDigit` returns False when any character in the string
        is not a digit.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(Stringable("abc").isDigit())

    # ------------------------------------------------------------- isIdentifier

    def testIsIdentifierReturnsTrueForValidIdentifier(self):
        """Return True for a valid Python identifier.

        Validates that `isIdentifier` returns True for a string that
        satisfies Python identifier naming rules.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable("my_variable").isIdentifier())

    def testIsIdentifierReturnsFalseForInvalidIdentifier(self):
        """Return False for an invalid Python identifier.

        Ensures `isIdentifier` returns False when the string contains
        characters that violate Python identifier rules.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(Stringable("123abc").isIdentifier())

    # --------------------------------------------------------------- isLower

    def testIsLowerReturnsTrueForLowercaseString(self):
        """Return True when all cased characters are lowercase.

        Validates that `isLower` returns True for a string composed
        entirely of lowercase letters.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable("hello").isLower())

    def testIsLowerReturnsFalseWhenUppercasePresent(self):
        """Return False when any cased character is uppercase.

        Ensures `isLower` returns False when the string contains at
        least one uppercase letter.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(Stringable("Hello").isLower())

    # -------------------------------------------------------------- isNumeric

    def testIsNumericReturnsTrueForNumericString(self):
        """Return True when all characters are numeric.

        Validates that `isNumeric` returns True for a string containing
        only numeric characters.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable("42").isNumeric())

    def testIsNumericReturnsFalseForNonNumeric(self):
        """Return False when the string contains non-numeric characters.

        Ensures `isNumeric` returns False when any character is not
        numeric.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(Stringable("3.14").isNumeric())

    # ------------------------------------------------------------ isPrintable

    def testIsPrintableReturnsTrueForPrintableString(self):
        """Return True when all characters are printable.

        Validates that `isPrintable` returns True for a string containing
        only printable characters.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable("hello world").isPrintable())

    def testIsPrintableReturnsFalseForControlCharacter(self):
        """Return False when the string contains non-printable characters.

        Ensures `isPrintable` returns False when any character in the
        string is a control character.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(Stringable("hello\x00").isPrintable())

    # --------------------------------------------------------------- isSpace

    def testIsSpaceReturnsTrueForWhitespaceOnly(self):
        """Return True when the string contains only whitespace.

        Validates that `isSpace` returns True for a string composed
        entirely of whitespace characters.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable("   ").isSpace())

    def testIsSpaceReturnsFalseForNonWhitespace(self):
        """Return False when the string contains non-whitespace characters.

        Ensures `isSpace` returns False when the string has at least one
        non-whitespace character.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(Stringable("hello").isSpace())

    # --------------------------------------------------------------- isTitle

    def testIsTitleReturnsTrueForTitleCasedString(self):
        """Return True when the string is title-cased.

        Validates that `isTitle` returns True for a string where every
        word starts with an uppercase letter.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable("Hello World").isTitle())

    def testIsTitleReturnsFalseForNonTitleCased(self):
        """Return False when the string is not title-cased.

        Ensures `isTitle` returns False when any word starts with a
        lowercase letter.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(Stringable("hello world").isTitle())

    # --------------------------------------------------------------- isUpper

    def testIsUpperReturnsTrueForUppercaseString(self):
        """Return True when all cased characters are uppercase.

        Validates that `isUpper` returns True for a string composed
        entirely of uppercase letters.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable("HELLO").isUpper())

    def testIsUpperReturnsFalseWhenLowercasePresent(self):
        """Return False when any cased character is lowercase.

        Ensures `isUpper` returns False when the string contains at
        least one lowercase letter.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(Stringable("Hello").isUpper())

    # --------------------------------------------------------------- isAscii

    def testIsAsciiReturnsTrueForPureAsciiString(self):
        """Return True when all characters are 7-bit ASCII.

        Validates that `isAscii` returns True for a string containing
        only characters within the ASCII range.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable("Hello World").isAscii())

    def testIsAsciiReturnsFalseForNonAsciiString(self):
        """Return False when the string contains non-ASCII characters.

        Ensures `isAscii` returns False when the string includes any
        character outside the 7-bit ASCII range.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(Stringable("Héllo").isAscii())

    # ---------------------------------------------------------------- isJson

    def testIsJsonReturnsTrueForValidJson(self):
        """Return True when the string is valid JSON.

        Validates that `isJson` returns True for a properly formatted
        JSON string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable('{"key": "value"}').isJson())

    def testIsJsonReturnsFalseForInvalidJson(self):
        """Return False when the string is not valid JSON.

        Ensures `isJson` returns False when the string cannot be parsed
        as valid JSON.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(Stringable("not json").isJson())

    def testIsJsonReturnsTrueForJsonArray(self):
        """Return True for a valid JSON array string.

        Validates that `isJson` accepts JSON arrays, not just objects.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable("[1, 2, 3]").isJson())

    # ----------------------------------------------------------------- isUrl

    def testIsUrlReturnsTrueForValidHttpUrl(self):
        """Return True for a valid HTTP URL.

        Validates that `isUrl` accepts a well-formed HTTP URL with the
        default allowed protocols.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable("http://example.com").isUrl())

    def testIsUrlReturnsTrueForValidHttpsUrl(self):
        """Return True for a valid HTTPS URL.

        Validates that `isUrl` accepts a well-formed HTTPS URL with the
        default allowed protocols.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable("https://example.com/path").isUrl())

    def testIsUrlReturnsFalseForInvalidUrl(self):
        """Return False for an invalid or plain URL string.

        Ensures `isUrl` returns False when the string is not a properly
        formatted URL with a recognised protocol.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(Stringable("not-a-url").isUrl())

    def testIsUrlRaisesTypeErrorOnNonListProtocols(self):
        """Raise TypeError when protocols is not a list.

        Ensures `isUrl` validates the protocols argument type before
        performing any URL parsing.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("https://example.com").isUrl(protocols="https")

    def testIsUrlWithCustomProtocol(self):
        """Return True when URL uses a custom allowed protocol.

        Validates that `isUrl` accepts a URL whose scheme matches one of
        the provided custom protocols.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(
            Stringable("ftp://files.example.com").isUrl(protocols=["ftp"]),
        )

    # ----------------------------------------------------------------- isUuid

    def testIsUuidReturnsTrueForValidUuid(self):
        """Return True for a valid UUID string.

        Validates that `isUuid` accepts a well-formed UUID string
        regardless of version.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(
            Stringable("550e8400-e29b-41d4-a716-446655440000").isUuid(),
        )

    def testIsUuidReturnsFalseForInvalidUuid(self):
        """Return False for an invalid UUID string.

        Ensures `isUuid` returns False when the string cannot be parsed
        as a valid UUID.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(Stringable("not-a-uuid").isUuid())

    def testIsUuidWithVersionValidation(self):
        """Validate the UUID version when version is specified.

        Validates that `isUuid` returns True when the version matches
        and False when requesting a different version number.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        uuid4_str = "550e8400-e29b-41d4-a716-446655440000"
        # This UUID has version=4 in its variant bits
        self.assertTrue(Stringable(uuid4_str).isUuid(4))
        self.assertFalse(Stringable(uuid4_str).isUuid(1))

    def testIsUuidRaisesTypeErrorOnInvalidVersion(self):
        """Raise TypeError when version argument has an invalid type.

        Ensures `isUuid` validates the version argument type and raises
        TypeError when it is neither an int, "max", nor None.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("550e8400-e29b-41d4-a716-446655440000").isUuid(3.14)

    # ----------------------------------------------------------------- isUlid

    def testIsUlidReturnsTrueForValidUlid(self):
        """Return True for a valid ULID string.

        Validates that `isUlid` returns True for a 26-character string
        composed of valid Crockford Base32 characters.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        valid_ulid = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        self.assertTrue(Stringable(valid_ulid).isUlid())

    def testIsUlidReturnsFalseForInvalidLength(self):
        """Return False for a ULID with incorrect length.

        Ensures `isUlid` returns False when the string does not have
        exactly 26 characters.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(Stringable("TOOSHORT").isUlid())

    def testIsUlidReturnsFalseForInvalidCharacters(self):
        """Return False when the string contains invalid ULID characters.

        Ensures `isUlid` returns False when the string contains
        characters outside the Crockford Base32 alphabet (e.g., I, L).

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        invalid_ulid = "IIIIIIIIIIIIIIIIIIIIIIIIII"
        self.assertFalse(Stringable(invalid_ulid).isUlid())

    # ------------------------------------------------------------- toInteger

    def testToIntegerConvertsValidString(self):
        """Convert a numeric string to an integer.

        Validates that `toInteger` correctly parses a decimal integer
        string and returns the corresponding integer value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("42").toInteger(), 42)

    def testToIntegerWithCustomBase(self):
        """Convert a string using a custom numeric base.

        Validates that `toInteger` correctly interprets the string in
        the specified base (e.g., hexadecimal).

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("ff").toInteger(16), 255)

    def testToIntegerRaisesValueErrorOnInvalidString(self):
        """Raise ValueError when the string cannot be converted to int.

        Ensures `toInteger` propagates a ValueError when the string
        content does not represent a valid integer.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            Stringable("abc").toInteger()

    # --------------------------------------------------------------- toFloat

    def testToFloatConvertsValidString(self):
        """Convert a numeric string to a float.

        Validates that `toFloat` correctly parses a floating-point
        string and returns the corresponding float value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertAlmostEqual(Stringable("3.14").toFloat(), 3.14)

    def testToFloatRaisesValueErrorOnInvalidString(self):
        """Raise ValueError when the string cannot be converted to float.

        Ensures `toFloat` propagates a ValueError when the string
        content does not represent a valid float.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            Stringable("hello").toFloat()

    # ------------------------------------------------------------- toBoolean

    def testToBooleanReturnsTrueForTruthyValues(self):
        """Return True for common truthy string representations.

        Validates that `toBoolean` recognises "1", "true", "on", and
        "yes" (case-insensitive) as truthy values.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for value in ["1", "true", "on", "yes", "TRUE", "YES"]:
            self.assertTrue(Stringable(value).toBoolean(), msg=f"Failed for {value!r}")

    def testToBooleanReturnsFalseForFalsyValues(self):
        """Return False for non-truthy string values.

        Ensures `toBoolean` returns False for strings that do not match
        the recognised truthy representations.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for value in ["0", "false", "no", "off", ""]:
            self.assertFalse(
                Stringable(value).toBoolean(), msg=f"Failed for {value!r}",
            )

    # --------------------------------------------------------------- isPattern

    def testIsPatternReturnsTrueForWildcardMatch(self):
        """Return True when the string matches a wildcard pattern.

        Validates that `isPattern` supports '*' wildcards and returns
        True when the pattern matches the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable("hello world").isPattern("hello*"))

    def testIsPatternReturnsFalseForNoMatch(self):
        """Return False when the string does not match any pattern.

        Ensures `isPattern` returns False when no provided pattern
        matches the string content.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(Stringable("hello world").isPattern("foo*"))

    def testIsPatternIgnoreCaseOption(self):
        """Perform case-insensitive matching when ignore_case is True.

        Validates that `isPattern` with ignore_case=True matches the
        pattern regardless of letter casing.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(
            Stringable("Hello World").isPattern("hello*", ignore_case=True),
        )

    def testIsPatternRaisesValueErrorOnEmptyList(self):
        """Raise ValueError when the pattern list is empty.

        Ensures `isPattern` validates that the pattern list contains at
        least one entry before performing matching.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            Stringable("hello").isPattern([])

    def testIsPatternRaisesTypeErrorOnNonString(self):
        """Raise TypeError when pattern is not a string or list.

        Ensures `isPattern` validates the pattern type before attempting
        any matching operation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").isPattern(42)

    # ----------------------------------------------------------------- match

    def testMatchReturnsFirstRegexMatch(self):
        """Return the first regex match found in the string.

        Validates that `match` returns a Stringable containing the first
        substring that matches the provided regular expression pattern.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello world 123").match(r"\d+")
        self.assertEqual(result, Stringable("123"))

    def testMatchReturnsEmptyWhenNoMatch(self):
        """Return an empty Stringable when no regex match is found.

        Ensures `match` returns an empty Stringable rather than raising
        an exception when the pattern has no match.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello world").match(r"\d+")
        self.assertEqual(result, Stringable(""))

    def testMatchRaisesTypeErrorOnNonStringPattern(self):
        """Raise TypeError when pattern is not a string.

        Ensures `match` validates the pattern type before executing the
        regular expression search.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").match(42)

    # --------------------------------------------------------------- matchAll

    def testMatchAllReturnsAllMatches(self):
        """Return all regex matches found in the string.

        Validates that `matchAll` returns a list of all non-overlapping
        substrings that match the provided regular expression pattern.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("one1 two2 three3").matchAll(r"\d")
        self.assertEqual(result, ["1", "2", "3"])

    def testMatchAllReturnsEmptyListWhenNoMatch(self):
        """Return an empty list when no regex matches are found.

        Ensures `matchAll` returns an empty list rather than raising an
        exception when the pattern yields no matches.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello world").matchAll(r"\d+")
        self.assertEqual(result, [])

    # --------------------------------------------------------------- isMatch

    def testIsMatchReturnsTrueWhenPatternMatches(self):
        """Return True when the string matches the pattern.

        Validates that `isMatch` returns True when the provided regular
        expression pattern matches some part of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable("hello123").isMatch(r"\d+"))

    def testIsMatchReturnsFalseWhenNoMatch(self):
        """Return False when the string does not match any pattern.

        Ensures `isMatch` returns False when none of the provided
        patterns match any part of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(Stringable("hello").isMatch(r"\d+"))

    def testIsMatchWithListOfPatterns(self):
        """Return True when any pattern from a list matches the string.

        Validates that `isMatch` with a list of patterns returns True
        when at least one of them matches the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable("hello").isMatch([r"\d+", r"[a-z]+"]))

    # ------------------------------------------------------------------- test

    def testTestDelegatesToIsMatch(self):
        """Delegate pattern matching to isMatch.

        Validates that `test` is an alias for `isMatch` and produces
        identical results for the same pattern and string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("hello123")
        self.assertEqual(s.test(r"\d+"), s.isMatch(r"\d+"))

    # ----------------------------------------------------------- explode

    def testExplodeSplitsStringByDelimiter(self):
        """Split the string into a list using the given delimiter.

        Validates that `explode` produces a list of substrings split on
        every occurrence of the delimiter.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("a,b,c").explode(",")
        self.assertEqual(result, ["a", "b", "c"])

    def testExplodeWithLimitReturnsLimitedElements(self):
        """Limit the number of list elements when limit is specified.

        Validates that `explode` returns at most limit elements, with
        the last element containing the remainder of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("a,b,c").explode(",", 2)
        self.assertEqual(result, ["a", "b,c"])

    def testExplodeRaisesTypeErrorOnNonStringDelimiter(self):
        """Raise TypeError when delimiter is not a string.

        Ensures `explode` validates the delimiter type before splitting
        the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("a,b,c").explode(42)

    # ----------------------------------------------------------------- split

    def testSplitByRegexPattern(self):
        """Split the string by a regular expression pattern.

        Validates that `split` with a regex pattern returns the correct
        list of substrings.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("one1two2three").split(r"\d")
        self.assertEqual(result, ["one", "two", "three"])

    def testSplitByChunkLength(self):
        """Split the string into fixed-length chunks.

        Validates that `split` with an integer pattern divides the string
        into chunks of exactly that number of characters.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("abcdef").split(2)
        self.assertEqual(result, ["ab", "cd", "ef"])

    def testSplitRaisesTypeErrorOnInvalidPattern(self):
        """Raise TypeError when pattern is neither a string nor an integer.

        Ensures `split` validates the pattern type before performing any
        splitting operation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").split(3.14)

    # ---------------------------------------------------------------- ucsplit

    def testUcsplitSplitsByUppercaseLetters(self):
        """Split the string at uppercase letter boundaries.

        Validates that `ucsplit` correctly partitions a camelCase or
        StudlyCaps string into its constituent words.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("HelloWorldFoo").ucsplit()
        self.assertIn("Hello", result)
        self.assertIn("World", result)
        self.assertIn("Foo", result)

    def testUcsplitOnLowercaseStringReturnsEntireWord(self):
        """Return the whole string in a list when no split occurs.

        Ensures `ucsplit` returns a single-element list when the string
        contains no uppercase boundaries.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello").ucsplit()
        self.assertEqual(result, ["hello"])
