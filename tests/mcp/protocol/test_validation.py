"""Validate wire invariants at both untrusted-input and application-output edges."""

import unittest

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


class TestMetadata(unittest.TestCase):
    """Check native request decoders preserve extensibility with strict known fields."""

    def decode(self, capabilities, **meta: object):
        """Decode real bytes through the production protocol entry point."""
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

    def test_nested_capabilities_and_client_information(self):
        """Reject malformed known settings without closing unknown capability names."""
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

    def test_metadata_names_reserved_policy_and_valid_trace_context(self):
        """Accept namespaced metadata and the documented OpenTelemetry conventions."""
        metadata = {
            "traceparent": "00-0af7651916cd43dd8448eb211c80319c-00f067aa0ba902b7-01",
            "tracestate": "vendor=value,other=second",
            "baggage": "user=alice;secure,region=us%20west",
            "org.example/widget": {"open": True},
        }
        self.decode({}, **metadata)
        with self.assertRaises(ValueError):
            validate_metadata(
                {"io.modelcontextprotocol/serverInfo": {}}, allow_reserved=False,
            )
        for bad in ("bad key", "9example/abc", "org.example/-bad", "extra/slash/key"):
            with self.subTest(key=bad), self.assertRaises(McpInvalidParams):
                self.decode({}, **{bad: 1})

    def test_invalid_trace_context(self):
        """Reject malformed and zero trace IDs or duplicate tracestate vendors."""
        for meta in (
            {"traceparent": "00-" + "0" * 32 + "-" + "1" * 16 + "-01"},
            {"traceparent": "ff-" + "1" * 32 + "-" + "1" * 16 + "-01"},
            {"tracestate": "vendor=x,vendor=y"},
            {"baggage": "bad key=value"},
            {"traceparent": 4},
        ):
            with self.subTest(meta=meta), self.assertRaises(McpInvalidParams):
                self.decode({}, **meta)


class TestOutputValidation(unittest.TestCase):
    """A typed Struct constructor must not bypass protocol validation."""

    def test_valid_content_variants_and_explicit_null(self):
        """Preserve valid embedded resources, prompt messages, and JSON null output."""
        content = (
            TextContent(text="ok"),
            ImageContent(data="YQ==", mimeType="image/png"),
            {"type": "resource", "resource": {"uri": "test:one", "blob": "YQ=="}},
            {"type": "resource_link", "name": "one", "uri": "test:one"},
            {"type": "audio", "data": "YQ==", "mimeType": "audio/wav"},
        )
        validate_result(
            CallToolResult(content=content, structuredContent=None), "tools/call",
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

    def test_invalid_direct_struct_values(self):
        """Reject malformed content before the final JSON writer can serialize it."""
        invalid = (
            TextContent(text=42),
            ImageContent(data="not base64!", mimeType="image/png"),
            TextContent(text="ok", annotations=Annotations(priority=2)),
            {"type": "unknown", "text": "ok"},
            {"type": "resource", "resource": {"uri": "relative", "text": "x"}},
            {"type": "resource_link", "name": "x", "uri": "test:x", "size": -1},
        )
        for content in invalid:
            with (
                self.subTest(content=content),
                self.assertRaises((ValueError, TypeError)),
            ):
                validate_result(CallToolResult(content=(content,)), "tools/call")

    def test_result_tags_method_roles_and_cache_hints(self):
        """Enforce the result discriminator and the requested result family."""
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


class TestMultiRoundTrip(unittest.TestCase):
    """Exercise explicit MRTR request and response forms, including wire-only legacy."""

    def request(self, capabilities=None, method="tools/call"):
        """Represent one independent modern request."""
        return McpRequest(
            id=1,
            method=method,
            meta={
                CLIENT_CAPABILITIES: capabilities or {},
            },
        )

    def result(self, method, params=msgspec.UNSET):
        """Build an embedded request without a JSON-RPC ID or envelope."""
        item = {"method": method}
        if params is not msgspec.UNSET:
            item["params"] = params
        return InputRequiredResult(inputRequests={"question": item})

    def test_requires_declared_capability_and_eligible_method(self):
        """Form support is evaluated against this call's capabilities only."""
        result = self.result(
            "elicitation/create",
            {
                "message": "Name?",
                "requestedSchema": {"type": "object", "properties": {}},
            },
        )
        with self.assertRaises(McpProtocolException) as caught:
            validate_input_required(result, self.request())
        self.assertEqual(caught.exception.code, -32021)
        validate_input_required(result, self.request({"elicitation": {}}))
        with self.assertRaises(McpInvalidParams):
            validate_input_required(
                result, self.request({"elicitation": {}}, "tools/list"),
            )
        with self.assertRaises(McpInvalidParams):
            validate_input_required(InputRequiredResult(), self.request())

    def test_form_schemas_reject_nesting_and_invalid_enumerations(self):
        """Only the protocol's primitive and string enum form fields are allowed."""
        for field in (
            {"type": "object", "properties": {}},
            {"type": "array", "items": {"type": "integer"}},
            {"type": "string", "minLength": -1},
            {"type": "boolean", "default": "true"},
        ):
            with self.subTest(field=field), self.assertRaises(McpInvalidParams):
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

    def test_wire_only_roots_and_sampling(self):
        """Support correct embedded shapes without introducing old session APIs."""
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
        with self.assertRaises(McpProtocolException):
            validate_input_required(
                self.result("sampling/createMessage", sampling),
                self.request({"sampling": {}}),
            )
        validate_input_required(
            self.result("sampling/createMessage", sampling),
            self.request({"sampling": {"tools": {}}}),
        )

    def test_exact_client_input_response_union(self):
        """Accept explicit result variants and reject errors or nested form values."""
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
