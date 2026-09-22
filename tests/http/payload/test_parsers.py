import json
from xml.etree.ElementTree import Element, ParseError
import msgspec
from orionis.http.payload.parsers import (
    parse_binary,
    parse_content_type,
    parse_json,
    parse_text,
    parse_urlencoded,
    parse_urlencoded_multi,
    parse_xml,
)
from orionis.test import TestCase

class TestParseContentType(TestCase):
    """Verify parse_content_type."""

    def testSimpleMediaType(self) -> None:
        """
        Verify that a bare media type is returned with an empty params dict.

        Confirms the fast path when no semicolon is present.
        """
        media_type, params = parse_content_type("application/json")
        self.assertEqual(media_type, "application/json")
        self.assertEqual(params, {})

    def testMediaTypeWithBoundary(self) -> None:
        """
        Verify that a boundary parameter is extracted correctly.

        Confirms that the parameter dict contains the boundary key after
        parsing a multipart Content-Type header.
        """
        header = "multipart/form-data; boundary=----WebKit"
        media_type, params = parse_content_type(header)
        self.assertEqual(media_type, "multipart/form-data")
        self.assertEqual(params["boundary"], "----WebKit")

    def testMediaTypeIsLowercased(self) -> None:
        """
        Verify that the media type is normalised to lowercase.

        Confirms that 'Application/JSON' is returned as 'application/json'.
        """
        media_type, _ = parse_content_type("Application/JSON")
        self.assertEqual(media_type, "application/json")

    def testCharsetParameter(self) -> None:
        """
        Verify that a charset parameter is extracted from the header.

        Confirms that 'text/html; charset=UTF-8' produces charset='utf-8'
        (value is not lowercased by the parser, key is).
        """
        _, params = parse_content_type("text/html; charset=UTF-8")
        self.assertIn("charset", params)
        self.assertEqual(params["charset"], "UTF-8")

    def testMultipleParameters(self) -> None:
        """
        Verify that multiple parameters are all extracted.

        Confirms that both boundary and charset are present when the
        header contains two semicolon-delimited parameters.
        """
        header = "multipart/mixed; boundary=abc; charset=utf-8"
        _, params = parse_content_type(header)
        self.assertIn("boundary", params)
        self.assertIn("charset", params)

    def testEmptyHeaderReturnsEmptyString(self) -> None:
        """
        Verify that an empty header string returns an empty media type.

        Confirms the function handles degenerate input without raising.
        """
        media_type, params = parse_content_type("")
        self.assertEqual(media_type, "")
        self.assertEqual(params, {})

class TestParseJson(TestCase):
    """Verify parse_json."""

    def testSimpleObject(self) -> None:
        """
        Verify that a JSON object payload is decoded to a dict.

        Confirms that parse_json returns the expected key-value mapping.
        """
        raw = b'{"key": "value"}'
        result = parse_json(raw)
        self.assertEqual(result, {"key": "value"})

    def testArrayPayload(self) -> None:
        """
        Verify that a JSON array payload is decoded to a list.

        Confirms that parse_json returns a list for top-level arrays.
        """
        raw = b"[1, 2, 3]"
        result = parse_json(raw)
        self.assertEqual(result, [1, 2, 3])

    def testNullPayload(self) -> None:
        """
        Verify that a JSON null payload is decoded to None.

        Confirms that the Python None sentinel is returned for null.
        """
        self.assertIsNone(parse_json(b"null"))

    def testBooleanPayload(self) -> None:
        """
        Verify that JSON boolean values are decoded correctly.

        Confirms that true and false map to Python True and False.
        """
        self.assertIs(parse_json(b"true"), True)
        self.assertIs(parse_json(b"false"), False)

    def testInvalidJsonRaisesDecodeError(self) -> None:
        """
        Verify that malformed JSON raises a decode exception.

        Confirms that invalid bytes cause an exception compatible with
        the msgspec.DecodeError hierarchy.
        """
        with self.assertRaises(msgspec.DecodeError):
            parse_json(b"{invalid json}")

    def testNestedObject(self) -> None:
        """
        Verify that nested JSON objects are decoded correctly.

        Confirms that multi-level dicts survive the decode cycle.
        """
        payload = {"a": {"b": {"c": 1}}}
        raw = json.dumps(payload).encode()
        self.assertEqual(parse_json(raw), payload)

class TestParseUrlencoded(TestCase):
    """Verify parse_urlencoded."""

    def testSimplePair(self) -> None:
        """
        Verify that a single key=value pair is decoded correctly.

        Confirms that the returned dict maps the key to the raw value.
        """
        result = parse_urlencoded(b"name=alice")
        self.assertEqual(result, {"name": "alice"})

    def testMultiplePairs(self) -> None:
        """
        Verify that multiple key=value pairs are decoded correctly.

        Confirms all pairs are present in the returned dict.
        """
        result = parse_urlencoded(b"a=1&b=2&c=3")
        self.assertEqual(result, {"a": "1", "b": "2", "c": "3"})

    def testBlankValuePreserved(self) -> None:
        """
        Verify that a key with an empty value is preserved.

        Confirms that keep_blank_values=True is in effect.
        """
        result = parse_urlencoded(b"empty=")
        self.assertEqual(result["empty"], "")

    def testUrlEncodedCharactersDecoded(self) -> None:
        """
        Verify that percent-encoded characters are decoded.

        Confirms that %40 is decoded to '@' in the returned dict.
        """
        result = parse_urlencoded(b"email=user%40example.com")
        self.assertEqual(result["email"], "user@example.com")

    def testEmptyBodyReturnsEmptyDict(self) -> None:
        """
        Verify that an empty byte string returns an empty dict.

        Confirms that no error is raised for empty URL-encoded input.
        """
        self.assertEqual(parse_urlencoded(b""), {})

class TestParseUrlencodedMulti(TestCase):
    """Verify parse_urlencoded_multi."""

    def testSingleOccurrenceIsScalar(self) -> None:
        """
        Verify that a key appearing once yields a plain string value.

        Confirms that single-occurrence keys are not promoted to lists.
        """
        result = parse_urlencoded_multi(b"x=1")
        self.assertEqual(result["x"], "1")

    def testDuplicateKeyProducesList(self) -> None:
        """
        Verify that a key appearing twice yields a list of values.

        Confirms that duplicate-key semantics are preserved.
        """
        result = parse_urlencoded_multi(b"tag=a&tag=b")
        self.assertEqual(result["tag"], ["a", "b"])

    def testTripleDuplicateKey(self) -> None:
        """
        Verify that a key appearing three times yields a three-element list.

        Confirms that more than two occurrences are accumulated correctly.
        """
        result = parse_urlencoded_multi(b"v=1&v=2&v=3")
        self.assertEqual(result["v"], ["1", "2", "3"])

    def testMixedSingleAndMultipleKeys(self) -> None:
        """
        Verify that a mix of single and multi-occurrence keys is handled.

        Confirms that single-key entries remain scalars while multi-key
        entries become lists in the same result dict.
        """
        result = parse_urlencoded_multi(b"a=1&b=x&b=y")
        self.assertEqual(result["a"], "1")
        self.assertEqual(result["b"], ["x", "y"])

class TestParseText(TestCase):
    """Verify parse_text."""

    def testUtf8BytesDecoded(self) -> None:
        """
        Verify that UTF-8 bytes are decoded to a str.

        Confirms basic ASCII text is returned as a Python string.
        """
        self.assertEqual(parse_text(b"hello world"), "hello world")

    def testUnicodeCharactersPreserved(self) -> None:
        """
        Verify that multi-byte UTF-8 sequences are decoded correctly.

        Confirms that non-ASCII Unicode characters survive the round-trip.
        """
        original = "héllo wörld"
        self.assertEqual(parse_text(original.encode("utf-8")), original)

    def testEmptyBytesReturnsEmptyString(self) -> None:
        """
        Verify that empty bytes return an empty string.

        Confirms that zero-length input does not raise an error.
        """
        self.assertEqual(parse_text(b""), "")

    def testInvalidUtf8RaisesUnicodeDecodeError(self) -> None:
        """
        Verify that invalid UTF-8 bytes raise UnicodeDecodeError.

        Confirms the strict decoder behaviour when bytes are not valid UTF-8.
        """
        with self.assertRaises(UnicodeDecodeError):
            parse_text(b"\xff\xfe")

class TestParseBinary(TestCase):
    """Verify parse_binary."""

    def testBytesReturnedUnchanged(self) -> None:
        """
        Verify that parse_binary returns the input bytes unchanged.

        Confirms that binary payloads are passed through without mutation.
        """
        raw = b"\x00\xff\xab\xcd"
        self.assertEqual(parse_binary(raw), raw)

    def testEmptyBytesReturnsEmpty(self) -> None:
        """
        Verify that empty bytes are returned as empty bytes.

        Confirms the function handles zero-length input.
        """
        self.assertEqual(parse_binary(b""), b"")

class TestParseXml(TestCase):
    """Verify parse_xml."""

    def testSimpleXmlParsed(self) -> None:
        """
        Verify that a simple XML document is parsed to an Element.

        Confirms that the root tag of the returned Element matches the
        document root.
        """
        raw = b"<root><child>text</child></root>"
        element = parse_xml(raw)
        self.assertIsInstance(element, Element)
        self.assertEqual(element.tag, "root")

    def testChildElementAccessible(self) -> None:
        """
        Verify that child elements are accessible on the parsed root.

        Confirms that the tree structure is preserved after parsing.
        """
        raw = b"<items><item>1</item><item>2</item></items>"
        root = parse_xml(raw)
        children = list(root)
        self.assertEqual(len(children), 2)

    def testMalformedXmlRaises(self) -> None:
        """
        Verify that malformed XML raises a ParseError.

        Confirms that invalid XML bytes cause an exception.
        """
        with self.assertRaises(ParseError):
            parse_xml(b"<unclosed>")
