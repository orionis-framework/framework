from orionis.support.types.stringable import Stringable
from orionis.test import TestCase

class TestStringableConditionals(TestCase):
    """Unit tests for Stringable conditional (when*) callback methods."""

    # ------------------------------------------------------------------- when

    def testWhenExecutesCallbackWhenConditionIsTrue(self):
        """Execute the callback when the boolean condition is True.

        Validates that `when` invokes the callback and returns its result
        wrapped in a Stringable when the condition evaluates to True.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello").when(True, lambda s: s.upper())
        self.assertEqual(result, Stringable("HELLO"))

    def testWhenSkipsCallbackWhenConditionIsFalse(self):
        """Return self when the boolean condition is False and no default.

        Validates that `when` returns the original Stringable unchanged
        when the condition is False and no default callback is provided.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello").when(False, lambda s: s.upper())
        self.assertEqual(result, Stringable("hello"))

    def testWhenExecutesDefaultCallbackWhenFalse(self):
        """Execute the default callback when the condition is False.

        Validates that `when` invokes the default callback and returns
        its result when the main condition evaluates to False.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello").when(
            False,
            lambda s: s.upper(),
            lambda s: s.lower(),
        )
        self.assertEqual(result, Stringable("hello"))

    def testWhenAcceptsCallableCondition(self):
        """Accept a callable as the condition argument.

        Validates that `when` evaluates a callable condition by passing
        self to it and using the return value as the boolean result.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello").when(
            lambda s: s.isNotEmpty(), lambda s: s.upper(),
        )
        self.assertEqual(result, Stringable("HELLO"))

    def testWhenRaisesTypeErrorOnInvalidCondition(self):
        """Raise TypeError when condition is neither bool nor callable.

        Ensures `when` validates the condition argument type before
        evaluating it.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").when("not-a-bool", lambda s: s)

    def testWhenRaisesTypeErrorOnNonCallableCallback(self):
        """Raise TypeError when callback is not callable.

        Ensures `when` validates that the callback argument is callable
        before any condition evaluation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").when(True, "not-callable")

    def testWhenRaisesTypeErrorOnNonCallableDefault(self):
        """Raise TypeError when default is provided but not callable.

        Ensures `when` validates that the optional default argument is
        callable when it is not None.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").when(False, lambda s: s, "not-callable")

    # ------------------------------------------------------------- whenContains

    def testWhenContainsExecutesCallbackWhenNeedleFound(self):
        """Execute callback when the string contains the needle.

        Validates that `whenContains` triggers the callback when the
        specified substring is present in the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello world").whenContains(
            "world", lambda s: s.upper(),
        )
        self.assertEqual(result, Stringable("HELLO WORLD"))

    def testWhenContainsSkipsCallbackWhenNeedleAbsent(self):
        """Return self when the string does not contain the needle.

        Ensures `whenContains` is a no-op when the needle is not found
        and no default callback is supplied.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello world").whenContains(
            "xyz", lambda s: s.upper(),
        )
        self.assertEqual(result, Stringable("hello world"))

    # ---------------------------------------------------------- whenContainsAll

    def testWhenContainsAllExecutesWhenAllNeedlesPresent(self):
        """Execute callback when all needles are found in the string.

        Validates that `whenContainsAll` triggers the callback only when
        every needle in the list is present within the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello world").whenContainsAll(
            ["hello", "world"], lambda s: s.upper(),
        )
        self.assertEqual(result, Stringable("HELLO WORLD"))

    def testWhenContainsAllSkipsCallbackWhenAnyNeedleMissing(self):
        """Return self when any needle is absent from the string.

        Ensures `whenContainsAll` does not invoke the callback when at
        least one of the required needles is missing.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello world").whenContainsAll(
            ["hello", "xyz"], lambda s: s.upper(),
        )
        self.assertEqual(result, Stringable("hello world"))

    # --------------------------------------------------------------- whenEmpty

    def testWhenEmptyExecutesCallbackOnEmptyString(self):
        """Execute callback when the string is empty.

        Validates that `whenEmpty` triggers the callback and returns its
        result when the Stringable instance has no characters.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("").whenEmpty(lambda _: Stringable("default"))
        self.assertEqual(result, Stringable("default"))

    def testWhenEmptySkipsCallbackOnNonEmptyString(self):
        """Return self when the string is not empty.

        Ensures `whenEmpty` is a no-op when the Stringable instance
        contains at least one character.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello").whenEmpty(lambda _: Stringable("default"))
        self.assertEqual(result, Stringable("hello"))

    # ----------------------------------------------------------- whenNotEmpty

    def testWhenNotEmptyExecutesCallbackOnNonEmptyString(self):
        """Execute callback when the string is not empty.

        Validates that `whenNotEmpty` triggers the callback when the
        Stringable instance contains at least one character.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello").whenNotEmpty(lambda s: s.upper())
        self.assertEqual(result, Stringable("HELLO"))

    def testWhenNotEmptySkipsCallbackOnEmptyString(self):
        """Return self when the string is empty.

        Ensures `whenNotEmpty` does not invoke the callback when the
        Stringable instance has no characters.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("").whenNotEmpty(lambda s: s.upper())
        self.assertEqual(result, Stringable(""))

    # ------------------------------------------------------------- whenEndsWith

    def testWhenEndsWithExecutesCallbackWhenMatching(self):
        """Execute callback when the string ends with the needle.

        Validates that `whenEndsWith` triggers the callback when the
        string terminates with the specified substring.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello.py").whenEndsWith(".py", lambda s: s.upper())
        self.assertEqual(result, Stringable("HELLO.PY"))

    def testWhenEndsWithSkipsCallbackWhenNotMatching(self):
        """Return self when the string does not end with the needle.

        Ensures `whenEndsWith` is a no-op when the string does not
        end with any of the provided needles.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello.py").whenEndsWith(
            ".txt", lambda s: s.upper(),
        )
        self.assertEqual(result, Stringable("hello.py"))

    # --------------------------------------------------------- whenDoesntEndWith

    def testWhenDoesntEndWithExecutesCallbackWhenNotMatching(self):
        """Execute callback when the string does not end with the needle.

        Validates that `whenDoesntEndWith` triggers the callback when
        the string does not terminate with the specified substring.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello.txt").whenDoesntEndWith(
            ".py", lambda s: s.upper(),
        )
        self.assertEqual(result, Stringable("HELLO.TXT"))

    def testWhenDoesntEndWithSkipsCallbackWhenMatching(self):
        """Return self when the string does end with the needle.

        Ensures `whenDoesntEndWith` is a no-op when the string actually
        ends with one of the provided needles.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello.py").whenDoesntEndWith(
            ".py", lambda s: s.upper(),
        )
        self.assertEqual(result, Stringable("hello.py"))

    # -------------------------------------------------------------- whenExactly

    def testWhenExactlyExecutesCallbackOnExactMatch(self):
        """Execute callback when the string exactly matches the value.

        Validates that `whenExactly` triggers the callback when the
        string is identical to the provided value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello").whenExactly("hello", lambda s: s.upper())
        self.assertEqual(result, Stringable("HELLO"))

    def testWhenExactlySkipsCallbackOnNoMatch(self):
        """Return self when the string does not exactly match.

        Ensures `whenExactly` is a no-op when the string differs from
        the provided value in any way.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello").whenExactly("HELLO", lambda s: s.upper())
        self.assertEqual(result, Stringable("hello"))

    # ----------------------------------------------------------- whenNotExactly

    def testWhenNotExactlyExecutesCallbackWhenNoMatch(self):
        """Execute callback when the string does not exactly match.

        Validates that `whenNotExactly` triggers the callback when the
        string differs from the provided value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello").whenNotExactly("world", lambda s: s.upper())
        self.assertEqual(result, Stringable("HELLO"))

    def testWhenNotExactlySkipsCallbackOnExactMatch(self):
        """Return self when the string exactly matches the value.

        Ensures `whenNotExactly` is a no-op when the string is identical
        to the provided value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello").whenNotExactly(
            "hello", lambda s: s.upper(),
        )
        self.assertEqual(result, Stringable("hello"))

    # ----------------------------------------------------------- whenStartsWith

    def testWhenStartsWithExecutesCallbackWhenMatching(self):
        """Execute callback when the string starts with the needle.

        Validates that `whenStartsWith` triggers the callback when the
        string begins with the specified substring.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello world").whenStartsWith(
            "hello", lambda s: s.upper(),
        )
        self.assertEqual(result, Stringable("HELLO WORLD"))

    def testWhenStartsWithSkipsCallbackWhenNotMatching(self):
        """Return self when the string does not start with the needle.

        Ensures `whenStartsWith` is a no-op when the string does not
        begin with any of the provided needles.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello world").whenStartsWith(
            "world", lambda s: s.upper(),
        )
        self.assertEqual(result, Stringable("hello world"))

    # ------------------------------------------------------- whenDoesntStartWith

    def testWhenDoesntStartWithExecutesCallbackWhenNotMatching(self):
        """Execute callback when the string does not start with the needle.

        Validates that `whenDoesntStartWith` triggers the callback when
        the string does not begin with the specified substring.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello world").whenDoesntStartWith(
            "world", lambda s: s.upper(),
        )
        self.assertEqual(result, Stringable("HELLO WORLD"))

    def testWhenDoesntStartWithSkipsCallbackWhenMatching(self):
        """Return self when the string does start with the needle.

        Ensures `whenDoesntStartWith` is a no-op when the string
        actually starts with one of the provided needles.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello world").whenDoesntStartWith(
            "hello", lambda s: s.upper(),
        )
        self.assertEqual(result, Stringable("hello world"))

    # -------------------------------------------------------------- whenTest

    def testWhenTestExecutesCallbackWhenPatternMatches(self):
        """Execute callback when the string matches the regex pattern.

        Validates that `whenTest` triggers the callback when the string
        matches the provided regular expression.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello123").whenTest(r"\d+", lambda s: s.upper())
        self.assertEqual(result, Stringable("HELLO123"))

    def testWhenTestSkipsCallbackWhenPatternDoesNotMatch(self):
        """Return self when the string does not match the regex.

        Ensures `whenTest` is a no-op when the regular expression does
        not match any part of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello").whenTest(r"\d+", lambda s: s.upper())
        self.assertEqual(result, Stringable("hello"))

    # --------------------------------------------------------------- whenIs

    def testWhenIsExecutesCallbackWhenPatternMatches(self):
        """Execute callback when the string matches the wildcard pattern.

        Validates that `whenIs` triggers the callback when the string
        matches the provided fnmatch-style pattern.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello world").whenIs("hello*", lambda s: s.upper())
        self.assertEqual(result, Stringable("HELLO WORLD"))

    def testWhenIsSkipsCallbackWhenPatternDoesNotMatch(self):
        """Return self when the string does not match the wildcard pattern.

        Ensures `whenIs` is a no-op when the string does not match any
        of the provided fnmatch-style patterns.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello world").whenIs("foo*", lambda s: s.upper())
        self.assertEqual(result, Stringable("hello world"))

    # ----------------------------------------------------------- whenIsAscii

    def testWhenIsAsciiExecutesCallbackForAsciiString(self):
        """Execute callback when the string is pure ASCII.

        Validates that `whenIsAscii` triggers the callback when the
        string contains only 7-bit ASCII characters.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello").whenIsAscii(lambda s: s.upper())
        self.assertEqual(result, Stringable("HELLO"))

    def testWhenIsAsciiSkipsCallbackForNonAsciiString(self):
        """Return self when the string contains non-ASCII characters.

        Ensures `whenIsAscii` is a no-op when the string includes
        characters outside the 7-bit ASCII range.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("héllo").whenIsAscii(lambda s: s.upper())
        self.assertEqual(result, Stringable("héllo"))

    # ----------------------------------------------------------- whenIsUuid

    def testWhenIsUuidExecutesCallbackForValidUuid(self):
        """Execute callback when the string is a valid UUID.

        Validates that `whenIsUuid` triggers the callback when the
        string can be parsed as a well-formed UUID.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        called = []
        Stringable(uuid_str).whenIsUuid(lambda _: called.append(True))
        self.assertTrue(called)

    def testWhenIsUuidSkipsCallbackForInvalidUuid(self):
        """Return self when the string is not a valid UUID.

        Ensures `whenIsUuid` is a no-op when the string cannot be
        parsed as a valid UUID.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        called = []
        Stringable("not-a-uuid").whenIsUuid(
            lambda _: called.append(True),
        )
        self.assertFalse(called)

    # ---------------------------------------------------------- whenIsUlid

    def testWhenIsUlidExecutesCallbackForValidUlid(self):
        """Execute callback when the string is a valid ULID.

        Validates that `whenIsUlid` triggers the callback when the
        string matches the ULID format specification.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        valid_ulid = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        called = []
        Stringable(valid_ulid).whenIsUlid(lambda _: called.append(True))
        self.assertTrue(called)

    def testWhenIsUlidSkipsCallbackForInvalidUlid(self):
        """Return self when the string is not a valid ULID.

        Ensures `whenIsUlid` is a no-op when the string does not conform
        to the ULID format.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        called = []
        Stringable("not-a-ulid").whenIsUlid(lambda _: called.append(True))
        self.assertFalse(called)
