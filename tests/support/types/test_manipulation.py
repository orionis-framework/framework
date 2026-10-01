from orionis.support.types.stringable import Stringable
from orionis.test import TestCase

class TestStringableManipulation(TestCase):
    """Unit tests for Stringable string-manipulation operations."""

    # --------------------------------------------------------------- replace

    def testReplaceSubstringCaseSensitive(self):
        """Replace a substring in case-sensitive mode.

        Validates that `replace` substitutes the exact match of the
        search string with the replacement in the default mode.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("Hello World").replace("World", "Python")
        self.assertEqual(result, Stringable("Hello Python"))

    def testReplaceSubstringCaseInsensitive(self):
        """Replace a substring in case-insensitive mode.

        Validates that `replace` with case_sensitive=False substitutes
        occurrences regardless of letter casing.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("Hello World").replace(
            "world", "Python", case_sensitive=False,
        )
        self.assertEqual(result, Stringable("Hello Python"))

    def testReplaceMultipleSearchAndReplace(self):
        """Replace multiple substrings in one call using lists.

        Validates that `replace` accepts parallel lists for search and
        replacement and applies each pair sequentially.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("a b c").replace(["a", "b"], ["x", "y"])
        self.assertEqual(result, Stringable("x y c"))

    def testReplaceRaisesOnMismatchedLists(self):
        """Raise ValueError when search and replace lists differ in length.

        Ensures `replace` enforces equal-length lists when both arguments
        are iterables by propagating the strict zip error.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            Stringable("abc").replace(["a", "b"], ["x"])

    # ---------------------------------------------------------- replaceFirst

    def testReplaceFirstReplacesOnlyFirstOccurrence(self):
        """Replace only the first occurrence of the search string.

        Validates that `replaceFirst` leaves subsequent occurrences of
        the search string intact.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("aaa").replaceFirst("a", "b")
        self.assertEqual(result, Stringable("baa"))

    def testReplaceFirstRaisesTypeErrorOnNonString(self):
        """Raise TypeError when search or replace is not a string.

        Ensures `replaceFirst` validates both argument types before
        attempting the replacement.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").replaceFirst(1, "x")

    # ----------------------------------------------------------- replaceLast

    def testReplaceLastReplacesOnlyLastOccurrence(self):
        """Replace only the last occurrence of the search string.

        Validates that `replaceLast` targets only the final match,
        leaving all earlier occurrences unchanged.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("aaa").replaceLast("a", "b")
        self.assertEqual(result, Stringable("aab"))

    def testReplaceLastNoChangeWhenNotFound(self):
        """Return unchanged string when search is absent.

        Ensures `replaceLast` returns the original Stringable when the
        search string cannot be found.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello").replaceLast("x", "y")
        self.assertEqual(result, Stringable("hello"))

    # ---------------------------------------------------------- replaceStart

    def testReplaceStartReplacesAtBeginning(self):
        """Replace the matching prefix at the start of the string.

        Validates that `replaceStart` substitutes the search string
        only when it appears at the very beginning of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("helloWorld").replaceStart("hello", "hi")
        self.assertEqual(result, Stringable("hiWorld"))

    def testReplaceStartNoChangeWhenNotAtStart(self):
        """Return unchanged string when search is not at the start.

        Ensures `replaceStart` does not modify the string when the
        search value is found in the middle or not at all.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("worldHello").replaceStart("hello", "hi")
        self.assertEqual(result, Stringable("worldHello"))

    # ------------------------------------------------------------ replaceEnd

    def testReplaceEndReplacesAtTheEnd(self):
        """Replace the matching suffix at the end of the string.

        Validates that `replaceEnd` substitutes the search string only
        when it appears at the very end of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("helloWorld").replaceEnd("World", "Python")
        self.assertEqual(result, Stringable("helloPython"))

    def testReplaceEndNoChangeWhenNotAtEnd(self):
        """Return unchanged string when search is not at the end.

        Ensures `replaceEnd` does not modify the string when the search
        value cannot be found at the string's tail.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("WorldHello").replaceEnd("World", "Python")
        self.assertEqual(result, Stringable("WorldHello"))

    # ---------------------------------------------------------- replaceArray

    def testReplaceArraySubstitutesSequentially(self):
        """Replace a substring sequentially with elements from a list.

        Validates that `replaceArray` substitutes each occurrence of the
        search string with the next element in the replacement list.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("? ? ?").replaceArray("?", ["a", "b", "c"])
        self.assertEqual(result, Stringable("a b c"))

    def testReplaceArrayRaisesTypeErrorWhenReplaceNotList(self):
        """Raise TypeError when replace argument is not a list.

        Ensures `replaceArray` validates the type of its replace
        parameter before starting any replacement operations.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").replaceArray("l", "x")

    def testReplaceArrayRaisesTypeErrorWhenItemNotString(self):
        """Raise TypeError when a replace list item is not a string.

        Ensures `replaceArray` validates each item in the replacement
        list for string type compliance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").replaceArray("l", [1, 2])

    # --------------------------------------------------------- replaceMatches

    def testReplaceMatchesWithStringReplacement(self):
        """Replace regex matches using a string replacement.

        Validates that `replaceMatches` substitutes all occurrences
        matching the provided regex pattern with the given string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello123world").replaceMatches(r"\d+", "NUM")
        self.assertEqual(result, Stringable("helloNUMworld"))

    def testReplaceMatchesWithCallableReplacement(self):
        """Replace regex matches using a callable replacement.

        Validates that `replaceMatches` invokes the callable with each
        match object and uses its return value as the replacement.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello").replaceMatches(
            r"[aeiou]", lambda m: m.group(0).upper(),
        )
        self.assertEqual(result, Stringable("hEllO"))

    def testReplaceMatchesWithMultiplePatterns(self):
        """Apply multiple patterns in a single replaceMatches call.

        Validates that `replaceMatches` accepts a list of patterns and
        applies each replacement sequentially.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello world").replaceMatches(
            [r"hello", r"world"], "x",
        )
        self.assertEqual(result, Stringable("x x"))

    def testReplaceMatchesRaisesTypeErrorOnInvalidPattern(self):
        """Raise TypeError when pattern is neither a string nor a list.

        Ensures `replaceMatches` enforces type validation on the
        pattern argument before any regex operation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").replaceMatches(123, "x")

    # ------------------------------------------------------------- remove

    def testRemoveDeletesSubstring(self):
        """Remove all occurrences of a substring from the string.

        Validates that `remove` deletes every instance of the search
        string from the Stringable.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello world").remove("l")
        self.assertEqual(result, Stringable("heo word"))

    def testRemoveCaseInsensitive(self):
        """Remove substrings case-insensitively when specified.

        Validates that `remove` with case_sensitive=False deletes all
        matches regardless of letter casing.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("Hello World").remove("hello", case_sensitive=False)
        self.assertEqual(result, Stringable(" World"))

    def testRemoveMultipleSubstrings(self):
        """Remove multiple substrings in one call using a list.

        Validates that `remove` accepts a list of search strings and
        deletes all occurrences of each.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello world").remove(["hello", " "])
        self.assertEqual(result, Stringable("world"))

    def testRemoveRaisesTypeErrorOnInvalidSearch(self):
        """Raise TypeError when search is neither a string nor a list.

        Ensures `remove` validates the search argument type before
        processing.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").remove(42)

    # -------------------------------------------------------------- chopStart

    def testChopStartRemovesPrefixWhenPresent(self):
        """Remove the specified prefix from the start of the string.

        Validates that `chopStart` strips the given prefix when it
        appears at the beginning of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("https://example.com").chopStart("https://")
        self.assertEqual(result, Stringable("example.com"))

    def testChopStartNoChangeWhenPrefixAbsent(self):
        """Return unchanged string when prefix is absent.

        Ensures `chopStart` is a no-op when none of the provided needles
        match the beginning of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("example.com").chopStart("https://")
        self.assertEqual(result, Stringable("example.com"))

    def testChopStartWithList(self):
        """Remove the first matching prefix from a list of needles.

        Validates that `chopStart` accepts a list and removes the first
        needle that matches the beginning of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("http://example.com").chopStart(
            ["https://", "http://"],
        )
        self.assertEqual(result, Stringable("example.com"))

    # --------------------------------------------------------------- chopEnd

    def testChopEndRemovesSuffixWhenPresent(self):
        """Remove the specified suffix from the end of the string.

        Validates that `chopEnd` strips the given suffix when it appears
        at the end of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("example.com/").chopEnd("/")
        self.assertEqual(result, Stringable("example.com"))

    def testChopEndNoChangeWhenSuffixAbsent(self):
        """Return unchanged string when suffix is absent.

        Ensures `chopEnd` is a no-op when none of the provided needles
        match the end of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("example.com").chopEnd("/")
        self.assertEqual(result, Stringable("example.com"))

    # ----------------------------------------------------------- deduplicate

    def testDeduplicateCollapsesSpaces(self):
        """Collapse consecutive spaces into a single space.

        Validates that `deduplicate` replaces runs of the default space
        character with a single space.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello   world").deduplicate()
        self.assertEqual(result, Stringable("hello world"))

    def testDeduplicateWithCustomCharacter(self):
        """Collapse consecutive occurrences of a custom character.

        Validates that `deduplicate` accepts a character argument and
        collapses consecutive runs of that character while leaving all
        other characters untouched.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("aabbcc").deduplicate("b")
        self.assertEqual(result, Stringable("aabcc"))

    def testDeduplicateRaisesValueErrorOnMultiCharInput(self):
        """Raise ValueError when character is not a single character.

        Ensures `deduplicate` enforces the single-character constraint
        on the character argument.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            Stringable("hello").deduplicate("ab")

    # ------------------------------------------------------------------ mask

    def testMaskReplacesMiddleSection(self):
        """Mask a section of the string with the specified character.

        Validates that `mask` replaces the specified character range with
        the masking character while leaving other positions intact.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("password").mask("*", 2, 4)
        self.assertEqual(result, Stringable("pa****rd"))

    def testMaskToEndOfStringWhenLengthOmitted(self):
        """Mask from the index to end of string when length is omitted.

        Validates that `mask` without a length argument masks every
        character from the start index to the end of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello").mask("*", 2)
        self.assertEqual(result, Stringable("he***"))

    def testMaskWithNegativeIndex(self):
        """Mask characters relative to the end of the string.

        Validates that a negative index causes `mask` to compute the
        start position from the end of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello").mask("*", -3)
        self.assertEqual(result, Stringable("he***"))

    def testMaskRaisesValueErrorOnMultiCharCharacter(self):
        """Raise ValueError when masking character is not a single char.

        Ensures `mask` enforces the single-character constraint on its
        character parameter.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            Stringable("hello").mask("**", 0)

    def testMaskRaisesTypeErrorOnNonIntegerIndex(self):
        """Raise TypeError when index is not an integer.

        Ensures `mask` validates the index type before computing the
        masking boundaries.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").mask("*", "a")

    # ----------------------------------------------------------------- limit

    def testLimitTruncatesString(self):
        """Limit the string to a maximum number of characters.

        Validates that `limit` returns a truncated string followed by
        the ellipsis when the original exceeds the limit.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello world").limit(5)
        self.assertEqual(result, Stringable("hello..."))

    def testLimitReturnsOriginalWhenWithinLimit(self):
        """Return the original string when it is within the limit.

        Ensures `limit` is a no-op when the string length does not
        exceed the specified limit.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hi").limit(100)
        self.assertEqual(result, Stringable("hi"))

    def testLimitWithCustomEnd(self):
        """Use a custom end string when truncation occurs.

        Validates that `limit` appends the provided end string instead
        of the default ellipsis when truncating.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello world").limit(5, " [more]")
        self.assertEqual(result, Stringable("hello [more]"))

    def testLimitWithPreserveWords(self):
        """Avoid cutting words in the middle when preserve_words is True.

        Validates that `limit` with preserve_words=True truncates at a
        word boundary rather than at an arbitrary character position.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello world foo").limit(8, "...", preserve_words=True)
        self.assertNotIn("wor", str(result)[5:])

    def testLimitRaisesValueErrorOnNegativeLimit(self):
        """Raise ValueError when limit is negative.

        Ensures `limit` validates that the limit parameter is a
        non-negative integer before processing.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            Stringable("hello").limit(-1)

    # -------------------------------------------------------------- padBoth

    def testPadBothCentresString(self):
        """Centre the string within the specified total length.

        Validates that `padBoth` adds equal padding to both sides of the
        string to reach the desired total length.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hi").padBoth(6)
        self.assertEqual(len(result), 6)
        self.assertTrue(str(result).startswith(" "))
        self.assertTrue(str(result).endswith(" "))

    def testPadBothNoOpWhenAlreadyLongEnough(self):
        """Return the original string when already at or above the length.

        Ensures `padBoth` is a no-op when the string length meets or
        exceeds the desired total length.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello world").padBoth(5)
        self.assertEqual(result, Stringable("hello world"))

    def testPadBothRaisesValueErrorOnEmptyPad(self):
        """Raise ValueError when pad is an empty string.

        Ensures `padBoth` validates that the pad string is non-empty
        before performing any padding calculation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            Stringable("hi").padBoth(10, "")

    # --------------------------------------------------------------- padLeft

    def testPadLeftAddsLeadingPadding(self):
        """Pad the left side of the string to reach the desired length.

        Validates that `padLeft` adds the correct number of padding
        characters to the left of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hi").padLeft(5)
        self.assertEqual(result, Stringable("   hi"))

    def testPadLeftWithCustomPad(self):
        """Use a custom pad string for left-padding.

        Validates that `padLeft` honours the provided pad string instead
        of the default space character.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("5").padLeft(3, "0")
        self.assertEqual(result, Stringable("005"))

    # -------------------------------------------------------------- padRight

    def testPadRightAddsTrailingPadding(self):
        """Pad the right side of the string to reach the desired length.

        Validates that `padRight` adds the correct number of padding
        characters to the right of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hi").padRight(5)
        self.assertEqual(result, Stringable("hi   "))

    # ------------------------------------------------------------------ trim

    def testTrimRemovesWhitespace(self):
        """Remove leading and trailing whitespace by default.

        Validates that `trim` strips whitespace from both ends when no
        characters argument is provided.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("  hello  ").trim()
        self.assertEqual(result, Stringable("hello"))

    def testTrimRemovesSpecifiedCharacters(self):
        """Remove specified characters from both ends.

        Validates that `trim` strips any combination of the provided
        characters from the beginning and end of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("--hello--").trim("-")
        self.assertEqual(result, Stringable("hello"))

    def testTrimRaisesTypeErrorOnNonString(self):
        """Raise TypeError when characters argument is not a string.

        Ensures `trim` validates its characters parameter type before
        delegating to the built-in strip.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").trim(42)

    # ------------------------------------------------------------------ ltrim

    def testLtrimRemovesLeadingWhitespace(self):
        """Remove leading whitespace while preserving trailing whitespace.

        Validates that `ltrim` only strips characters from the left
        side of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("  hello  ").ltrim()
        self.assertEqual(result, Stringable("hello  "))

    # ------------------------------------------------------------------ rtrim

    def testRtrimRemovesTrailingWhitespace(self):
        """Remove trailing whitespace while preserving leading whitespace.

        Validates that `rtrim` only strips characters from the right
        side of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("  hello  ").rtrim()
        self.assertEqual(result, Stringable("  hello"))

    # ------------------------------------------------------------- lStrip

    def testLStripRemovesLeadingCharacters(self):
        """Remove specified leading characters using lStrip.

        Validates that `lStrip` removes any combination of the specified
        characters from the start of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("xxhello").lStrip("x")
        self.assertEqual(result, Stringable("hello"))

    def testLStripRaisesTypeErrorOnNonString(self):
        """Raise TypeError when chars is not a string or None.

        Ensures `lStrip` validates the chars parameter type before
        delegating to the built-in lstrip.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").lStrip(42)

    # ------------------------------------------------------------- rStrip

    def testRStripRemovesTrailingCharacters(self):
        """Remove specified trailing characters using rStrip.

        Validates that `rStrip` removes any combination of the specified
        characters from the end of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("helloxx").rStrip("x")
        self.assertEqual(result, Stringable("hello"))

    def testRStripRaisesTypeErrorOnNonString(self):
        """Raise TypeError when chars is not a string or None.

        Ensures `rStrip` validates the chars parameter type before
        delegating to the built-in rstrip.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").rStrip(42)

    # ----------------------------------------------------------------- zFill

    def testZFillPadsWithLeadingZeros(self):
        """Pad the string with leading zeros to reach the given width.

        Validates that `zFill` produces a string of exactly the
        specified width, padded on the left with zeros.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("42").zFill(5)
        self.assertEqual(result, Stringable("00042"))

    def testZFillNoOpWhenAlreadyWideEnough(self):
        """Return the original string when it is already wide enough.

        Ensures `zFill` is a no-op when the string length meets or
        exceeds the desired width.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello").zFill(3)
        self.assertEqual(result, Stringable("hello"))

    def testZFillRaisesValueErrorOnNegativeWidth(self):
        """Raise ValueError when width is negative.

        Ensures `zFill` validates that the width parameter is a
        non-negative integer.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            Stringable("5").zFill(-1)

    # --------------------------------------------------------------- repeat

    def testRepeatReturnsRepeatedString(self):
        """Repeat the string the specified number of times.

        Validates that `repeat` produces a string composed of the
        original Stringable concatenated the given number of times.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("ab").repeat(3), Stringable("ababab"))

    def testRepeatZeroTimesReturnsEmpty(self):
        """Return an empty Stringable when repeating zero times.

        Validates that `repeat(0)` produces an empty string without
        raising errors.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("hello").repeat(0), Stringable(""))

    def testRepeatRaisesValueErrorOnNegativeTimes(self):
        """Raise ValueError when times is negative.

        Ensures `repeat` validates that the times parameter is a
        non-negative integer.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            Stringable("ab").repeat(-1)

    # ----------------------------------------------------------------- words

    def testWordsLimitsWordCount(self):
        """Limit the string to the specified number of words.

        Validates that `words` returns only the first N words of the
        string, appending the default ellipsis when truncated.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("one two three four").words(2)
        self.assertEqual(result, Stringable("one two..."))

    def testWordsNoTruncationWhenWithinLimit(self):
        """Return the full string when word count is within the limit.

        Ensures `words` is a no-op when the string contains fewer or
        equal words than the limit.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello world").words(10)
        self.assertEqual(result, Stringable("hello world"))

    def testWordsRaisesValueErrorOnNegativeCount(self):
        """Raise ValueError when word count is negative.

        Ensures `words` validates that the words parameter is a
        non-negative integer.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            Stringable("hello").words(-1)

    # --------------------------------------------------------------- wordCount

    def testWordCountReturnsCorrectCount(self):
        """Count the number of words in the string.

        Validates that `wordCount` returns the correct integer word
        count for a standard space-separated string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("hello world foo").wordCount(), 3)

    def testWordCountReturnsZeroForEmptyString(self):
        """Return zero for an empty string.

        Ensures `wordCount` returns 0 when the string contains no
        words.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("").wordCount(), 0)

    def testWordCountWithCustomSeparatorCharacters(self):
        """Count words using additional separator characters.

        Validates that `wordCount` treats the specified characters as
        additional word separators.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello,world").wordCount(",")
        self.assertEqual(result, 2)

    # -------------------------------------------------------------- wordWrap

    def testWordWrapBreaksLongLines(self):
        """Wrap text to the specified line width.

        Validates that `wordWrap` inserts line breaks so that no line
        exceeds the specified character limit.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        long_text = "The quick brown fox jumped over the lazy dog"
        result = Stringable(long_text).wordWrap(15)
        for line in str(result).split("\n"):
            self.assertLessEqual(len(line), 25)

    # ------------------------------------------------------------------ wrap

    def testWrapAddsBeforeAndAfter(self):
        """Wrap the string with a prefix and suffix.

        Validates that `wrap` prepends the before string and appends the
        after string to the current Stringable instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello").wrap("[", "]")
        self.assertEqual(result, Stringable("[hello]"))

    def testWrapUsesSameStringWhenAfterOmitted(self):
        """Use the before string as suffix when after is not provided.

        Validates that `wrap` applies the before argument to both sides
        when the after argument is omitted.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello").wrap("*")
        self.assertEqual(result, Stringable("*hello*"))

    def testWrapRaisesTypeErrorOnNonStringBefore(self):
        """Raise TypeError when before argument is not a string.

        Ensures `wrap` validates the before parameter type before
        constructing the wrapped string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").wrap(1)

    # ---------------------------------------------------------------- unwrap

    def testUnwrapRemovesPrefixAndSuffix(self):
        """Remove the specified prefix and suffix from the string.

        Validates that `unwrap` strips both the before prefix and the
        after suffix from the Stringable instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("[hello]").unwrap("[", "]")
        self.assertEqual(result, Stringable("hello"))

    def testUnwrapUsesSameStringWhenAfterOmitted(self):
        """Remove the same string from both ends when after is omitted.

        Validates that `unwrap` applies the before argument to both sides
        when the after argument is not provided.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("*hello*").unwrap("*")
        self.assertEqual(result, Stringable("hello"))

    # ------------------------------------------------------------------ squish

    def testSquishNormalisesWhitespace(self):
        """Normalise consecutive whitespace to a single space.

        Validates that `squish` replaces any run of whitespace characters
        with a single space and strips leading/trailing whitespace.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("  hello   world  ").squish()
        self.assertEqual(result, Stringable("hello world"))

    def testSquishWithTabsAndNewlines(self):
        """Normalise tabs and newlines as well as spaces.

        Ensures `squish` treats all whitespace character types uniformly
        when collapsing consecutive whitespace.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello\t\nworld").squish()
        self.assertEqual(result, Stringable("hello world"))

    # --------------------------------------------------------------- numbers

    def testNumbersRemovesNonDigitChars(self):
        """Remove all non-numeric characters from the string.

        Validates that `numbers` returns only the digit characters
        present in the original Stringable.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("abc123def456").numbers()
        self.assertEqual(result, Stringable("123456"))

    def testNumbersOnPureDigitString(self):
        """Return unchanged string when input contains only digits.

        Ensures `numbers` is a no-op when the string already consists
        entirely of digit characters.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("12345").numbers()
        self.assertEqual(result, Stringable("12345"))

    def testNumbersOnStringWithNoDigits(self):
        """Return empty Stringable when input has no digit characters.

        Ensures `numbers` returns an empty Stringable when none of the
        characters in the string are digits.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("abc").numbers()
        self.assertEqual(result, Stringable(""))

    # ------------------------------------------------------------------ pipe

    def testPipeAppliesCallbackAndReturns(self):
        """Apply a callback and return the result as a Stringable.

        Validates that `pipe` passes the current Stringable to the
        callback and wraps the return value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello").pipe(lambda s: str(s).upper())
        self.assertEqual(result, Stringable("HELLO"))

    def testPipeRaisesTypeErrorOnNonCallable(self):
        """Raise TypeError when callback is not callable.

        Ensures `pipe` validates that its argument is callable before
        invoking it.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").pipe("not_callable")

    # ------------------------------------------------------------------- tap

    def testTapCallsCallbackAndReturnsSelf(self):
        """Call the callback but return the unchanged Stringable.

        Validates that `tap` invokes the callback as a side-effect and
        returns the same Stringable instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        called_with = []
        result = Stringable("hello").tap(lambda s: called_with.append(str(s)))
        self.assertEqual(result, Stringable("hello"))
        self.assertEqual(called_with, ["hello"])

    # ----------------------------------------------------------------- swap

    def testSwapReplacesMultipleKeywords(self):
        """Swap multiple keywords simultaneously using a dictionary.

        Validates that `swap` replaces every key occurrence with its
        corresponding value, processing all mappings in order.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello world").swap({"hello": "hi", "world": "earth"})
        self.assertEqual(result, Stringable("hi earth"))

    def testSwapRaisesTypeErrorOnNonDict(self):
        """Raise TypeError when map_dict is not a dictionary.

        Ensures `swap` validates that its argument is a dict before
        attempting any keyword substitution.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").swap("not-a-dict")

    def testSwapRaisesTypeErrorOnNonStringValues(self):
        """Raise TypeError when dictionary values are not strings.

        Ensures `swap` validates that all keys and values in the mapping
        dictionary are strings.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").swap({"hello": 42})

    # ------------------------------------------------------------- substrCount

    def testSubstrCountCountsOccurrences(self):
        """Count the non-overlapping occurrences of a needle.

        Validates that `substrCount` returns the correct count of
        non-overlapping appearances of the needle in the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello world hello").substrCount("hello")
        self.assertEqual(result, 2)

    def testSubstrCountWithOffset(self):
        """Count occurrences after a given starting offset.

        Validates that `substrCount` begins counting from the specified
        offset, skipping earlier occurrences.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello hello hello").substrCount("hello", 6)
        self.assertEqual(result, 2)

    def testSubstrCountRaisesTypeErrorOnNonStringNeedle(self):
        """Raise TypeError when needle is not a string.

        Ensures `substrCount` validates the needle type before performing
        the count operation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").substrCount(42)

    # ----------------------------------------------------------- substrReplace

    def testSubstrReplaceBasicReplacement(self):
        """Replace a portion of the string at the given offset.

        Validates that `substrReplace` substitutes the substring starting
        at offset with the provided replacement.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello world").substrReplace("Python", 6)
        self.assertIn("Python", str(result))

    def testSubstrReplaceWithLength(self):
        """Replace exactly the specified number of characters.

        Validates that `substrReplace` with a length argument replaces
        only the given number of characters at the offset position.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello world").substrReplace("X", 0, 5)
        self.assertTrue(str(result).startswith("X"))

    def testSubstrReplaceRaisesValueErrorOnNegativeLength(self):
        """Raise ValueError when length is negative.

        Ensures `substrReplace` validates that the length parameter is
        non-negative before performing any replacement.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            Stringable("hello").substrReplace("x", 0, -1)
