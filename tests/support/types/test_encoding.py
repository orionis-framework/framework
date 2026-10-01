import hashlib
from orionis.support.types.stringable import Stringable
from orionis.test import TestCase

class TestStringableEncoding(TestCase):
    """Unit tests for Stringable encoding, hashing, and serialization."""

    # --------------------------------------------------------------- toBase64

    def testToBase64EncodesString(self):
        """Encode the string to Base64 format.

        Validates that `toBase64` produces the correct Base64-encoded
        representation of the source string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello").toBase64()
        self.assertEqual(result, Stringable("aGVsbG8="))

    def testToBase64ReturnsStringable(self):
        """Return a Stringable instance from toBase64.

        Ensures the return type of `toBase64` is a Stringable so that
        method chaining remains available.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsInstance(Stringable("hello").toBase64(), Stringable)

    def testToBase64OnEmptyString(self):
        """Encode an empty string to Base64.

        Validates that `toBase64` handles empty input without raising
        and returns the correct Base64 representation of an empty string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("").toBase64(), Stringable(""))

    # ------------------------------------------------------------- fromBase64

    def testFromBase64DecodesString(self):
        """Decode a Base64-encoded string.

        Validates that `fromBase64` correctly decodes a valid Base64
        string back to its original plaintext form.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("aGVsbG8=").fromBase64()
        self.assertEqual(result, Stringable("hello"))

    def testFromBase64ReturnsEmptyOnInvalidInput(self):
        """Return empty Stringable for invalid Base64 when non-strict.

        Ensures that `fromBase64` swallows decode errors and returns an
        empty Stringable when strict mode is disabled (the default).

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("!!!invalid!!!").fromBase64()
        self.assertEqual(result, Stringable(""))

    def testFromBase64RaisesOnInvalidInputWhenStrict(self):
        """Raise RuntimeError for invalid Base64 in strict mode.

        Validates that `fromBase64(strict=True)` propagates the decode
        error as a RuntimeError rather than swallowing it.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(RuntimeError):
            Stringable("!!!invalid!!!").fromBase64(strict=True)

    def testFromBase64RaisesTypeErrorOnNonBoolStrict(self):
        """Raise TypeError when strict is not a boolean.

        Ensures `fromBase64` validates the type of the strict parameter
        before attempting any decoding operation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("aGVsbG8=").fromBase64(strict="yes")

    def testBase64RoundTrip(self):
        """Verify that encoding then decoding returns the original string.

        Validates that successive calls to `toBase64` and `fromBase64`
        yield the original plaintext string without data loss.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        original = "hello world 123"
        result = Stringable(original).toBase64().fromBase64()
        self.assertEqual(result, Stringable(original))

    # --------------------------------------------------------------------- md5

    def testMd5ReturnsCorrectHash(self):
        """Compute the MD5 hash of the string.

        Validates that `md5` returns a 32-character hexadecimal string
        matching the expected MD5 digest for the input.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("hello").md5()
        expected = hashlib.md5(b"hello").hexdigest()
        self.assertEqual(result, expected)

    def testMd5ReturnsString(self):
        """Return a plain str from md5.

        Ensures the return type of `md5` is a regular Python `str`
        rather than a Stringable.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsInstance(Stringable("hello").md5(), str)

    def testMd5HasExpectedLength(self):
        """Produce a 32-character hexadecimal MD5 hash.

        Validates that the hex digest returned by `md5` always contains
        exactly 32 characters, matching the MD5 output specification.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(len(Stringable("test").md5()), 32)

    # -------------------------------------------------------------------- sha1

    def testSha1ReturnsCorrectHash(self):
        """Compute the SHA1 hash of the string.

        Validates that `sha1` returns the expected 40-character
        hexadecimal SHA1 digest for the given input.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        expected = hashlib.sha1(b"hello").hexdigest()
        self.assertEqual(Stringable("hello").sha1(), expected)

    def testSha1HasExpectedLength(self):
        """Produce a 40-character hexadecimal SHA1 hash.

        Validates that the hex digest returned by `sha1` always contains
        exactly 40 characters, matching the SHA1 output specification.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(len(Stringable("test").sha1()), 40)

    # ----------------------------------------------------------------- sha256

    def testSha256ReturnsCorrectHash(self):
        """Compute the SHA256 hash of the string.

        Validates that `sha256` returns the expected 64-character
        hexadecimal SHA256 digest for the given input.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        expected = hashlib.sha256(b"hello").hexdigest()
        self.assertEqual(Stringable("hello").sha256(), expected)

    def testSha256HasExpectedLength(self):
        """Produce a 64-character hexadecimal SHA256 hash.

        Validates that the hex digest returned by `sha256` always
        contains exactly 64 characters, matching the SHA256 output spec.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(len(Stringable("test").sha256()), 64)

    # -------------------------------------------------------------------- hash

    def testHashWithSha256Algorithm(self):
        """Hash the string using the sha256 algorithm via hash().

        Validates that `hash("sha256")` returns a result equivalent to
        calling `sha256()` directly on the same string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("hello")
        self.assertEqual(s.hash("sha256"), s.sha256())

    def testHashWithMd5Algorithm(self):
        """Hash the string using the md5 algorithm via hash().

        Validates that `hash("md5")` returns a result equivalent to
        calling `md5()` directly on the same string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("hello")
        self.assertEqual(str(s.hash("md5")), s.md5())

    def testHashRaisesValueErrorForUnsupportedAlgorithm(self):
        """Raise ValueError for an unsupported hash algorithm.

        Ensures `hash` validates the algorithm name against the hashlib
        registry and raises ValueError when no match is found.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            Stringable("hello").hash("not_a_real_algorithm_xyz")

    # ----------------------------------------------------------- toHtmlString

    def testToHtmlStringEscapesSpecialChars(self):
        """Escape HTML special characters in the string.

        Validates that `toHtmlString` converts characters such as <, >,
        and & into their safe HTML entity equivalents.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("<div>Hello & World</div>").toHtmlString()
        self.assertIn("&lt;", str(result))
        self.assertIn("&gt;", str(result))
        self.assertIn("&amp;", str(result))

    def testToHtmlStringReturnStringable(self):
        """Return a Stringable instance from toHtmlString.

        Ensures the return type of `toHtmlString` is a Stringable so
        that method chaining remains available.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsInstance(Stringable("text").toHtmlString(), Stringable)

    # -------------------------------------------------------------- stripTags

    def testStripTagsRemovesAllHtmlTags(self):
        """Remove all HTML tags from the string.

        Validates that `stripTags` with no allowed_tags argument strips
        every HTML tag from the string, leaving only text content.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("<p>Hello <b>World</b></p>").stripTags()
        self.assertEqual(result, Stringable("Hello World"))

    def testStripTagsWithAllowedTagsUnescapesEntities(self):
        """Unescape HTML entities when allowed_tags is provided.

        Validates that passing an allowed_tags value triggers HTML entity
        unescaping instead of full tag removal.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Stringable("&lt;p&gt;Hello&lt;/p&gt;").stripTags("<p>")
        self.assertIn("Hello", str(result))

    # --------------------------------------------------------------- jsonSerialize

    def testJsonSerializeReturnsPlainString(self):
        """Return a plain string for JSON serialization.

        Validates that `jsonSerialize` returns the string value of the
        Stringable instance as a regular Python `str`.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        s = Stringable("hello")
        result = s.jsonSerialize()
        self.assertEqual(result, "hello")
        self.assertIsInstance(result, str)

    # --------------------------------------------------------------- offsetExists

    def testOffsetExistsReturnsTrueForValidIndex(self):
        """Return True for a valid character offset.

        Validates that `offsetExists` returns True when the given index
        is within the bounds of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(Stringable("hello").offsetExists(0))
        self.assertTrue(Stringable("hello").offsetExists(4))

    def testOffsetExistsReturnsFalseForOutOfBoundsIndex(self):
        """Return False for an out-of-bounds offset.

        Ensures `offsetExists` returns False when the index exceeds
        the string length, avoiding any IndexError propagation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(Stringable("hi").offsetExists(99))

    def testOffsetExistsReturnsFalseForNonInteger(self):
        """Return False when offset is not an integer.

        Validates that `offsetExists` handles non-integer offsets
        gracefully by returning False.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(Stringable("hello").offsetExists("a"))

    # ---------------------------------------------------------------- offsetGet

    def testOffsetGetReturnsCorrectCharacter(self):
        """Return the character at the given offset.

        Validates that `offsetGet` retrieves the correct character for a
        valid integer index within the string bounds.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Stringable("hello").offsetGet(1), "e")

    def testOffsetGetRaisesIndexErrorForOutOfBounds(self):
        """Raise IndexError when offset is out of string bounds.

        Ensures `offsetGet` propagates IndexError when the requested
        index exceeds the length of the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(IndexError):
            Stringable("hi").offsetGet(99)

    def testOffsetGetRaisesTypeErrorOnNonInteger(self):
        """Raise TypeError when offset is not an integer.

        Verifies `offsetGet` enforces the integer type constraint on its
        offset parameter before accessing the string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Stringable("hello").offsetGet("a")
