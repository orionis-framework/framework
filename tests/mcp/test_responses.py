import base64
import msgspec
from orionis.container.container import Container
from orionis.mcp.protocol.metadata import ContentAnnotations
from orionis.mcp.protocol.metadata import PromptArgument
from orionis.mcp.protocol.results import CallToolResult
from orionis.mcp.responses import McpResponse
from orionis.mcp.server.primitives import Prompt, Resource, Server, Tool
from orionis.schemas import Schema
from orionis.test import TestCase

_SERIALIZED_DATA = {"name": "Caf\u00e9", "values": [1, None, False]}

class _SerializationInput(Schema):
    mime_type: str

class _SerializationTool(Tool[_SerializationInput]):
    name = "serialized-data"

    def handle(self, payload: _SerializationInput) -> McpResponse:
        """Return application data without serializing it in the handler.

        Parameters
        ----------
        payload : _SerializationInput
            MIME type selected by the test client.

        Returns
        -------
        McpResponse
            Resource content encoded by the shared response builder.
        """
        return McpResponse.resource(
            "demo://serialized", _SERIALIZED_DATA, payload.mime_type,
        )

class _SerializationPrompt(Prompt):
    name = "serialized-data"
    arguments = (PromptArgument(name="mime_type", required=True),)

    def handle(self, mime_type: str) -> McpResponse:
        """Return application data in an assistant prompt message.

        Parameters
        ----------
        mime_type : str
            MIME type selected by the test client.

        Returns
        -------
        McpResponse
            Resource content encoded by the shared response builder.
        """
        return McpResponse.resource(
            "demo://serialized", _SERIALIZED_DATA, mime_type,
        ).asAssistant()

class _SerializationResource(Resource):
    uri = "demo://serialized/json"
    mime_type = "application/json"

    def handle(self) -> McpResponse:
        """Return application data using the resource's declared MIME type.

        Returns
        -------
        McpResponse
            Resource content encoded by the shared response builder.
        """
        return McpResponse.structured(_SERIALIZED_DATA)

class _MessagePackResource(_SerializationResource):
    uri = "demo://serialized/msgpack"
    mime_type = "application/msgpack"

class _ScalarSerializationResource(_SerializationResource):
    uri = "demo://scalar/json"

    def handle(self) -> McpResponse:
        """Return a JSON scalar for serialization under the declared MIME type.

        Returns
        -------
        McpResponse
            A string value, not a pre-encoded JSON or MessagePack payload.
        """
        return McpResponse.structured("Caf\u00e9")

class _ScalarMessagePackResource(_ScalarSerializationResource):
    uri = "demo://scalar/msgpack"
    mime_type = "application/msgpack"

class _TextMessagePackResource(_MessagePackResource):
    uri = "demo://text/msgpack"

    def handle(self) -> McpResponse:
        """Return text using binary framing selected by the resource MIME type.

        Returns
        -------
        McpResponse
            Text which the normalizer serializes as a MessagePack string.
        """
        return McpResponse.text("Caf\u00e9")

class _SerializationServer(Server):
    name = "MIME serialization"
    tools = (_SerializationTool,)
    resources = (
        _SerializationResource, _MessagePackResource,
        _ScalarSerializationResource, _ScalarMessagePackResource,
        _TextMessagePackResource,
    )
    prompts = (_SerializationPrompt,)

class TestResponses(TestCase):
    """Preserve JSON scalar/null values and base64 binary contents."""

    def test_structured_json_values(self):
        """Arrays, scalars and null are valid modern structured content.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        for value in (None, False, 0, [], {}, "ok", [1, 2]):
            response = McpResponse.structured(value)
            wire = msgspec.json.decode(
                msgspec.json.encode(
                    CallToolResult(
                        content=response.content,
                        structuredContent=response.structured_content,
                    ),
                ),
            )
            self.assertEqual(wire["structuredContent"], value)
            self.assertEqual(msgspec.json.decode(wire["content"][0]["text"]), value)
            self.assertEqual(wire["resultType"], "complete")

    def test_content_factories(self):
        """Images, audio and blobs use protocol-defined shapes.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        responses = (
            McpResponse.image(b"abc", "image/png"),
            McpResponse.audio(b"abc", "audio/wav"),
            McpResponse.resource("docs://one", b"abc", "application/octet-stream"),
            McpResponse.resourceLink("docs://one", "one"),
        )
        values = [
            msgspec.json.decode(msgspec.json.encode(item.content[0]))
            for item in responses
        ]
        self.assertEqual(
            [item["type"] for item in values],
            ["image", "audio", "resource", "resource_link"],
        )
        self.assertEqual(values[0]["data"], "YWJj")
        self.assertEqual(values[2]["resource"]["blob"], "YWJj")

    def test_progress_rejects_nonfinite_values(self):
        """Do not emit NaN as an invalid JSON number.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        with self.assertRaises(ValueError):
            McpResponse.progress(float("nan"))

    def test_metadata_and_annotations(self):
        """Keep result and content metadata separate while preserving hints.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        response = (
            McpResponse.text("example")
            .withMeta({"example.com/result": True})
            .withContentMeta({"example.com/content": "note"})
            .withAnnotations(ContentAnnotations(audience=("assistant",), priority=0.5))
        )
        self.assertEqual(response.meta, {"example.com/result": True})
        value = msgspec.json.decode(msgspec.json.encode(response.content[0]))
        self.assertEqual(value["_meta"], {"example.com/content": "note"})
        self.assertEqual(value["annotations"]["priority"], 0.5)
        for factory in (response.withMeta, response.withContentMeta):
            with self.assertRaises(ValueError):
                factory({"io.modelcontextprotocol/serverInfo": {"name": "forged"}})

    def test_structured_rejects_values_that_json_would_coerce(self):
        """Never silently turn NaN into null or serialize arbitrary Python objects.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        for value in (float("nan"), float("inf"), {1: "key"}, b"binary"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                McpResponse.structured(value)

    def testJsonResourcesSerializeStructuredData(self) -> None:
        """Encode application mappings using JSON MIME types.

        Validates native encoding, declared MIME preservation and text framing.
        """
        payload = {"name": "Caf\u00e9", "values": [1, None, False]}
        for mime_type in (
            "application/json", "application/schema+json",
            "Application/JSON; charset=UTF-8",
        ):
            with self.subTest(mime_type=mime_type):
                response = McpResponse.resource("docs://schema", payload, mime_type)
                contents = msgspec.to_builtins(response.content[0])["resource"]
                self.assertEqual(contents["uri"], "docs://schema")
                self.assertEqual(contents["mimeType"], mime_type)
                self.assertEqual(msgspec.json.decode(contents["text"]), payload)
                self.assertNotIn("blob", contents)

    def testMessagePackResourcesSerializeStructuredData(self) -> None:
        """Encode application mappings using MessagePack MIME types.

        Validates lossless binary data and protocol-defined Base64 framing.
        """
        payload = {"name": "Caf\u00e9", "binary": b"\x00\xff", "values": [None, 1]}
        for mime_type in (
            "application/msgpack", "application/x-msgpack",
            "application/vnd.msgpack", "application/example+msgpack",
            "Application/X-MsgPack; version=1",
        ):
            with self.subTest(mime_type=mime_type):
                response = McpResponse.resource("docs://schema", payload, mime_type)
                contents = msgspec.to_builtins(response.content[0])["resource"]
                self.assertEqual(contents["uri"], "docs://schema")
                self.assertEqual(contents["mimeType"], mime_type)
                encoded = base64.b64decode(contents["blob"], validate=True)
                self.assertEqual(msgspec.msgpack.decode(encoded), payload)
                self.assertNotIn("text", contents)

    def testResourcesInferJsonForStructuredValues(self) -> None:
        """Infer JSON for application values without an explicit MIME type.

        Validates arrays, null, booleans and finite scalar content.
        """
        for payload in (None, False, 0, 1.5, [], {}, (1, 2)):
            with self.subTest(payload=payload):
                response = McpResponse.resource("docs://value", payload)
                contents = msgspec.to_builtins(response.content[0])["resource"]
                self.assertEqual(contents["mimeType"], "application/json")
                expected = McpResponse.structured(payload).structured_content
                self.assertEqual(msgspec.json.decode(contents["text"]), expected)

    def testResourcesPreserveEncodedContent(self) -> None:
        """Keep text and binary buffers compatible with existing callers.

        Validates that pre-encoded JSON and MessagePack are not encoded twice.
        """
        text = msgspec.json.encode(_SERIALIZED_DATA).decode("utf-8")
        response = McpResponse.resource("docs://value", text, "application/json")
        self.assertEqual(response.content[0].resource.text, text)
        binary = msgspec.msgpack.encode(_SERIALIZED_DATA)
        for payload in (binary, bytearray(binary), memoryview(binary)):
            with self.subTest(payload_type=type(payload).__name__):
                response = McpResponse.resource(
                    "docs://value", payload, "application/msgpack",
                )
                contents = msgspec.to_builtins(response.content[0])["resource"]
                encoded = base64.b64decode(contents["blob"], validate=True)
                self.assertEqual(encoded, binary)
        plain = McpResponse.resource("docs://value", "plain text")
        contents = msgspec.to_builtins(plain.content[0])["resource"]
        self.assertEqual(contents["text"], "plain text")
        self.assertNotIn("mimeType", contents)

    def testMessagePackResourcesSerializeScalarValues(self) -> None:
        """Serialize string and scalar values as binary MessagePack content.

        Validates that a MessagePack MIME type always selects binary framing.
        """
        for payload in (None, False, 0, "Caf\u00e9", [1, None]):
            with self.subTest(payload=payload):
                response = McpResponse.resource(
                    "docs://value", payload, "application/msgpack",
                )
                contents = msgspec.to_builtins(response.content[0])["resource"]
                encoded = base64.b64decode(contents["blob"], validate=True)
                self.assertEqual(msgspec.msgpack.decode(encoded), payload)
                self.assertNotIn("text", contents)

    def testJsonResourceValidationMatchesStructuredResponses(self) -> None:
        """Apply the same strict JSON validation to resources and tool output.

        Validates that nonfinite numbers and non-JSON nested data are rejected.
        """
        for payload in (
            float("nan"), float("inf"), {1: "key"}, {"binary": b"data"}, object(),
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    McpResponse.structured(payload)
                with self.assertRaises(ValueError):
                    McpResponse.resource("docs://value", payload, "application/json")

    def testResourcesRejectUnregisteredStructuredMimeTypes(self) -> None:
        """Do not silently stringify data for formats without a codec.

        Validates eager rejection while preserving already encoded content.
        """
        for mime_type in ("text/plain", "application/xml", "application/octet-stream"):
            with self.subTest(mime_type=mime_type):
                with self.assertRaises(ValueError):
                    McpResponse.resource("docs://value", {"value": 1}, mime_type)
                response = McpResponse.resource("docs://value", "encoded", mime_type)
                self.assertEqual(response.content[0].resource.text, "encoded")

    def testResourceSerializationCapturesIndependentSnapshots(self) -> None:
        """Serialize a stable snapshot without changing application data.

        Validates that later mutations do not alter existing response content.
        """
        payload = {"values": [1, None]}
        json_response = McpResponse.resource(
            "docs://value", payload, "application/json",
        )
        packed_response = McpResponse.resource(
            "docs://value", payload, "application/msgpack",
        )
        self.assertEqual(payload, {"values": [1, None]})
        payload["values"].append(2)
        text = msgspec.to_builtins(json_response.content[0])["resource"]["text"]
        blob = msgspec.to_builtins(packed_response.content[0])["resource"]["blob"]
        self.assertEqual(msgspec.json.decode(text), {"values": [1, None]})
        encoded = base64.b64decode(blob, validate=True)
        self.assertEqual(msgspec.msgpack.decode(encoded), {"values": [1, None]})

    async def testMimeSerializationWorksAcrossPrimitives(self) -> None:
        """Dispatch identical encoded data through tools, resources and prompts.

        Validates actual native scopes, result schemas and JSON-RPC framing.
        """
        class _SerializationContainer(Container):
            pass

        client = await self.mcp(_SerializationServer, app=_SerializationContainer())
        for mime_type, uri in (
            ("application/json", "demo://serialized/json"),
            ("application/msgpack", "demo://serialized/msgpack"),
        ):
            with self.subTest(mime_type=mime_type):
                tool = await client.tool("serialized-data", {"mime_type": mime_type})
                resource = await client.request("resources/read", {"uri": uri})
                prompt = await client.request(
                    "prompts/get",
                    {"name": "serialized-data", "arguments": {"mime_type": mime_type}},
                )
                for response in (tool, resource, prompt):
                    response.assertOk()
                    self.assertEqual(response.message["jsonrpc"], "2.0")
                messages = prompt.message["result"]["messages"]
                self.assertEqual(messages[0]["role"], "assistant")
                contents = (
                    tool.message["result"]["content"][0]["resource"],
                    resource.message["result"]["contents"][0],
                    messages[0]["content"]["resource"],
                )
                for content in contents:
                    self.assertEqual(content["mimeType"], mime_type)
                    if mime_type == "application/json":
                        decoded = msgspec.json.decode(content["text"])
                    else:
                        encoded = base64.b64decode(content["blob"], validate=True)
                        decoded = msgspec.msgpack.decode(encoded)
                    self.assertEqual(decoded, _SERIALIZED_DATA)

    async def testResourcesApplyDeclaredMimeToScalarContent(self) -> None:
        """Apply declared resource MIME types without handler-side encoding.

        Validates scalar JSON, structured MessagePack and plain text conversion.
        """
        class _ScalarContainer(Container):
            pass

        client = await self.mcp(_SerializationServer, app=_ScalarContainer())
        for mime_type, uri in (
            ("application/json", "demo://scalar/json"),
            ("application/msgpack", "demo://scalar/msgpack"),
            ("application/msgpack", "demo://text/msgpack"),
        ):
            with self.subTest(uri=uri):
                response = await client.request("resources/read", {"uri": uri})
                response.assertOk()
                contents = response.message["result"]["contents"][0]
                self.assertEqual(contents["mimeType"], mime_type)
                if mime_type == "application/json":
                    decoded = msgspec.json.decode(contents["text"])
                else:
                    encoded = base64.b64decode(contents["blob"], validate=True)
                    decoded = msgspec.msgpack.decode(encoded)
                self.assertEqual(decoded, "Caf\u00e9")
