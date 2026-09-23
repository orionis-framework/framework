from xml.etree.ElementTree import ParseError

from defusedxml.common import DefusedXmlException, EntitiesForbidden

from orionis.http.payload.parsers import parse_xml
from orionis.test import TestCase
from tests.http.test_request import make_asgi_request


class TestXmlExceptionContract(TestCase):
    """Distinguish prohibited entity declarations from malformed XML."""

    async def testEntityDeclarationsRaiseEntitiesForbidden(self) -> None:
        """Expose the security exception unchanged through parser and request."""
        payloads = (
            b'<!DOCTYPE root [<!ENTITY item "text">]><root>&item;</root>',
            b'<!DOCTYPE root [<!ENTITY item "unused">]><root/>',
            (
                b'<!DOCTYPE root [<!ENTITY item SYSTEM "urn:orionis:xml:test">]>'
                b"<root>&item;</root>"
            ),
            (
                b'<!DOCTYPE root [<!ENTITY % item SYSTEM "urn:orionis:xml:test">'
                b"%item;]><root/>"
            ),
        )
        for payload in payloads:
            with self.assertRaises(DefusedXmlException) as parsed:
                parse_xml(payload)
            self.assertIsInstance(parsed.exception, EntitiesForbidden)
            self.assertNotIsInstance(parsed.exception, ParseError)

            request = make_asgi_request(body=payload)
            with self.assertRaises(DefusedXmlException) as requested:
                await request.xml()
            self.assertIsInstance(requested.exception, EntitiesForbidden)
            self.assertNotIsInstance(requested.exception, ParseError)

    async def testDtdWithoutEntityDeclarationsIsAllowed(self) -> None:
        """Keep harmless DTDs and predefined entities available to XML callers."""
        payloads = (
            (b"<!DOCTYPE root><root/>", None),
            (
                (
                    b"<!DOCTYPE root [<!ELEMENT root (#PCDATA)>]>"
                    b"<root>allowed &amp; safe</root>"
                ),
                "allowed & safe",
            ),
        )
        for payload, expected_text in payloads:
            parsed = parse_xml(payload)
            self.assertEqual(parsed.tag, "root")
            self.assertEqual(parsed.text, expected_text)

            requested = await make_asgi_request(body=payload).xml()
            self.assertEqual(requested.tag, "root")
            self.assertEqual(requested.text, expected_text)
