# ruff: noqa: ANN001, ANN201, PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
import msgspec

from orionis.mcp.context import McpRequest
from orionis.mcp.exceptions import McpInvalidParams, McpProtocolException
from orionis.mcp.protocol.codecs import decode_envelope, decode_params
from orionis.mcp.protocol.constants import CLIENT_CAPABILITIES, PROTOCOL_VERSION
from orionis.mcp.protocol.content import (
    Annotations,
    ImageContent,
    TextContent,
    TextResourceContents,
)
from orionis.mcp.protocol.metavalidation import validate_metadata
from orionis.mcp.protocol.mrtr import validate_input_required, validate_input_responses
from orionis.mcp.protocol.results import (
    CallToolResult,
    CompleteCompletionResult,
    CompleteResult,
    Completion,
    GetPromptResult,
    InputRequiredResult,
    ReadResourceResult,
)
from orionis.mcp.protocol.validation import validate_result
from orionis.test import TestCase


class TestMetadata(TestCase):
    """Check native request decoders preserve extensibility with strict known fields."""

    def decode(self, capabilities, **meta: object):
        """Decode real bytes through the production protocol entry point.

        Parameters
        ----------
        capabilities : object
            Value supplied for ``capabilities``.
        **meta : object
            Value supplied for ``meta``.

        Returns
        -------
        object
            Return the result produced by ``decode``.
        """
        return decode_params(
            decode_envelope(
                msgspec.json.encode(
                    {
                        "jsonrpc": "2.0",
                        "method": "server/discover",
                        "id": 1,
                        "params": {
                            "_meta": {
                                PROTOCOL_VERSION: "2026-07-28",
                                CLIENT_CAPABILITIES: capabilities,
                                **meta,
                            },
                        },
                    },
                ),
            ),
        )

    def testNestedCapabilitiesAndClientInformation(self):
        """Reject malformed known settings without closing unknown capability names.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        for capabilities in (
            {"elicitation": {"form": True}},
            {"sampling": {"tools": []}},
            {"extensions": {"unnamespaced": {}}},
            {"roots": None},
        ):
            with (
                self.subTest(capabilities=capabilities),
                self.assertRaises(
                    McpInvalidParams,
                ),
            ):
                self.decode(capabilities)
        self.decode({"example": "open", "extensions": {"org.example/ui": {}}})
        with self.assertRaises(McpInvalidParams):
            self.decode(
                {},
                **{
                    "io.modelcontextprotocol/clientInfo": {
                        "name": "client",
                        "version": "1",
                        "icons": [{"src": "file:///x"}],
                    },
                },
            )

    def testMetadataNamesReservedPolicyAndValidTraceContext(self):
        """Accept namespaced metadata and the documented OpenTelemetry conventions.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        metadata = {
            "traceparent": "00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01",
            "tracestate": "vendor=value,other=second",
            "baggage": "user=alice;secure,region=us%20west",
            "org.example/widget": {"open": True},
        }
        self.decode({}, **metadata)
        with self.assertRaises(ValueError):
            validate_metadata(
                {"io.modelcontextprotocol/serverInfo": {}},
                allow_reserved=False,
            )
        for bad in ("bad key", "9example/abc", "org.example/-bad", "extra/slash/key"):
            with self.subTest(key=bad), self.assertRaises(McpInvalidParams):
                self.decode({}, **{bad: 1})

    def testInvalidTraceContext(self):
        """Reject malformed and zero trace IDs or duplicate tracestate vendors.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        for meta in (
            {"traceparent": "00-" + "0" * 32 + "-" + "1" * 16 + "-01"},
            {"traceparent": "ff-" + "1" * 32 + "-" + "1" * 16 + "-01"},
            {"tracestate": "vendor=x,vendor=y"},
            {"baggage": "bad key=value"},
            {"traceparent": 4},
        ):
            with self.subTest(meta=meta), self.assertRaises(McpInvalidParams):
                self.decode({}, **meta)


class TestOutputValidation(TestCase):
    """A typed Struct constructor must not bypass protocol validation."""

    def testResultMetadataRejectsNonfiniteValuesInsteadOfEncodingNull(self) -> None:
        """Apply finite JSON checks to direct result metadata before serialization.

        Returns
        -------
        None
            No return value.
        """
        for value in (float("nan"), float("inf"), float("-inf")):
            for result, method in (
                (CallToolResult(content=()), "tools/call"),
                (ReadResourceResult(contents=()), "resources/read"),
                (CompleteResult(), "subscriptions/listen"),
            ):
                with self.subTest(value=value, method=method):
                    invalid = msgspec.structs.replace(
                        result,
                        meta={"example.org/value": {"nested": [value]}},
                    )
                    with self.assertRaisesRegex(ValueError, "finite JSON"):
                        validate_result(invalid, method)

    def testValidContentVariantsAndExplicitNull(self):
        """Preserve valid embedded resources, prompt messages, and JSON null output.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        content = (
            TextContent(text="ok"),
            ImageContent(data="YQ==", mimeType="image/png"),
            {"type": "resource", "resource": {"uri": "test:one", "blob": "YQ=="}},
            {"type": "resource_link", "name": "one", "uri": "test:one"},
            {"type": "audio", "data": "YQ==", "mimeType": "audio/wav"},
        )
        validate_result(
            CallToolResult(content=content, structuredContent=None),
            "tools/call",
        )
        validate_result(
            GetPromptResult(
                messages=(
                    {
                        "role": "assistant",
                        "content": content[0],
                    },
                ),
            ),
            "prompts/get",
        )
        validate_result(
            ReadResourceResult(
                contents=(TextResourceContents(uri="test:one", text="ok"),),
            ),
            "resources/read",
        )

    def testInvalidDirectStructValues(self):
        """Reject malformed content before the final JSON writer can serialize it.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        invalid = (
            TextContent(text=42),
            ImageContent(data="not base64!", mimeType="image/png"),
            TextContent(text="ok", annotations=Annotations(priority=2)),
            {"type": "unknown", "text": "ok"},
            {"type": "resource", "resource": {"uri": "relative", "text": "x"}},
            {"type": "resource_link", "name": "x", "uri": "test:x", "size": -1},
        )
        for content in invalid:
            with (  # NOSONAR
                self.subTest(content=content),
                self.assertRaises((ValueError, TypeError)),
            ):
                validate_result(CallToolResult(content=(content,)), "tools/call")

    def testResultTagsMethodRolesAndCacheHints(self):
        """Enforce the result discriminator and the requested result family.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        cases = (
            (CallToolResult(content=(), resultType="unknown"), "tools/call"),
            (CallToolResult(content=()), "resources/read"),
            (ReadResourceResult(contents=(), ttlMs=-1), "resources/read"),
            (ReadResourceResult(contents=(), ttlMs=True), "resources/read"),
            (
                GetPromptResult(
                    messages=(
                        {
                            "role": "system",
                            "content": {
                                "type": "text",
                                "text": "x",
                            },
                        },
                    ),
                ),
                "prompts/get",
            ),
            (CallToolResult(content=(), structuredContent=float("nan")), "tools/call"),
            (
                CompleteCompletionResult(completion=Completion(values=("x",) * 101)),
                "completion/complete",
            ),
        )
        for result, method in cases:
            with (
                self.subTest(result=result),
                self.assertRaises((TypeError, ValueError)),
            ):
                validate_result(result, method)
        validate_result(CompleteResult(), "subscriptions/listen")


class TestMultiRoundTrip(TestCase):
    """Exercise explicit MRTR request and response forms, including wire-only legacy."""

    def request(self, capabilities=None, method="tools/call"):
        """Represent one independent modern request.

        Parameters
        ----------
        capabilities : object
            Value supplied for ``capabilities``.
        method : object
            Value supplied for ``method``.

        Returns
        -------
        McpRequest
            Return the result produced by ``request``.
        """
        return McpRequest(
            id=1,
            method=method,
            meta={
                CLIENT_CAPABILITIES: capabilities or {},
            },
        )

    def result(self, method, params=msgspec.UNSET):
        """Build an embedded request without a JSON-RPC ID or envelope.

        Parameters
        ----------
        method : object
            Value supplied for ``method``.
        params : object
            Value supplied for ``params``.

        Returns
        -------
        InputRequiredResult
            Return the result produced by ``result``.
        """
        item = {"method": method}
        if params is not msgspec.UNSET:
            item["params"] = params
        return InputRequiredResult(inputRequests={"question": item})

    def testRequiresDeclaredCapabilityAndEligibleMethod(self):
        """Form support is evaluated against this call's capabilities only.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        result = self.result(
            "elicitation/create",
            {
                "message": "Name?",
                "requestedSchema": {"type": "object", "properties": {}},
            },
        )
        with self.assertRaises(McpProtocolException) as caught:  # NOSONAR
            validate_input_required(result, self.request())
        self.assertEqual(caught.exception.code, -32021)
        validate_input_required(result, self.request({"elicitation": {}}))
        with self.assertRaises(McpInvalidParams):  # NOSONAR
            validate_input_required(
                result,
                self.request({"elicitation": {}}, "tools/list"),
            )
        with self.assertRaises(McpInvalidParams):  # NOSONAR
            validate_input_required(InputRequiredResult(), self.request())

    def testFormSchemasRejectNestingAndInvalidEnumerations(self):
        """Only the protocol's primitive and string enum form fields are allowed.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        for field in (
            {"type": "object", "properties": {}},
            {"type": "array", "items": {"type": "integer"}},
            {"type": "string", "minLength": -1},
            {"type": "boolean", "default": "true"},
        ):
            with (
                self.subTest(field=field),
                self.assertRaises(McpInvalidParams),
            ):  # NOSONAR
                validate_input_required(
                    self.result(
                        "elicitation/create",
                        {
                            "message": "Question?",
                            "requestedSchema": {
                                "type": "object",
                                "properties": {"answer": field},
                            },
                        },
                    ),
                    self.request({"elicitation": {}}),
                )
        validate_input_required(
            self.result(
                "elicitation/create",
                {
                    "message": "Colors?",
                    "requestedSchema": {
                        "type": "object",
                        "properties": {
                            "colors": {
                                "type": "array",
                                "items": {"type": "string", "enum": ["red"]},
                            },
                        },
                    },
                },
            ),
            self.request({"elicitation": {"form": {}}}),
        )

    def testWireOnlyRootsAndSampling(self):
        """Support correct embedded shapes without introducing old session APIs.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        validate_input_required(self.result("roots/list"), self.request({"roots": {}}))
        sampling = {
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": "Hello",
                    },
                },
            ],
            "maxTokens": 10,
            "tools": [],
        }
        with self.assertRaises(McpProtocolException):  # NOSONAR
            validate_input_required(
                self.result("sampling/createMessage", sampling),
                self.request({"sampling": {}}),
            )
        validate_input_required(
            self.result("sampling/createMessage", sampling),
            self.request({"sampling": {"tools": {}}}),
        )

    def testExactClientInputResponseUnion(self):
        """Accept explicit result variants and reject errors or nested form values.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        validate_input_responses(
            {
                "form": {"action": "accept", "content": {"colors": ["red"], "age": 20}},
                "url": {"action": "accept"},
                "roots": {"roots": [{"uri": "file:///workspace"}]},
                "sample": {
                    "role": "assistant",
                    "model": "example",
                    "content": {
                        "type": "text",
                        "text": "Hello",
                    },
                },
            },
        )
        for value in (
            {"error": {"code": -1, "message": "failure"}},
            {},
            {"action": "accept", "content": {"nested": {}}},
            {"action": "decline", "content": {}},
            {"roots": [{"uri": "https://example.com"}]},
            {"model": "example", "role": "system", "content": {}},
        ):
            with self.subTest(value=value), self.assertRaises(McpInvalidParams):
                validate_input_responses({"key": value})
