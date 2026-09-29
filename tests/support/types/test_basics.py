from orionis.test import TestCase
from orionis.support.types.stringable import Stringable

class TestStringableBasics(TestCase):
    """Unit tests for basic Stringable string operations."""

    # ------------------------------------------------------------------ after

    def testAfterReturnsSubstringAfterFirstOccurrence(self):
        """Return the substring after the first occurrence.

        Validates that `after` correctly locates the search string and
        returns everything following its first occurrence.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("hello world hello")
        self.assertEqual(s.after("hello"), Stringable(" world hello"))

    def testAfterReturnsOriginalWhenNotFound(self):
        """Return the original string when search value is absent.

        Ensures `after` falls back to the original string when the
        search substring does not exist.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("hello world")
        self.assertEqual(s.after("xyz"), Stringable("hello world"))

    def testAfterEmptySearchString(self):
        """Return the full string when search is an empty string.

        Verifies that an empty search string returns the original value
        because find("") returns index 0.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("hello")
        self.assertEqual(s.after(""), Stringable("hello"))

    # -------------------------------------------------------------- afterLast

    def testAfterLastReturnsSubstringAfterLastOccurrence(self):
        """Return the substring after the last occurrence.

        Validates that `afterLast` locates the *last* match and returns
        everything following it.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("foo/bar/baz")
        self.assertEqual(s.afterLast("/"), Stringable("baz"))

    def testAfterLastReturnsOriginalWhenNotFound(self):
        """Return the original string when search value is absent.

        Ensures `afterLast` falls back to the original string when the
        search substring does not exist.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("hello")
        self.assertEqual(s.afterLast("x"), Stringable("hello"))

    # ----------------------------------------------------------------- before

    def testBeforeReturnsSubstringBeforeFirstOccurrence(self):
        """Return the substring before the first occurrence.

        Validates that `before` correctly extracts everything preceding
        the first occurrence of the search string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("hello world hello")
        self.assertEqual(s.before("world"), Stringable("hello "))

    def testBeforeReturnsOriginalWhenNotFound(self):
        """Return the original string when search value is absent.

        Ensures `before` falls back to the original string when the
        search substring does not exist.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("hello world")
        self.assertEqual(s.before("xyz"), Stringable("hello world"))

    # ------------------------------------------------------------- beforeLast

    def testBeforeLastReturnsSubstringBeforeLastOccurrence(self):
        """Return the substring before the last occurrence.

        Validates that `beforeLast` extracts everything preceding the
        last match of the search string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("foo/bar/baz")
        self.assertEqual(s.beforeLast("/"), Stringable("foo/bar"))

    def testBeforeLastReturnsOriginalWhenNotFound(self):
        """Return the original string when search value is absent.

        Ensures `beforeLast` falls back to the original string when the
        search substring does not exist.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("hello")
        self.assertEqual(s.beforeLast("x"), Stringable("hello"))

    # --------------------------------------------------------------- between

    def testBetweenExtractsSubstringBetweenDelimiters(self):
        """Extract the substring between two delimiters.

        Validates that `between` correctly isolates the content located
        between the starting and ending delimiter strings.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("[hello]")
        self.assertEqual(s.between("[", "]"), Stringable("hello"))

    def testBetweenReturnsEmptyWhenStartDelimiterMissing(self):
        """Return empty string when starting delimiter is absent.

        Ensures `between` returns an empty Stringable when the opening
        delimiter cannot be located.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("hello]")
        self.assertEqual(s.between("[", "]"), Stringable(""))

    def testBetweenReturnsEmptyWhenEndDelimiterMissing(self):
        """Return empty string when ending delimiter is absent.

        Ensures `between` returns an empty Stringable when the closing
        delimiter cannot be located after the opening one.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("[hello")
        self.assertEqual(s.between("[", "]"), Stringable(""))

    def testBetweenRaisesTypeErrorOnInvalidDelimiters(self):
        """Raise TypeError when delimiters are not strings.

        Verifies that passing non-string delimiters to `between` raises
        a TypeError to enforce the expected contract.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("text")
        with self.assertRaises(TypeError):
            s.between(1, "]")

    # ----------------------------------------------------------- betweenFirst

    def testBetweenFirstExtractsFirstPairContent(self):
        """Extract content between the first pair of delimiters.

        Validates that `betweenFirst` isolates content between the very
        first occurrence of both opening and closing delimiters.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("[a][b]")
        self.assertEqual(s.betweenFirst("[", "]"), Stringable("a"))

    # --------------------------------------------------------------- append

    def testAppendJoinsStrings(self):
        """Append one or more strings to the end.

        Validates that `append` concatenates all provided values to the
        current Stringable instance in order.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("hello")
        self.assertEqual(s.append(" world", "!"), Stringable("hello world!"))

    def testAppendRaisesTypeErrorOnNonString(self):
        """Raise TypeError when a non-string value is appended.

        Ensures `append` enforces type validation on all provided
        arguments before performing any concatenation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("hello")
        with self.assertRaises(TypeError):
            s.append(42)

    # --------------------------------------------------------------- prepend

    def testPrependJoinsStrings(self):
        """Prepend one or more strings to the beginning.

        Validates that `prepend` inserts all provided values before the
        current Stringable instance in the supplied order.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("world")
        self.assertEqual(s.prepend("hello ", "dear "), Stringable("hello dear world"))

    def testPrependRaisesTypeErrorOnNonString(self):
        """Raise TypeError when a non-string value is prepended.

        Ensures `prepend` enforces type validation on all arguments
        before performing any concatenation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("world")
        with self.assertRaises(TypeError):
            s.prepend(10)

    # --------------------------------------------------------------- newLine

    def testNewLineAppendsDefaultSingleNewline(self):
        """Append a single newline by default.

        Validates that calling `newLine` without a count argument appends
        exactly one newline character.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("hello")
        self.assertEqual(s.newLine(), Stringable("hello\n"))

    def testNewLineAppendsMultipleNewlines(self):
        """Append multiple newlines when count is specified.

        Ensures that passing a count value causes `newLine` to append the
        correct number of newline characters.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("hello")
        self.assertEqual(s.newLine(3), Stringable("hello\n\n\n"))

    # ----------------------------------------------------------------- value

    def testValueReturnsPlainString(self):
        """Return the underlying plain string value.

        Validates that `value` returns a regular Python `str` equal to
        the content of the Stringable instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("hello")
        self.assertEqual(s.value(), "hello")
        self.assertIsInstance(s.value(), str)

    # ---------------------------------------------------------------- length

    def testLengthReturnsCharacterCount(self):
        """Return the number of characters in the string.

        Validates that `length` returns an integer matching the expected
        character count of the current string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("hello").length(), 5)
        self.assertEqual(Stringable("").length(), 0)

    # --------------------------------------------------------------- reverse

    def testReverseReturnsReversedString(self):
        """Return the string with characters in reverse order.

        Validates that `reverse` correctly mirrors the full sequence of
        characters of the Stringable instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("hello").reverse(), Stringable("olleh"))

    def testReverseOnEmptyString(self):
        """Return an empty Stringable when reversing an empty string.

        Ensures that reversing an empty string returns an empty Stringable
        without raising any errors.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("").reverse(), Stringable(""))

    # ------------------------------------------------------------------ take

    def testTakePositiveCharactersFromStart(self):
        """Take a specified number of characters from the start.

        Validates that `take` with a positive limit returns the first N
        characters of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("hello world").take(5), Stringable("hello"))

    def testTakeNegativeCharactersFromEnd(self):
        """Take a specified number of characters from the end.

        Validates that `take` with a negative limit returns the last N
        characters of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("hello world").take(-5), Stringable("world"))

    def testTakeRaisesTypeErrorOnNonInteger(self):
        """Raise TypeError when limit is not an integer.

        Ensures `take` validates its argument type before processing,
        raising TypeError for non-integer inputs.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").take("3")

    # ---------------------------------------------------------------- substr

    def testSubstrExtractsFromStart(self):
        """Extract a substring from a given start position.

        Validates that `substr` with a start index and no length returns
        the remaining string from that position.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("hello world").substr(6), Stringable("world"))

    def testSubstrExtractsWithLength(self):
        """Extract a substring of a specified length from a start position.

        Ensures `substr` correctly slices the string when both start and
        length are provided.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("hello world").substr(0, 5), Stringable("hello"))

    def testSubstrRaisesTypeErrorOnInvalidStart(self):
        """Raise TypeError when start is not an integer.

        Verifies `substr` enforces the integer type constraint on its
        start parameter.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").substr("a")

    # --------------------------------------------------------------- charAt

    def testCharAtReturnsCorrectCharacter(self):
        """Return the character at a given index.

        Validates that `charAt` returns the correct character for a valid
        index within the bounds of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("hello").charAt(1), "e")

    def testCharAtReturnsFalseForOutOfBoundsIndex(self):
        """Return False when index is out of bounds.

        Ensures `charAt` returns `False` rather than raising an exception
        when an index exceeds the string length.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(Stringable("hi").charAt(99))

    def testCharAtNegativeIndex(self):
        """Return the character at a negative index.

        Validates that negative indices work correctly, accessing
        characters from the end of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("hello").charAt(-1), "o")

    def testCharAtRaisesTypeErrorOnNonInteger(self):
        """Raise TypeError when index is not an integer.

        Ensures `charAt` enforces the integer type constraint before
        accessing the underlying string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").charAt("a")

    # -------------------------------------------------------------- position

    def testPositionReturnsIndexOfFirstOccurrence(self):
        """Return the index of the first occurrence of a substring.

        Validates that `position` correctly identifies the zero-based
        index where the needle first appears.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("hello world").position("world"), 6)

    def testPositionReturnsFalseWhenNotFound(self):
        """Return False when the needle is not found.

        Ensures `position` returns `False` rather than raising an
        exception when the needle is absent from the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(Stringable("hello").position("xyz"))

    def testPositionWithOffset(self):
        """Respect the offset parameter when searching.

        Validates that `position` begins its search at the specified
        offset, skipping earlier occurrences.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("aabbaa").position("a", 4)
        self.assertEqual(result, 4)

    def testPositionRaisesTypeErrorOnNonStringNeedle(self):
        """Raise TypeError when needle is not a string.

        Ensures `position` validates needle type before performing the
        search operation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").position(42)

    # ---------------------------------------------------------------- finish

    def testFinishAppendsCapIfAbsent(self):
        """Append the cap string when it is missing at the end.

        Validates that `finish` ensures the string ends with the specified
        cap by appending it when not already present.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("hello").finish("/"), Stringable("hello/"))

    def testFinishDoesNotDuplicateCapIfPresent(self):
        """Preserve the cap when the string already ends with it.

        Ensures `finish` does not append a duplicate cap when the string
        already ends with the specified value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("hello/").finish("/"), Stringable("hello/"))

    def testFinishRaisesTypeErrorOnNonString(self):
        """Raise TypeError when cap is not a string.

        Verifies that `finish` enforces type validation on the cap
        parameter before processing.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").finish(1)

    # ----------------------------------------------------------------- start

    def testStartPrependsPrefix(self):
        """Prepend the prefix when the string does not start with it.

        Validates that `start` ensures the string begins with the
        specified prefix by prepending it when not already present.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("world").start("/"), Stringable("/world"))

    def testStartDoesNotDuplicatePrefixIfPresent(self):
        """Preserve the prefix when the string already starts with it.

        Ensures `start` does not prepend a duplicate prefix when the
        string already begins with the specified value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("/world").start("/"), Stringable("/world"))

    def testStartRaisesTypeErrorOnNonString(self):
        """Raise TypeError when prefix is not a string.

        Verifies that `start` enforces type validation on the prefix
        parameter before processing.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("world").start(1)

    # --------------------------------------------------------------- excerpt

    def testExcerptExtractsAroundPhrase(self):
        """Extract text surrounding the given phrase.

        Validates that `excerpt` returns a snippet centered around the
        first occurrence of the phrase, with surrounding context.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("The quick brown fox")
        result = s.excerpt("brown", {"radius": 5})
        self.assertIn("brown", result)

    def testExcerptReturnsNoneWhenPhraseNotFound(self):
        """Return None when the phrase is not found.

        Ensures `excerpt` returns `None` when the searched phrase does
        not exist within the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("hello world")
        self.assertIsNone(s.excerpt("xyz"))

    def testExcerptWithEmptyPhrase(self):
        """Return the beginning of the string when phrase is empty.

        Validates that `excerpt` with an empty phrase returns the first
        radius*2 characters of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("hello world")
        result = s.excerpt("", {"radius": 5})
        self.assertIsNotNone(result)

    def testExcerptRaisesTypeErrorOnNonStringPhrase(self):
        """Raise TypeError when phrase is not a string.

        Ensures `excerpt` validates the phrase type before attempting
        any search operation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").excerpt(42)

    # -------------------------------------------------------------- basename

    def testBasenameExtractsFilename(self):
        """Extract the trailing filename component from a path.

        Validates that `basename` correctly isolates the final segment
        of the path string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("/var/www/html/index.html")
        self.assertEqual(s.basename(), Stringable("index.html"))

    def testBasenameRemovesSuffix(self):
        """Remove the specified suffix from the basename.

        Ensures that `basename` with a suffix argument strips the suffix
        from the resulting filename component.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("/var/www/html/index.html")
        self.assertEqual(s.basename(".html"), Stringable("index"))

    # --------------------------------------------------------------- dirname

    def testDirnameReturnsParentDirectory(self):
        """Return the parent directory path.

        Validates that `dirname` correctly extracts the immediate parent
        of the given file path.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("/var/www/html/index.html")
        result = s.dirname()
        self.assertIn("html", str(result))

    def testDirnameWithMultipleLevels(self):
        """Ascend multiple directory levels.

        Ensures `dirname` with a level count greater than one navigates
        up the appropriate number of directory levels.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("/var/www/html/index.html")
        result = s.dirname(2)
        self.assertIn("www", str(result))

    # ----------------------------------------------------------- __getitem__

    def testGetItemByIndex(self):
        """Return the character at a given index via subscript.

        Validates that index-based subscript access returns a Stringable
        instance containing the correct single character.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("hello")
        self.assertEqual(s[0], Stringable("h"))
        self.assertIsInstance(s[0], Stringable)

    def testGetItemBySlice(self):
        """Return a substring via slice subscript.

        Validates that slice-based subscript access returns a Stringable
        instance containing the correct substring.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("hello world")
        self.assertEqual(s[0:5], Stringable("hello"))
        self.assertIsInstance(s[0:5], Stringable)

    # ----------------------------------------------------------------- __str__

    def testStrReturnsPlainStringRepresentation(self):
        """Return the plain string representation.

        Validates that Python's built-in `str()` applied to a Stringable
        returns an equivalent plain string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("hello")
        self.assertEqual(str(s), "hello")
        self.assertIsInstance(str(s), str)

    # --------------------------------------------------------------- scan

    def testScanParsesFormatString(self):
        """Parse values from a string according to a format pattern.

        Validates that `scan` correctly extracts typed tokens from the
        string using a simplified format specification.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("name=John age=30")
        result = s.scan("name=%s age=%d")
        self.assertIsInstance(result, list)
        self.assertIn("John", result)

    def testScanReturnsEmptyListWhenNoMatch(self):
        """Return an empty list when no pattern matches.

        Ensures `scan` returns an empty list rather than raising an
        exception when the format does not match the string content.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("no match here")
        result = s.scan("%d-%d-%d")
        self.assertEqual(result, [])

    def testScanRaisesTypeErrorOnNonStringFormat(self):
        """Raise TypeError when format string is not a string.

        Verifies that `scan` enforces the string type constraint on the
        format_str parameter.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").scan(123)
