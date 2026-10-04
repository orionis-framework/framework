"""Check HTTP metadata against real protocol decoding and native header storage."""

import base64
import unittest

import msgspec

from orionis.http.payload.estructures.headers import Headers
from orionis.mcp.exceptions import McpProtocolException
from orionis.mcp.protocol.codecs import decode_envelope, decode_params
from orionis.mcp.protocol.constants import CLIENT_CAPABILITIES, PROTOCOL_VERSION
from orionis.mcp.transport.headers import compile_header_bindings, validate_headers


class TestHeaders(unittest.TestCase):
    """Cover header ambiguity, encoded names and compiled parameter extraction."""

    def request(self, method="tools/call", **params: object):
        """Create protocol bytes with mandatory metadata and an explicit request ID."""
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

    def headers(self, method="tools/call", name="weather", extra=()):
        """Preserve original pairs so duplicate headers reach validation."""
        return Headers(
            [
                ("MCP-Protocol-Version", "2026-07-28"),
                ("Mcp-Method", method),
                *((("Mcp-Name", name),) if name is not None else ()),
                *extra,
            ],
        )

    def encoded(self, value):
        """Construct the specification's case-sensitive UTF-8 sentinel."""
        return "=?base64?" + base64.b64encode(value.encode()).decode() + "?="

    def assertMismatch(self, headers, request, bindings=()):
        """Check the exact JSON-RPC and HTTP header-validation error pair."""
        with self.assertRaises(McpProtocolException) as caught:
            validate_headers(headers, request, bindings=bindings)
        self.assertEqual(
            (caught.exception.code, caught.exception.status), (-32020, 400),
        )

    def test_standard_headers_match_typed_and_raw_parameters(self):
        """Known typed params and unknown raw methods share the same header gate."""
        for method, params, name in (
            ("tools/call", {"name": "weather"}, "weather"),
            ("prompts/get", {"name": "weather"}, "weather"),
            ("resources/read", {"uri": "file:///weather"}, "file:///weather"),
            ("server/discover", {}, None),
        ):
            request = self.request(method, **params)
            validate_headers(
                self.headers(method, name), request, decode_params(request),
            )
            validate_headers(self.headers(method, name), request)
        request = self.request("unknown")
        validate_headers(self.headers("unknown", None), request)
        with self.assertRaises(McpProtocolException) as caught:
            decode_params(request)
        self.assertEqual(caught.exception.status, 404)

    def test_required_mismatch_and_duplicate_headers(self):
        """Reject missing metadata and disagreeing or repeated singleton headers."""
        request = self.request(name="weather")
        pairs = list(self.headers())
        for index in range(len(pairs)):
            self.assertMismatch(Headers(pairs[:index] + pairs[index + 1 :]), request)
            changed = list(pairs)
            changed[index] = (pairs[index][0], "different")
            self.assertMismatch(Headers(changed), request)
            self.assertMismatch(
                Headers([*pairs, (pairs[index][0].upper(), pairs[index][1])]), request,
            )

    def test_header_name_case_and_value_case_are_distinct(self):
        """Normalize field names without case folding method or name values."""
        request = self.request(name="weather")
        validate_headers(
            Headers([(key.swapcase(), value) for key, value in self.headers()]),
            request,
        )
        self.assertMismatch(self.headers(name="WEATHER"), request)
        self.assertMismatch(self.headers(method="TOOLS/CALL"), request)

    def test_legacy_missing_headers_fail_before_unknown_method(self):
        """A header-less initialize receives the modern header validation error."""
        request = decode_envelope(b'{"jsonrpc":"2.0","id":1,"method":"initialize"}')
        self.assertMismatch(Headers([]), request)

    def test_missing_body_metadata_is_invalid_params_when_headers_exist(self):
        """Honor the official stateless conformance error classification."""
        for params in ({}, {"_meta": {}}, {"_meta": {PROTOCOL_VERSION: None}}):
            request = decode_envelope(msgspec.json.encode({
                "jsonrpc": "2.0", "id": 1, "method": "server/discover",
                "params": params,
            }))
            with self.assertRaises(McpProtocolException) as caught:
                validate_headers(self.headers("server/discover", None), request)
            self.assertEqual(caught.exception.code, -32602)

    def test_unsupported_matching_version_is_left_to_protocol(self):
        """Do not misclassify a matching unsupported version as a header mismatch."""
        request = self.request(
            "server/discover",
            _meta={
                PROTOCOL_VERSION: "1900-01-01",
                CLIENT_CAPABILITIES: {},
            },
        )
        validate_headers(
            Headers(
                [
                    ("mcp-protocol-version", "1900-01-01"),
                    ("mcp-method", "server/discover"),
                ],
            ),
            request,
        )
        with self.assertRaises(McpProtocolException) as caught:
            decode_params(request)
        self.assertEqual(caught.exception.code, -32022)

    def test_unicode_whitespace_and_sentinel_name_encoding(self):
        """Decode UTF-8 names and literals that would otherwise resemble sentinels."""
        for name in ("Café 世界", " padded ", "line1\nline2", "=?base64?literal?="):
            request = self.request(name=name)
            validate_headers(self.headers(name=self.encoded(name)), request)
            self.assertMismatch(self.headers(name=name), request)

    def test_malformed_encoded_values_and_unsafe_raw_values(self):
        """Reject invalid Base64, invalid UTF-8, controls and outer whitespace."""
        request = self.request(name="weather")
        for value in (
            "=?base64?%%%?=",
            "=?base64?/w==?=",
            "weather\r\nX: y",
            " weather",
            "weather\t",
            "wea\x00ther",
            "café",
        ):
            self.assertMismatch(self.headers(name=value), request)

    def test_static_nested_paths_are_compiled_without_dotted_key_expansion(self):
        """Nested properties and literal dotted properties resolve independently."""
        schema = {
            "type": "object",
            "properties": {
                "region": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "x-mcp-header": "Region"},
                    },
                },
                "region.name": {"type": "boolean", "x-mcp-header": "Enabled"},
            },
        }
        bindings = compile_header_bindings(schema)
        self.assertEqual(bindings[0].path, ("region", "name"))
        request = self.request(
            name="weather",
            arguments={
                "region": {"name": "us-west1"},
                "region.name": True,
            },
        )
        validate_headers(
            self.headers(
                extra=(
                    ("mcp-param-region", "us-west1"),
                    ("Mcp-Param-Enabled", "true"),
                ),
            ),
            request,
            bindings=bindings,
        )

    def test_schema_rejects_unreachable_annotations_and_duplicate_names(self):
        """Fail malformed catalog metadata at compilation rather than first call."""
        annotated = {"type": "string", "x-mcp-header": "Region"}
        for schema in (
            annotated,
            {"items": annotated},
            {"$defs": {"value": annotated}},
            {"oneOf": [{"properties": {"value": annotated}}]},
            {"properties": {"x": {"if": {"properties": {"x": annotated}}}}},
            {
                "properties": {
                    "a": annotated,
                    "b": {**annotated, "x-mcp-header": "REGION"},
                },
            },
        ):
            with self.subTest(schema=schema), self.assertRaises(ValueError):
                compile_header_bindings(schema)

    def test_schema_rejects_invalid_names_and_nonprimitive_types(self):
        """Token syntax and primitive restrictions cover CRLF and nullable unions."""
        for name in ("", "two words", "name:colon", "line\r\n", 1):
            with self.subTest(name=name), self.assertRaises(ValueError):
                compile_header_bindings(
                    {
                        "properties": {
                            "value": {
                                "type": "string",
                                "x-mcp-header": name,
                            },
                        },
                    },
                )
        for kind in ("number", "array", "object", ["string", "null"], None):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                compile_header_bindings(
                    {
                        "properties": {
                            "value": {
                                "type": kind,
                                "x-mcp-header": "Value",
                            },
                        },
                    },
                )

    def test_optional_missing_null_and_extra_recognized_headers(self):
        """Omit absent or null values and reject injected recognized headers."""
        bindings = compile_header_bindings(
            {
                "properties": {
                    "value": {
                        "type": "string",
                        "x-mcp-header": "Value",
                    },
                },
            },
        )
        for arguments in ({}, {"value": None}):
            request = self.request(name="weather", arguments=arguments)
            validate_headers(self.headers(), request, bindings=bindings)
            self.assertMismatch(
                self.headers(extra=(("mcp-param-value", "injected"),)),
                request,
                bindings,
            )
        request = self.request(name="weather", arguments={"value": "real"})
        self.assertMismatch(self.headers(), request, bindings)
        self.assertMismatch(
            self.headers(
                extra=(
                    ("mcp-param-value", "real"),
                    ("MCP-PARAM-VALUE", "real"),
                ),
            ),
            request,
            bindings,
        )

    def test_parameter_string_boolean_and_numeric_comparisons(self):
        """Require strict primitive kinds while comparing integers numerically."""
        cases = (
            ("string", "Hello 世界", self.encoded("Hello 世界")),
            ("boolean", True, "true"),
            ("boolean", False, "false"),
            ("integer", 42, "42.0"),
            ("integer", 42.0, "4.2e1"),
            ("integer", -9007199254740991, "-9007199254740991"),
        )
        for kind, value, header in cases:
            bindings = compile_header_bindings(
                {
                    "properties": {
                        "value": {
                            "type": kind,
                            "x-mcp-header": "Value",
                        },
                    },
                },
            )
            request = self.request(name="weather", arguments={"value": value})
            validate_headers(
                self.headers(extra=(("mcp-param-value", header),)),
                request,
                bindings=bindings,
            )

    def test_parameter_type_range_and_header_disagreement_are_rejected(self):
        """Reject coercion, unsafe integers and values different from the body."""
        cases = (
            ("boolean", 1, "true"),
            ("boolean", True, "True"),
            ("integer", True, "1"),
            ("integer", "42", "42"),
            ("integer", 42.5, "42.5"),
            ("integer", 9007199254740992, "9007199254740992"),
            ("integer", 42, "NaN"),
            ("integer", 42, "1e9999999999999999999999999999999999"),
            ("integer", 42, "43"),
            ("string", 42, "42"),
            ("string", "real", "fake"),
        )
        for kind, value, header in cases:
            bindings = compile_header_bindings(
                {
                    "properties": {
                        "value": {
                            "type": kind,
                            "x-mcp-header": "Value",
                        },
                    },
                },
            )
            request = self.request(name="weather", arguments={"value": value})
            self.assertMismatch(
                self.headers(extra=(("mcp-param-value", header),)), request, bindings,
            )

    def test_notification_headers_are_not_request_metadata(self):
        """The revision does not prescribe request metadata for notification POSTs."""
        notification = decode_envelope(
            b'{"jsonrpc":"2.0","method":"notifications/cancelled"}',
        )
        validate_headers(Headers([]), notification)
