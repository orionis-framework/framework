import msgspec
from orionis.mcp.protocol.metadata import ContentAnnotations
from orionis.mcp.protocol.results import CallToolResult
from orionis.mcp.responses import McpResponse
from orionis.test import TestCase

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
