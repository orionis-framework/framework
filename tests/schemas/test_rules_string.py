from unittest.mock import patch
import socket
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

    def testAcceptsTruthyStrings(self) -> None:
        """
        Return True for every textual representation of an acceptance.

        Validates that ``yes``, ``on``, ``1`` and ``true`` are accepted
        regardless of their casing.
        """
        rule = Accepted()
        for value in ("yes", "on", "1", "true", "YES", "True"):
            self.assertTrue(rule.enforce("terms", value, _OWNER))

    def testAcceptsBooleanAndInteger(self) -> None:
        """
        Return True for the boolean and integer acceptance values.

        Validates that ``True`` and ``1`` are treated as an acceptance.
        """
        rule = Accepted()
        self.assertTrue(rule.enforce("terms", True, _OWNER))
        self.assertTrue(rule.enforce("terms", 1, _OWNER))

    def testRejectsFalsyValues(self) -> None:
        """
        Return False for values that do not express an acceptance.

        Validates that negatives, zero, ``None`` and unrelated types fail.
        """
        rule = Accepted()
        for value in (False, 0, 2, "no", "off", "", None, [], object()):
            self.assertFalse(rule.enforce("terms", value, _OWNER))

    def testCodeAndDefaultMessage(self) -> None:
        """
        Expose the documented rule code in the reported failure.

        Validates that a rejected value produces a failure carrying the
        ``accepted`` code.
        """
        failure = Accepted().validate("terms", "no", _OWNER)
        self.assertIsNotNone(failure)
        self.assertEqual(failure.rule, "accepted")

class TestActiveUrl(TestCase):

    def testResolvableHostnamePasses(self) -> None:
        """
        Return True when the hostname resolves through the system resolver.

        Validates the success path without depending on real DNS traffic.
        """
        rule = ActiveUrl()
        target = "orionis.schemas.rules.active_url.socket.getaddrinfo"
        with patch(target, return_value=[("family", "type", 6, "", ("1.2.3.4", 0))]):
            self.assertTrue(rule.enforce("url", "https://example.com/a", _OWNER))

    def testUnresolvableHostnameFails(self) -> None:
        """
        Return False when the resolver reports an unknown hostname.

        Validates that a ``gaierror`` is translated into a failed check.
        """
        rule = ActiveUrl()
        target = "orionis.schemas.rules.active_url.socket.getaddrinfo"
        with patch(target, side_effect=socket.gaierror):
            self.assertFalse(rule.enforce("url", "https://example.com", _OWNER))

    def testUrlWithoutHostnameFails(self) -> None:
        """
        Return False when the value carries no hostname component.

        Validates that relative paths and bare words are rejected before
        any lookup is attempted.
        """
        rule = ActiveUrl()
        self.assertFalse(rule.enforce("url", "/relative/path", _OWNER))
        self.assertFalse(rule.enforce("url", "", _OWNER))

    def testMalformedUrlFails(self) -> None:
        """
        Return False when the value cannot be split into URL components.

        Validates that a malformed IPv6 literal does not raise.
        """
        rule = ActiveUrl()
        self.assertFalse(rule.enforce("url", "http://[oops", _OWNER))

    def testNonStringValuePasses(self) -> None:
        """
        Return True when the value is not a string.

        Validates that type reporting is delegated to the type layer.
        """
        self.assertTrue(ActiveUrl().enforce("url", 123, _OWNER))

class TestAlpha(TestCase):

    def testUnicodeLettersPass(self) -> None:
        """
        Return True for Unicode letters and combining marks.

        Validates that accented text and decomposed characters are
        accepted by the default configuration.
        """
        rule = Alpha()
        self.assertTrue(rule.enforce("name", "José", _OWNER))
        self.assertTrue(rule.enforce("name", "e\u0301", _OWNER))

    def testNonLettersFail(self) -> None:
        """
        Return False when the value carries digits, spaces or symbols.

        Validates that only alphabetic content is accepted.
        """
        rule = Alpha()
        for value in ("abc1", "ab c", "ab-c", ""):
            self.assertFalse(rule.enforce("name", value, _OWNER))

    def testAsciiOnlyRejectsAccents(self) -> None:
        """
        Return False for non-ASCII letters when ``ascii_only`` is enabled.

        Validates that the restricted mode narrows the accepted range to
        ``a-z`` and ``A-Z``.
        """
        rule = Alpha(ascii_only=True)
        self.assertTrue(rule.enforce("name", "Jose", _OWNER))
        self.assertFalse(rule.enforce("name", "José", _OWNER))

    def testNonStringValuePasses(self) -> None:
        """
        Return True when the value is not a string.

        Validates that type reporting is delegated to the type layer.
        """
        self.assertTrue(Alpha().enforce("name", 10, _OWNER))

class TestAscii(TestCase):

    def testSevenBitContentPasses(self) -> None:
        """
        Return True for content limited to the 7-bit ASCII range.

        Validates that letters, digits and punctuation are accepted.
        """
        self.assertTrue(Ascii().enforce("tag", "abc-123_!", _OWNER))

    def testNonAsciiContentFails(self) -> None:
        """
        Return False when the value carries characters beyond ASCII.

        Validates that accented and emoji content is rejected.
        """
        rule = Ascii()
        self.assertFalse(rule.enforce("tag", "ñandú", _OWNER))
        self.assertFalse(rule.enforce("tag", "a€", _OWNER))

    def testNonStringValuePasses(self) -> None:
        """
        Return True when the value is not a string.

        Validates that type reporting is delegated to the type layer.
        """
        self.assertTrue(Ascii().enforce("tag", None, _OWNER))

class TestEndsWith(TestCase):

    def testMatchingSuffixPasses(self) -> None:
        """
        Return True when the value ends with one of the suffixes.

        Validates that any configured suffix satisfies the rule.
        """
        rule = EndsWith(".png", ".jpg")
        self.assertTrue(rule.enforce("file", "photo.png", _OWNER))
        self.assertTrue(rule.enforce("file", "photo.jpg", _OWNER))

    def testMissingSuffixFails(self) -> None:
        """
        Return False when the value ends with none of the suffixes.

        Validates that unrelated extensions are rejected.
        """
        self.assertFalse(EndsWith(".png").enforce("file", "photo.gif", _OWNER))

    def testSuffixMatchIsCaseSensitive(self) -> None:
        """
        Return False when only the casing differs from the suffix.

        Validates that comparison never folds the case.
        """
        self.assertFalse(EndsWith(".png").enforce("file", "photo.PNG", _OWNER))

    def testNonStringValuePasses(self) -> None:
        """
        Return True when the value is not a string.

        Validates that type reporting is delegated to the type layer.
        """
        self.assertTrue(EndsWith(".png").enforce("file", 5, _OWNER))

    def testEmptyConfigurationRaises(self) -> None:
        """
        Raise ValueError when no suffix is supplied.

        Validates that the rule refuses an configuration that can never
        be satisfied.
        """
        with self.assertRaises(ValueError):
            EndsWith()

class TestDoesntEndWith(TestCase):

    def testForbiddenSuffixFails(self) -> None:
        """
        Return False when the value ends with a forbidden suffix.

        Validates that any configured suffix rejects the value.
        """
        rule = DoesntEndWith(".exe", ".bat")
        self.assertFalse(rule.enforce("file", "setup.exe", _OWNER))
        self.assertFalse(rule.enforce("file", "setup.bat", _OWNER))

    def testOtherSuffixPasses(self) -> None:
        """
        Return True when the value ends with an unrelated suffix.

        Validates that only the configured suffixes are rejected.
        """
        self.assertTrue(DoesntEndWith(".exe").enforce("file", "a.txt", _OWNER))

    def testNonStringValuePasses(self) -> None:
        """
        Return True when the value is not a string.

        Validates that type reporting is delegated to the type layer.
        """
        self.assertTrue(DoesntEndWith(".exe").enforce("file", None, _OWNER))

    def testEmptyConfigurationRaises(self) -> None:
        """
        Raise ValueError when no suffix is supplied.

        Validates that the rule refuses an empty configuration.
        """
        with self.assertRaises(ValueError):
            DoesntEndWith()

class TestStartsWith(TestCase):

    def testMatchingPrefixPasses(self) -> None:
        """
        Return True when the value starts with one of the prefixes.

        Validates that any configured prefix satisfies the rule.
        """
        rule = StartsWith("https://", "http://")
        self.assertTrue(rule.enforce("url", "https://a.test", _OWNER))
        self.assertTrue(rule.enforce("url", "http://a.test", _OWNER))

    def testMissingPrefixFails(self) -> None:
        """
        Return False when the value starts with none of the prefixes.

        Validates that unrelated schemes are rejected.
        """
        self.assertFalse(StartsWith("https://").enforce("url", "ftp://a", _OWNER))

    def testNonStringValuePasses(self) -> None:
        """
        Return True when the value is not a string.

        Validates that type reporting is delegated to the type layer.
        """
        self.assertTrue(StartsWith("a").enforce("url", 1, _OWNER))

    def testEmptyConfigurationRaises(self) -> None:
        """
        Raise ValueError when no prefix is supplied.

        Validates that the rule refuses an empty configuration.
        """
        with self.assertRaises(ValueError):
            StartsWith()

class TestDoesntStartWith(TestCase):

    def testForbiddenPrefixFails(self) -> None:
        """
        Return False when the value starts with a forbidden prefix.

        Validates that any configured prefix rejects the value.
        """
        rule = DoesntStartWith("tmp_", "draft_")
        self.assertFalse(rule.enforce("name", "tmp_report", _OWNER))
        self.assertFalse(rule.enforce("name", "draft_report", _OWNER))

    def testOtherPrefixPasses(self) -> None:
        """
        Return True when the value starts with an unrelated prefix.

        Validates that only the configured prefixes are rejected.
        """
        self.assertTrue(DoesntStartWith("tmp_").enforce("name", "report", _OWNER))

    def testNonStringValuePasses(self) -> None:
        """
        Return True when the value is not a string.

        Validates that type reporting is delegated to the type layer.
        """
        self.assertTrue(DoesntStartWith("tmp_").enforce("name", 0, _OWNER))

    def testEmptyConfigurationRaises(self) -> None:
        """
        Raise ValueError when no prefix is supplied.

        Validates that the rule refuses an empty configuration.
        """
        with self.assertRaises(ValueError):
            DoesntStartWith()

class TestIpAddress(TestCase):

    def testDefaultsToVersionFour(self) -> None:
        """
        Return True only for IPv4 literals under the default configuration.

        Validates that IPv6 values are rejected unless requested.
        """
        rule = IpAddress()
        self.assertTrue(rule.enforce("ip", "192.168.0.1", _OWNER))
        self.assertFalse(rule.enforce("ip", "::1", _OWNER))

    def testVersionSixAcceptsIpv6Only(self) -> None:
        """
        Return True only for IPv6 literals when version six is required.

        Validates that the version filter is applied after parsing.
        """
        rule = IpAddress(6)
        self.assertTrue(rule.enforce("ip", "2001:db8::1", _OWNER))
        self.assertFalse(rule.enforce("ip", "192.168.0.1", _OWNER))

    def testVersionNoneAcceptsBothFamilies(self) -> None:
        """
        Return True for either family when no version is required.

        Validates that ``None`` disables the version filter.
        """
        rule = IpAddress(None)
        self.assertTrue(rule.enforce("ip", "10.0.0.1", _OWNER))
        self.assertTrue(rule.enforce("ip", "::1", _OWNER))

    def testInvalidLiteralFails(self) -> None:
        """
        Return False when the value is not a parsable IP address.

        Validates that out-of-range octets and free text are rejected.
        """
        rule = IpAddress()
        self.assertFalse(rule.enforce("ip", "999.1.1.1", _OWNER))
        self.assertFalse(rule.enforce("ip", "not-an-ip", _OWNER))

    def testUnsupportedVersionRaises(self) -> None:
        """
        Raise ValueError when the configured version is unknown.

        Validates that the constructor rejects families it cannot check.
        """
        with self.assertRaises(ValueError):
            IpAddress(5)

    def testNonStringValuePasses(self) -> None:
        """
        Return True when the value is not a string.

        Validates that type reporting is delegated to the type layer.
        """
        self.assertTrue(IpAddress().enforce("ip", None, _OWNER))

class TestJson(TestCase):

    def testValidDocumentsPass(self) -> None:
        """
        Return True for objects, arrays and scalars encoded as JSON.

        Validates that every JSON production is accepted.
        """
        rule = Json()
        for value in ('{"a": 1}', "[1, 2]", "123", '"text"', "null"):
            self.assertTrue(rule.enforce("payload", value, _OWNER))

    def testInvalidDocumentsFail(self) -> None:
        """
        Return False when the value is not parsable JSON.

        Validates that truncated and free-form text is rejected.
        """
        rule = Json()
        for value in ("{", "{'a': 1}", "", "undefined"):
            self.assertFalse(rule.enforce("payload", value, _OWNER))

    def testNonStringValuePasses(self) -> None:
        """
        Return True when the value is not a string.

        Validates that type reporting is delegated to the type layer.
        """
        self.assertTrue(Json().enforce("payload", {"a": 1}, _OWNER))

class TestLowercase(TestCase):

    def testLowercaseContentPasses(self) -> None:
        """
        Return True when the value carries no uppercase character.

        Validates that caseless characters such as digits still pass.
        """
        rule = Lowercase()
        self.assertTrue(rule.enforce("tag", "abc-123", _OWNER))
        self.assertTrue(rule.enforce("tag", "123", _OWNER))
        self.assertTrue(rule.enforce("tag", "ñandú", _OWNER))

    def testUppercaseContentFails(self) -> None:
        """
        Return False when the value carries an uppercase character.

        Validates that a single capital letter rejects the value.
        """
        self.assertFalse(Lowercase().enforce("tag", "Abc", _OWNER))

    def testNonStringValuePasses(self) -> None:
        """
        Return True when the value is not a string.

        Validates that type reporting is delegated to the type layer.
        """
        self.assertTrue(Lowercase().enforce("tag", 1, _OWNER))

class TestUppercase(TestCase):

    def testUppercaseContentPasses(self) -> None:
        """
        Return True when the value carries no lowercase character.

        Validates that caseless characters such as digits still pass.
        """
        rule = Uppercase()
        self.assertTrue(rule.enforce("code", "ABC-123", _OWNER))
        self.assertTrue(rule.enforce("code", "123", _OWNER))

    def testLowercaseContentFails(self) -> None:
        """
        Return False when the value carries a lowercase character.

        Validates that a single small letter rejects the value.
        """
        self.assertFalse(Uppercase().enforce("code", "ABc", _OWNER))

    def testNonStringValuePasses(self) -> None:
        """
        Return True when the value is not a string.

        Validates that type reporting is delegated to the type layer.
        """
        self.assertTrue(Uppercase().enforce("code", 1, _OWNER))

class TestMacAddress(TestCase):

    def testEveryNotationPasses(self) -> None:
        """
        Return True for the colon, hyphen and dotted notations.

        Validates that all three canonical spellings are accepted.
        """
        rule = MacAddress()
        for value in ("00:1B:44:11:3A:B7", "00-1b-44-11-3a-b7", "001b.4411.3ab7"):
            self.assertTrue(rule.enforce("mac", value, _OWNER))

    def testInvalidAddressFails(self) -> None:
        """
        Return False when the value is not a 48-bit hardware address.

        Validates that wrong lengths, separators and digits are rejected.
        """
        rule = MacAddress()
        for value in ("00:1B:44:11:3A", "zz:1B:44:11:3A:B7", "001b44113ab7", ""):
            self.assertFalse(rule.enforce("mac", value, _OWNER))

    def testNonStringValuePasses(self) -> None:
        """
        Return True when the value is not a string.

        Validates that type reporting is delegated to the type layer.
        """
        self.assertTrue(MacAddress().enforce("mac", None, _OWNER))

class TestUuid(TestCase):

    def testAnyVersionPassesByDefault(self) -> None:
        """
        Return True for every canonical identifier when no version is set.

        Validates that the nil identifier and all versions are accepted.
        """
        rule = Uuid()
        for value in (_UUID_V4, _UUID_V1, _UUID_NIL):
            self.assertTrue(rule.enforce("ident", value, _OWNER))

    def testVersionFilterIsApplied(self) -> None:
        """
        Return True only when the identifier matches the required version.

        Validates that the version nibble is compared against the setting.
        """
        self.assertTrue(Uuid(4).enforce("ident", _UUID_V4, _OWNER))
        self.assertFalse(Uuid(1).enforce("ident", _UUID_V4, _OWNER))
        self.assertTrue(Uuid(1).enforce("ident", _UUID_V1, _OWNER))

    def testVersionFilterRejectsNilIdentifier(self) -> None:
        """
        Return False for the nil identifier when a version is required.

        Validates that the variant nibble is also verified.
        """
        self.assertFalse(Uuid(4).enforce("ident", _UUID_NIL, _OWNER))

    def testMalformedIdentifierFails(self) -> None:
        """
        Return False when the value is not a canonical identifier.

        Validates that wrong lengths and characters are rejected.
        """
        rule = Uuid()
        for value in ("not-a-uuid", _UUID_V4.replace("-", ""), ""):
            self.assertFalse(rule.enforce("ident", value, _OWNER))

    def testUnsupportedVersionRaises(self) -> None:
        """
        Raise ValueError when the configured version is not in RFC 9562.

        Validates that the constructor rejects unknown layouts.
        """
        with self.assertRaises(ValueError):
            Uuid(2)

    def testNonStringValuePasses(self) -> None:
        """
        Return True when the value is not a string.

        Validates that type reporting is delegated to the type layer.
        """
        self.assertTrue(Uuid().enforce("ident", None, _OWNER))

class TestUlid(TestCase):

    def testCanonicalIdentifierPasses(self) -> None:
        """
        Return True for a canonical identifier in either casing.

        Validates that the textual form is compared case-insensitively.
        """
        rule = Ulid()
        self.assertTrue(rule.enforce("sortable", _ULID, _OWNER))
        self.assertTrue(rule.enforce("sortable", _ULID.lower(), _OWNER))

    def testWrongLengthFails(self) -> None:
        """
        Return False when the value is not 26 characters long.

        Validates that truncated and padded values are rejected.
        """
        rule = Ulid()
        self.assertFalse(rule.enforce("sortable", _ULID[:-1], _OWNER))
        self.assertFalse(rule.enforce("sortable", _ULID + "A", _OWNER))

    def testExcludedAlphabetFails(self) -> None:
        """
        Return False when the value uses a character outside the alphabet.

        Validates that the ambiguous letters I, L, O and U are rejected.
        """
        self.assertFalse(Ulid().enforce("sortable", "I" + _ULID[1:], _OWNER))

    def testTimestampOverflowFails(self) -> None:
        """
        Return False when the leading character overflows the timestamp.

        Validates that anything above ``7`` is rejected.
        """
        self.assertFalse(Ulid().enforce("sortable", "8" + _ULID[1:], _OWNER))

    def testNonStringValuePasses(self) -> None:
        """
        Return True when the value is not a string.

        Validates that type reporting is delegated to the type layer.
        """
        self.assertTrue(Ulid().enforce("sortable", None, _OWNER))
