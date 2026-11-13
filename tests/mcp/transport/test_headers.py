# ruff: noqa: ANN001, ANN201, PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
import base64
import msgspec
from orionis.http.payload.estructures.headers import Headers
from orionis.mcp.exceptions import McpProtocolException
from orionis.mcp.protocol.codecs import decode_envelope, decode_params
from orionis.mcp.protocol.constants import CLIENT_CAPABILITIES, PROTOCOL_VERSION
from orionis.mcp.transport.headers import compile_header_bindings, validate_headers
from orionis.test import TestCase


class TestHeaders(TestCase):
    """Cover header ambiguity, encoded names and compiled parameter extraction."""

    def request(self, method="tools/call", **params: object):
        """Create protocol bytes with mandatory metadata and an explicit request ID.

        Parameters
        ----------
        method : object
            Value supplied for ``method``.
        **params : object
            Value supplied for ``params``.

        Returns
        -------
        object
            Return the result produced by ``request``.
        """
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
        """Preserve original pairs so duplicate headers reach validation.

        Parameters
        ----------
        method : object
            Value supplied for ``method``.
        name : object
            Value supplied for ``name``.
        extra : object
            Value supplied for ``extra``.

        Returns
        -------
        Headers
            Return the result produced by ``headers``.
        """
        return Headers(
            [
                ("MCP-Protocol-Version", "2026-07-28"),
                ("Mcp-Method", method),
                *((("Mcp-Name", name),) if name is not None else ()),
                *extra,
            ],
        )

    def encoded(self, value):
        """Construct the specification's case-sensitive UTF-8 sentinel.

        Parameters
        ----------
        value : object
            Value supplied for ``value``.

        Returns
        -------
        object
            Return the result produced by ``encoded``.
        """
        return "=?base64?" + base64.b64encode(value.encode()).decode() + "?="

    def assertMismatch(self, headers, request, bindings=()):
        """Check the exact JSON-RPC and HTTP header-validation error pair.

        Parameters
        ----------
        headers : object
            Value supplied for ``headers``.
        request : object
            Value supplied for ``request``.
        bindings : object
            Value supplied for ``bindings``.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        with self.assertRaises(McpProtocolException) as caught:
            validate_headers(headers, request, bindings=bindings)
        self.assertEqual(
            (caught.exception.code, caught.exception.status),
            (-32020, 400),
        )

    def testStandardHeadersMatchTypedAndRawParameters(self):
        """Known typed params and unknown raw methods share the same header gate.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        for method, params, name in (
            ("tools/call", {"name": "weather"}, "weather"),
            ("prompts/get", {"name": "weather"}, "weather"),
            ("resources/read", {"uri": "file:///weather"}, "file:///weather"),
            ("server/discover", {}, None),
        ):
            request = self.request(method, **params)
            validate_headers(
                self.headers(method, name),
                request,
                decode_params(request),
            )
            validate_headers(self.headers(method, name), request)
        request = self.request("unknown")
        validate_headers(self.headers("unknown", None), request)
        with self.assertRaises(McpProtocolException) as caught:
            decode_params(request)
        self.assertEqual(caught.exception.status, 404)

    def testRequiredMismatchAndDuplicateHeaders(self):
        """Reject missing metadata and disagreeing or repeated singleton headers.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        request = self.request(name="weather")
        pairs = list(self.headers())
        for index in range(len(pairs)):
            self.assertMismatch(Headers(pairs[:index] + pairs[index + 1 :]), request)
            changed = list(pairs)
            changed[index] = (pairs[index][0], "different")
            self.assertMismatch(Headers(changed), request)
            self.assertMismatch(
                Headers([*pairs, (pairs[index][0].upper(), pairs[index][1])]),
                request,
            )

    def testHeaderNameCaseAndValueCaseAreDistinct(self):
        """Normalize field names without case folding method or name values.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        request = self.request(name="weather")
        validate_headers(
            Headers([(key.swapcase(), value) for key, value in self.headers()]),
            request,
        )
        self.assertMismatch(self.headers(name="WEATHER"), request)
        self.assertMismatch(self.headers(method="TOOLS/CALL"), request)

    def testLegacyMissingHeadersFailBeforeUnknownMethod(self):
        """A header-less initialize receives the modern header validation error.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        request = decode_envelope(b'{"jsonrpc":"2.0","id":1,"method":"initialize"}')
        self.assertMismatch(Headers([]), request)

    def testMissingBodyMetadataIsInvalidParamsWhenHeadersExist(self):
        """Honor the official stateless conformance error classification.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        for params in ({}, {"_meta": {}}, {"_meta": {PROTOCOL_VERSION: None}}):
            request = decode_envelope(
                msgspec.json.encode(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "server/discover",
                        "params": params,
                    },
                ),
            )
            with self.assertRaises(McpProtocolException) as caught:  # NOSONAR
                validate_headers(self.headers("server/discover", None), request)
            self.assertEqual(caught.exception.code, -32602)

    def testUnsupportedMatchingVersionIsLeftToProtocol(self):
        """Do not misclassify a matching unsupported version as a header mismatch.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
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

    def testUnicodeWhitespaceAndSentinelNameEncoding(self):
        """Decode UTF-8 names and literals that would otherwise resemble sentinels.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        for name in ("Café 世界", " padded ", "line1\nline2", "=?base64?literal?="):
            request = self.request(name=name)
            validate_headers(self.headers(name=self.encoded(name)), request)
            self.assertMismatch(self.headers(name=name), request)

    def testMalformedEncodedValuesAndUnsafeRawValues(self):
        """Reject invalid Base64, invalid UTF-8, controls and outer whitespace.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
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

    def testStaticNestedPathsAreCompiledWithoutDottedKeyExpansion(self):
        """Nested properties and literal dotted properties resolve independently.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
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

    def testSchemaRejectsUnreachableAnnotationsAndDuplicateNames(self):
        """Fail malformed catalog metadata at compilation rather than first call.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
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

    def testSchemaRejectsInvalidNamesAndNonprimitiveTypes(self):
        """Token syntax and primitive restrictions cover CRLF and nullable unions.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
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

    def testOptionalMissingNullAndExtraRecognizedHeaders(self):
        """Omit absent or null values and reject injected recognized headers.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
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

    def testParameterStringBooleanAndNumericComparisons(self):
        """Require strict primitive kinds while comparing integers numerically.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
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

    def testParameterTypeRangeAndHeaderDisagreementAreRejected(self):
        """Reject coercion, unsafe integers and values different from the body.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
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
                self.headers(extra=(("mcp-param-value", header),)),
                request,
                bindings,
            )

    def testNotificationHeadersAreNotRequestMetadata(self):
        """The revision does not prescribe request metadata for notification POSTs.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        notification = decode_envelope(
            b'{"jsonrpc":"2.0","method":"notifications/cancelled"}',
        )
        validate_headers(Headers([]), notification)
