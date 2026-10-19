import socket
from unittest.mock import patch
from orionis.schemas.rules.accepted import Accepted
from orionis.schemas.rules.active_url import ActiveUrl
from orionis.schemas.rules.alpha import Alpha
from orionis.schemas.rules.ascii import Ascii
from orionis.schemas.rules.doesnt_end_with import DoesntEndWith
from orionis.schemas.rules.doesnt_start_with import DoesntStartWith
from orionis.schemas.rules.ends_with import EndsWith
from orionis.schemas.rules.ip_address import IpAddress
from orionis.schemas.rules.json_string import Json
from orionis.schemas.rules.lowercase import Lowercase
from orionis.schemas.rules.mac_address import MacAddress
from orionis.schemas.rules.starts_with import StartsWith
from orionis.schemas.rules.ulid import Ulid
from orionis.schemas.rules.uppercase import Uppercase
from orionis.schemas.rules.uuid_string import Uuid
from orionis.test import TestCase

# Shared owner instance; string rules never inspect sibling fields.
_OWNER = object()

# Canonical identifiers reused across the UUID and ULID assertions.
_UUID_V4 = "9f8c1e2a-4b3d-4c5e-8a9b-0c1d2e3f4a5b"
_UUID_V1 = "c232ab00-9414-11ec-b3c8-9f6bdeced846"
_UUID_NIL = "00000000-0000-0000-0000-000000000000"
_ULID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"

class TestAccepted(TestCase):

    async def testAcceptsTruthyStrings(self) -> None:
        """Return True for every textual representation of an acceptance.

        Validates that ``yes``, ``on``, ``1`` and ``true`` are accepted
        regardless of their casing.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = Accepted()
        for value in ("yes", "on", "1", "true", "YES", "True"):
            self.assertTrue(await rule.enforce("terms", value, _OWNER))

    async def testAcceptsBooleanAndInteger(self) -> None:
        """Return True for the boolean and integer acceptance values.

        Validates that ``True`` and ``1`` are treated as an acceptance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = Accepted()
        self.assertTrue(await rule.enforce("terms", True, _OWNER))
        self.assertTrue(await rule.enforce("terms", 1, _OWNER))

    async def testRejectsFalsyValues(self) -> None:
        """Return False for values that do not express an acceptance.

        Validates that negatives, zero, ``None`` and unrelated types fail.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = Accepted()
        for value in (False, 0, 2, "no", "off", "", None, [], object()):
            self.assertFalse(await rule.enforce("terms", value, _OWNER))

    async def testCodeAndDefaultMessage(self) -> None:
        """Expose the documented rule code in the reported failure.

        Validates that a rejected value produces a failure carrying the
        ``accepted`` code.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        failure = await Accepted().validate("terms", "no", _OWNER)
        self.assertIsNotNone(failure)
        self.assertEqual(failure.rule, "accepted")

class TestActiveUrl(TestCase):

    async def testResolvableHostnamePasses(self) -> None:
        """Return True when the hostname resolves through the system resolver.

        Validates the success path without depending on real DNS traffic.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = ActiveUrl()
        target = "orionis.schemas.rules.active_url.socket.getaddrinfo"
        with patch(target, return_value=[("family", "type", 6, "", ("1.2.3.4", 0))]):
            self.assertTrue(await rule.enforce("url", "https://example.com/a", _OWNER))

    async def testUnresolvableHostnameFails(self) -> None:
        """Return False when the resolver reports an unknown hostname.

        Validates that a ``gaierror`` is translated into a failed check.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = ActiveUrl()
        target = "orionis.schemas.rules.active_url.socket.getaddrinfo"
        with patch(target, side_effect=socket.gaierror):
            self.assertFalse(await rule.enforce("url", "https://example.com", _OWNER))

    async def testUrlWithoutHostnameFails(self) -> None:
        """Return False when the value carries no hostname component.

        Validates that relative paths and bare words are rejected before
        any lookup is attempted.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = ActiveUrl()
        self.assertFalse(await rule.enforce("url", "/relative/path", _OWNER))
        self.assertFalse(await rule.enforce("url", "", _OWNER))

    async def testMalformedUrlFails(self) -> None:
        """Return False when the value cannot be split into URL components.

        Validates that a malformed IPv6 literal does not raise.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = ActiveUrl()
        self.assertFalse(await rule.enforce("url", "http://[oops", _OWNER))

    async def testNonStringValuePasses(self) -> None:
        """Return True when the value is not a string.

        Validates that type reporting is delegated to the type layer.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(await ActiveUrl().enforce("url", 123, _OWNER))

class TestAlpha(TestCase):

    async def testUnicodeLettersPass(self) -> None:
        """Return True for Unicode letters and combining marks.

        Validates that accented text and decomposed characters are
        accepted by the default configuration.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = Alpha()
        self.assertTrue(await rule.enforce("name", "José", _OWNER))
        self.assertTrue(await rule.enforce("name", "e\u0301", _OWNER))

    async def testNonLettersFail(self) -> None:
        """Return False when the value carries digits, spaces or symbols.

        Validates that only alphabetic content is accepted.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = Alpha()
        for value in ("abc1", "ab c", "ab-c", ""):
            self.assertFalse(await rule.enforce("name", value, _OWNER))

    async def testAsciiOnlyRejectsAccents(self) -> None:
        """Return False for non-ASCII letters when ``ascii_only`` is enabled.

        Validates that the restricted mode narrows the accepted range to
        ``a-z`` and ``A-Z``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = Alpha(ascii_only=True)
        self.assertTrue(await rule.enforce("name", "Jose", _OWNER))
        self.assertFalse(await rule.enforce("name", "José", _OWNER))

    async def testNonStringValuePasses(self) -> None:
        """Return True when the value is not a string.

        Validates that type reporting is delegated to the type layer.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(await Alpha().enforce("name", 10, _OWNER))

class TestAscii(TestCase):

    async def testSevenBitContentPasses(self) -> None:
        """Return True for content limited to the 7-bit ASCII range.

        Validates that letters, digits and punctuation are accepted.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(await Ascii().enforce("tag", "abc-123_!", _OWNER))

    async def testNonAsciiContentFails(self) -> None:
        """Return False when the value carries characters beyond ASCII.

        Validates that accented and emoji content is rejected.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = Ascii()
        self.assertFalse(await rule.enforce("tag", "ñandú", _OWNER))
        self.assertFalse(await rule.enforce("tag", "a€", _OWNER))

    async def testNonStringValuePasses(self) -> None:
        """Return True when the value is not a string.

        Validates that type reporting is delegated to the type layer.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(await Ascii().enforce("tag", None, _OWNER))

class TestEndsWith(TestCase):

    async def testMatchingSuffixPasses(self) -> None:
        """Return True when the value ends with one of the suffixes.

        Validates that any configured suffix satisfies the rule.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = EndsWith(".png", ".jpg")
        self.assertTrue(await rule.enforce("file", "photo.png", _OWNER))
        self.assertTrue(await rule.enforce("file", "photo.jpg", _OWNER))

    async def testMissingSuffixFails(self) -> None:
        """Return False when the value ends with none of the suffixes.

        Validates that unrelated extensions are rejected.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(await EndsWith(".png").enforce("file", "photo.gif", _OWNER))

    async def testSuffixMatchIsCaseSensitive(self) -> None:
        """Return False when only the casing differs from the suffix.

        Validates that comparison never folds the case.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(await EndsWith(".png").enforce("file", "photo.PNG", _OWNER))

    async def testNonStringValuePasses(self) -> None:
        """Return True when the value is not a string.

        Validates that type reporting is delegated to the type layer.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(await EndsWith(".png").enforce("file", 5, _OWNER))

    def testEmptyConfigurationRaises(self) -> None:
        """Raise ValueError when no suffix is supplied.

        Validates that the rule refuses an configuration that can never
        be satisfied.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            EndsWith()

class TestDoesntEndWith(TestCase):

    async def testForbiddenSuffixFails(self) -> None:
        """Return False when the value ends with a forbidden suffix.

        Validates that any configured suffix rejects the value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = DoesntEndWith(".exe", ".bat")
        self.assertFalse(await rule.enforce("file", "setup.exe", _OWNER))
        self.assertFalse(await rule.enforce("file", "setup.bat", _OWNER))

    async def testOtherSuffixPasses(self) -> None:
        """Return True when the value ends with an unrelated suffix.

        Validates that only the configured suffixes are rejected.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(await DoesntEndWith(".exe").enforce("file", "a.txt", _OWNER))

    async def testNonStringValuePasses(self) -> None:
        """Return True when the value is not a string.

        Validates that type reporting is delegated to the type layer.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(await DoesntEndWith(".exe").enforce("file", None, _OWNER))

    def testEmptyConfigurationRaises(self) -> None:
        """Raise ValueError when no suffix is supplied.

        Validates that the rule refuses an empty configuration.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            DoesntEndWith()

class TestStartsWith(TestCase):

    async def testMatchingPrefixPasses(self) -> None:
        """Return True when the value starts with one of the prefixes.

        Validates that any configured prefix satisfies the rule.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = StartsWith("https://", "http://")
        self.assertTrue(await rule.enforce("url", "https://a.test", _OWNER))
        self.assertTrue(await rule.enforce("url", "http://a.test", _OWNER))

    async def testMissingPrefixFails(self) -> None:
        """Return False when the value starts with none of the prefixes.

        Validates that unrelated schemes are rejected.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(await StartsWith("https://").enforce("url", "ftp://a", _OWNER))

    async def testNonStringValuePasses(self) -> None:
        """Return True when the value is not a string.

        Validates that type reporting is delegated to the type layer.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(await StartsWith("a").enforce("url", 1, _OWNER))

    def testEmptyConfigurationRaises(self) -> None:
        """Raise ValueError when no prefix is supplied.

        Validates that the rule refuses an empty configuration.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            StartsWith()

class TestDoesntStartWith(TestCase):

    async def testForbiddenPrefixFails(self) -> None:
        """Return False when the value starts with a forbidden prefix.

        Validates that any configured prefix rejects the value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = DoesntStartWith("tmp_", "draft_")
        self.assertFalse(await rule.enforce("name", "tmp_report", _OWNER))
        self.assertFalse(await rule.enforce("name", "draft_report", _OWNER))

    async def testOtherPrefixPasses(self) -> None:
        """Return True when the value starts with an unrelated prefix.

        Validates that only the configured prefixes are rejected.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(await DoesntStartWith("tmp_").enforce("name", "report", _OWNER))

    async def testNonStringValuePasses(self) -> None:
        """Return True when the value is not a string.

        Validates that type reporting is delegated to the type layer.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(await DoesntStartWith("tmp_").enforce("name", 0, _OWNER))

    def testEmptyConfigurationRaises(self) -> None:
        """Raise ValueError when no prefix is supplied.

        Validates that the rule refuses an empty configuration.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            DoesntStartWith()

class TestIpAddress(TestCase):

    async def testDefaultsToVersionFour(self) -> None:
        """Return True only for IPv4 literals under the default configuration.

        Validates that IPv6 values are rejected unless requested.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = IpAddress()
        self.assertTrue(await rule.enforce("ip", "192.168.0.1", _OWNER))
        self.assertFalse(await rule.enforce("ip", "::1", _OWNER))

    async def testVersionSixAcceptsIpv6Only(self) -> None:
        """Return True only for IPv6 literals when version six is required.

        Validates that the version filter is applied after parsing.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = IpAddress(6)
        self.assertTrue(await rule.enforce("ip", "2001:db8::1", _OWNER))
        self.assertFalse(await rule.enforce("ip", "192.168.0.1", _OWNER))

    async def testVersionNoneAcceptsBothFamilies(self) -> None:
        """Return True for either family when no version is required.

        Validates that ``None`` disables the version filter.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = IpAddress(None)
        self.assertTrue(await rule.enforce("ip", "10.0.0.1", _OWNER))
        self.assertTrue(await rule.enforce("ip", "::1", _OWNER))

    async def testInvalidLiteralFails(self) -> None:
        """Return False when the value is not a parsable IP address.

        Validates that out-of-range octets and free text are rejected.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = IpAddress()
        self.assertFalse(await rule.enforce("ip", "999.1.1.1", _OWNER))
        self.assertFalse(await rule.enforce("ip", "not-an-ip", _OWNER))

    def testUnsupportedVersionRaises(self) -> None:
        """Raise ValueError when the configured version is unknown.

        Validates that the constructor rejects families it cannot check.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            IpAddress(5)

    async def testNonStringValuePasses(self) -> None:
        """Return True when the value is not a string.

        Validates that type reporting is delegated to the type layer.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(await IpAddress().enforce("ip", None, _OWNER))

class TestJson(TestCase):

    async def testValidDocumentsPass(self) -> None:
        """Return True for objects, arrays and scalars encoded as JSON.

        Validates that every JSON production is accepted.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = Json()
        for value in ('{"a": 1}', "[1, 2]", "123", '"text"', "null"):
            self.assertTrue(await rule.enforce("payload", value, _OWNER))

    async def testInvalidDocumentsFail(self) -> None:
        """Return False when the value is not parsable JSON.

        Validates that truncated and free-form text is rejected.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = Json()
        for value in ("{", "{'a': 1}", "", "undefined"):
            self.assertFalse(await rule.enforce("payload", value, _OWNER))

    async def testNonStringValuePasses(self) -> None:
        """Return True when the value is not a string.

        Validates that type reporting is delegated to the type layer.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(await Json().enforce("payload", {"a": 1}, _OWNER))

class TestLowercase(TestCase):

    async def testLowercaseContentPasses(self) -> None:
        """Return True when the value carries no uppercase character.

        Validates that caseless characters such as digits still pass.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = Lowercase()
        self.assertTrue(await rule.enforce("tag", "abc-123", _OWNER))
        self.assertTrue(await rule.enforce("tag", "123", _OWNER))
        self.assertTrue(await rule.enforce("tag", "ñandú", _OWNER))

    async def testUppercaseContentFails(self) -> None:
        """Return False when the value carries an uppercase character.

        Validates that a single capital letter rejects the value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(await Lowercase().enforce("tag", "Abc", _OWNER))

    async def testNonStringValuePasses(self) -> None:
        """Return True when the value is not a string.

        Validates that type reporting is delegated to the type layer.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(await Lowercase().enforce("tag", 1, _OWNER))

class TestUppercase(TestCase):

    async def testUppercaseContentPasses(self) -> None:
        """Return True when the value carries no lowercase character.

        Validates that caseless characters such as digits still pass.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = Uppercase()
        self.assertTrue(await rule.enforce("code", "ABC-123", _OWNER))
        self.assertTrue(await rule.enforce("code", "123", _OWNER))

    async def testLowercaseContentFails(self) -> None:
        """Return False when the value carries a lowercase character.

        Validates that a single small letter rejects the value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(await Uppercase().enforce("code", "ABc", _OWNER))

    async def testNonStringValuePasses(self) -> None:
        """Return True when the value is not a string.

        Validates that type reporting is delegated to the type layer.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(await Uppercase().enforce("code", 1, _OWNER))

class TestMacAddress(TestCase):

    async def testEveryNotationPasses(self) -> None:
        """Return True for the colon, hyphen and dotted notations.

        Validates that all three canonical spellings are accepted.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = MacAddress()
        for value in ("00:1B:44:11:3A:B7", "00-1b-44-11-3a-b7", "001b.4411.3ab7"):
            self.assertTrue(await rule.enforce("mac", value, _OWNER))

    async def testInvalidAddressFails(self) -> None:
        """Return False when the value is not a 48-bit hardware address.

        Validates that wrong lengths, separators and digits are rejected.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = MacAddress()
        for value in ("00:1B:44:11:3A", "zz:1B:44:11:3A:B7", "001b44113ab7", ""):
            self.assertFalse(await rule.enforce("mac", value, _OWNER))

    async def testNonStringValuePasses(self) -> None:
        """Return True when the value is not a string.

        Validates that type reporting is delegated to the type layer.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(await MacAddress().enforce("mac", None, _OWNER))

class TestUuid(TestCase):

    async def testAnyVersionPassesByDefault(self) -> None:
        """Return True for every canonical identifier when no version is set.

        Validates that the nil identifier and all versions are accepted.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = Uuid()
        for value in (_UUID_V4, _UUID_V1, _UUID_NIL):
            self.assertTrue(await rule.enforce("ident", value, _OWNER))

    async def testVersionFilterIsApplied(self) -> None:
        """Return True only when the identifier matches the required version.

        Validates that the version nibble is compared against the setting.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(await Uuid(4).enforce("ident", _UUID_V4, _OWNER))
        self.assertFalse(await Uuid(1).enforce("ident", _UUID_V4, _OWNER))
        self.assertTrue(await Uuid(1).enforce("ident", _UUID_V1, _OWNER))

    async def testVersionFilterRejectsNilIdentifier(self) -> None:
        """Return False for the nil identifier when a version is required.

        Validates that the variant nibble is also verified.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(await Uuid(4).enforce("ident", _UUID_NIL, _OWNER))

    async def testMalformedIdentifierFails(self) -> None:
        """Return False when the value is not a canonical identifier.

        Validates that wrong lengths and characters are rejected.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = Uuid()
        for value in ("not-a-uuid", _UUID_V4.replace("-", ""), ""):
            self.assertFalse(await rule.enforce("ident", value, _OWNER))

    def testUnsupportedVersionRaises(self) -> None:
        """Raise ValueError when the configured version is not in RFC 9562.

        Validates that the constructor rejects unknown layouts.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            Uuid(2)

    async def testNonStringValuePasses(self) -> None:
        """Return True when the value is not a string.

        Validates that type reporting is delegated to the type layer.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(await Uuid().enforce("ident", None, _OWNER))

class TestUlid(TestCase):

    async def testCanonicalIdentifierPasses(self) -> None:
        """Return True for a canonical identifier in either casing.

        Validates that the textual form is compared case-insensitively.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = Ulid()
        self.assertTrue(await rule.enforce("sortable", _ULID, _OWNER))
        self.assertTrue(await rule.enforce("sortable", _ULID.lower(), _OWNER))

    async def testWrongLengthFails(self) -> None:
        """Return False when the value is not 26 characters long.

        Validates that truncated and padded values are rejected.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = Ulid()
        self.assertFalse(await rule.enforce("sortable", _ULID[:-1], _OWNER))
        self.assertFalse(await rule.enforce("sortable", _ULID + "A", _OWNER))

    async def testExcludedAlphabetFails(self) -> None:
        """Return False when the value uses a character outside the alphabet.

        Validates that the ambiguous letters I, L, O and U are rejected.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(await Ulid().enforce("sortable", "I" + _ULID[1:], _OWNER))

    async def testTimestampOverflowFails(self) -> None:
        """Return False when the leading character overflows the timestamp.

        Validates that anything above ``7`` is rejected.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(await Ulid().enforce("sortable", "8" + _ULID[1:], _OWNER))

    async def testNonStringValuePasses(self) -> None:
        """Return True when the value is not a string.

        Validates that type reporting is delegated to the type layer.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(await Ulid().enforce("sortable", None, _OWNER))
