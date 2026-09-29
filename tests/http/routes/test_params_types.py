import uuid
from orionis.http.routes.params_types import PARAM_TYPES
from orionis.test import TestCase

class TestParamTypes(TestCase):
    """Unit tests for the PARAM_TYPES route parameter type registry."""

    def testRegistryContainsExpectedKeys(self) -> None:
        """Verify that PARAM_TYPES contains all four expected type keys.

        Confirms that 'str', 'slug', 'int', and 'uuid' are present in
        the registry.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for key in ("str", "slug", "int", "uuid"):
            self.assertIn(key, PARAM_TYPES)

    def testEachEntryHasPatternAndConverter(self) -> None:
        """Verify that every registry entry exposes 'pattern' and 'converter'.

        Confirms the expected structure for all registered type entries.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for name, entry in PARAM_TYPES.items():
            with self.subTest(param_type=name):
                self.assertIn("pattern", entry)
                self.assertIn("converter", entry)

    def testStrPatternMatchesAnyNonSlash(self) -> None:
        """Verify that the 'str' pattern matches segments with no slashes.

        Confirms the regex accepts alphanumeric and special characters
        but does not span path separators.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        import re

        pattern = re.compile("^" + PARAM_TYPES["str"]["pattern"] + "$")
        self.assertIsNotNone(pattern.match("hello-world_123"))
        self.assertIsNone(pattern.match("a/b"))

    def testSlugPatternMatchesLowercaseAlphanumericHyphen(self) -> None:
        """Verify that the 'slug' pattern matches only slug-safe characters.

        Confirms that lowercase letters, digits, and hyphens are
        accepted while uppercase letters and other characters are not.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        import re

        pattern = re.compile("^" + PARAM_TYPES["slug"]["pattern"] + "$")
        self.assertIsNotNone(pattern.match("my-post-123"))
        self.assertIsNone(pattern.match("My-Post"))
        self.assertIsNone(pattern.match("has space"))

    def testIntPatternMatchesDigitsOnly(self) -> None:
        """Verify that the 'int' pattern matches sequences of digits only.

        Confirms that non-digit characters cause the match to fail.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        import re

        pattern = re.compile("^" + PARAM_TYPES["int"]["pattern"] + "$")
        self.assertIsNotNone(pattern.match("42"))
        self.assertIsNotNone(pattern.match("0"))
        self.assertIsNone(pattern.match("3.14"))
        self.assertIsNone(pattern.match("abc"))

    def testUuidPatternMatchesValidUuid(self) -> None:
        """Verify that the 'uuid' pattern matches a valid UUID string.

        Generates a real UUID and confirms that the pattern accepts it.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        import re

        pattern = re.compile("^" + PARAM_TYPES["uuid"]["pattern"] + "$")
        valid = str(uuid.uuid4())
        self.assertIsNotNone(pattern.match(valid))
        self.assertIsNone(pattern.match("not-a-uuid"))

    def testStrConverterReturnsString(self) -> None:
        """Verify that the 'str' converter returns a str value.

        Confirms the converter callable casts its argument to str.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        converter = PARAM_TYPES["str"]["converter"]
        self.assertIsInstance(converter("hello"), str)

    def testIntConverterReturnsInt(self) -> None:
        """Verify that the 'int' converter returns an int value.

        Confirms the converter callable casts a digit string to int.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        converter = PARAM_TYPES["int"]["converter"]
        result = converter("99")
        self.assertIsInstance(result, int)
        self.assertEqual(result, 99)

    def testUuidConverterReturnsUuidObject(self) -> None:
        """Verify that the 'uuid' converter returns a uuid.UUID instance.

        Confirms the converter callable wraps the raw string in UUID.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        converter = PARAM_TYPES["uuid"]["converter"]
        raw = "550e8400-e29b-41d4-a716-446655440000"
        result = converter(raw)
        self.assertIsInstance(result, uuid.UUID)
