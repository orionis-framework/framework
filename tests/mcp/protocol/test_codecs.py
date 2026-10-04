"""Exercise actual protocol bytes before integrating any runtime layers."""

import unittest

import msgspec

from orionis.mcp.exceptions import McpProtocolException
from orionis.mcp.protocol.codecs import decode_envelope, decode_params, encode_error
from orionis.mcp.protocol.constants import CLIENT_CAPABILITIES, PROTOCOL_VERSION


class TestCodecs(unittest.TestCase):
    """Reject malformed envelopes and legacy negotiation consistently."""

    def request(self, method="tools/call", **params: object):
        """Build a complete modern request."""
        return decode_envelope(
            msgspec.json.encode(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": method,
                    "params": {
                        "_meta": {
                            PROTOCOL_VERSION: "2026-07-28",
                            CLIENT_CAPABILITIES: {},
                        },
                        **params,
                    },
                },
            ),
        )

    def test_typed_payload_stays_inside_arguments(self):
        """A dependency-looking argument cannot become an invocation kwarg."""
        request = self.request(name="weather", arguments={"repository": "attacker"})
        self.assertIsInstance(request.params, msgspec.Raw)
        params = decode_params(request)
        self.assertEqual(params.arguments, {"repository": "attacker"})

    def test_invalid_envelopes(self):
        """Reject batches, null/bool/fractional IDs and response messages."""
        for data in (
            b"[]",
            b"null",
            b'{"jsonrpc":"2.0","id":null,"method":"x"}',
            b'{"jsonrpc":"2.0","id":true,"method":"x"}',
            b'{"jsonrpc":"2.0","id":1.5,"method":"x"}',
            b'{"jsonrpc":"2.0","id":1,"result":{}}',
        ):
            with (
                self.subTest(data=data),
                self.assertRaises(McpProtocolException) as caught,
            ):
                decode_envelope(data)
            self.assertEqual(caught.exception.code, -32600)

    def test_parse_error_has_no_null_id(self):
        """The modern schema omits an unknown ID instead of serializing null."""
        with self.assertRaises(McpProtocolException) as caught:
            decode_envelope(b"{")
        result = msgspec.json.decode(encode_error(caught.exception))
        self.assertEqual(result["error"]["code"], -32700)
        self.assertNotIn("id", result)

    def test_unsupported_version_lists_only_modern(self):
        """Reject other versions without negotiation or fallback."""
        request = self.request(
            "server/discover",
            _meta={
                PROTOCOL_VERSION: "1900-01-01",
                CLIENT_CAPABILITIES: {},
            },
        )
        with self.assertRaises(McpProtocolException) as caught:
            decode_params(request)
        result = msgspec.json.decode(encode_error(caught.exception, request.id))
        self.assertEqual(result["error"]["code"], -32022)
        self.assertEqual(result["error"]["data"]["supported"], ["2026-07-28"])

    def test_initialize_is_unknown(self):
        """Keep legacy negotiation outside the dispatcher."""
        with self.assertRaises(McpProtocolException) as caught:
            decode_params(self.request("initialize"))
        self.assertEqual(caught.exception.code, -32601)
        self.assertIn("2026-07-28", caught.exception.message)

    def test_metadata_is_mandatory(self):
        """Every independent request carries its own version and capabilities."""
        for meta in (
            {},
            {PROTOCOL_VERSION: "2026-07-28"},
            {PROTOCOL_VERSION: "2026-07-28", CLIENT_CAPABILITIES: []},
        ):
            with (
                self.subTest(meta=meta),
                self.assertRaises(McpProtocolException) as caught,
            ):
                decode_params(self.request("server/discover", _meta=meta))
            self.assertEqual(caught.exception.code, -32602)

    def test_prompt_arguments_are_strings(self):
        """Reject JSON numbers instead of coercing them into prompt strings."""
        with self.assertRaises(McpProtocolException):
            decode_params(self.request("prompts/get", name="x", arguments={"tone": 1}))

    def test_notifications_have_no_id(self):
        """Distinguish a notification from a null-ID request."""
        request = decode_envelope(
            b'{"jsonrpc":"2.0","method":"notifications/cancelled"}',
        )
        self.assertIs(request.id, msgspec.UNSET)
