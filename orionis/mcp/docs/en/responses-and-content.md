# Content, serialization and metadata

`McpResponse` is an immutable transport-independent value. Builders create text, images, audio, embedded resources, links, structured data, tool errors or progress updates. `withMeta`, `withContentMeta`, `withAnnotations`, `asUser` and `asAssistant` return copies instead of mutating a shared response.

## Returning structured data

```python
from orionis.mcp import ContentAnnotations, McpResponse

result = (
    McpResponse.structured({"status": "ok", "count": 2})
    .withMeta({"example.org/trace": "docs"})
    .withContentMeta({"example.org/source": "catalog"})
    .withAnnotations(ContentAnnotations(audience=("assistant",), priority=0.8))
)
assert result.structured_content == {"status": "ok", "count": 2}
assert result.content[0].meta["example.org/source"] == "catalog"
```

`structured(value)` retains JSON `structuredContent` with corresponding text content. It normalizes `Schema`, `msgspec.Struct`, dataclasses, enums, dates, UUIDs and Decimal through msgspec, honoring aliases, tags and omitted defaults. The original value is unchanged. Nonfinite values, non-string JSON keys, unsupported objects and nested binary buffers are invalid JSON; use explicit binary representations instead.

## JSON and MessagePack resources

```python
import base64
import msgspec
from orionis.mcp import McpResponse

value = {"ready": True, "count": 2}
json_result = McpResponse.resource("demo://status", value, "application/json")
packed = McpResponse.resource("demo://status", value, "application/msgpack")
assert msgspec.json.decode(json_result.content[0].resource.text) == value
assert msgspec.msgpack.decode(base64.b64decode(packed.content[0].resource.blob)) == value
```

JSON and `+json` subtypes become UTF-8 text. MessagePack (`application/msgpack`, `application/x-msgpack`, `application/vnd.msgpack` and `+msgpack` subtypes) becomes a Base64 blob. MIME describes content: HTTP/STDIO envelopes remain JSON-RPC JSON. Other MIME types require already encoded text or bytes; arbitrary structured data is rejected.

Without MIME, structured data uses JSON. Previously encoded JSON text and suitable binary buffers are preserved without double encoding; strings with MessagePack MIME are encoded as MessagePack data. Codec selection ignores case/parameters while retaining the declared MIME.

Reading a `Resource` applies its `mime_type` to `structured()` and `text()` results. MessagePack resources convert the original value into binary rather than encoding a previously serialized JSON string. Explicit embedded resources retain their own content and MIME.

## Images, links and failures

`image(bytes, mime_type)` and `audio(bytes, mime_type)` represent binary content. `resourceLink(uri, name, title=..., description=..., mime_type=...)` publishes a reference without automatically reading it. `error(message)` describes an expected tool failure; keep secrets out. JSON-RPC errors, invalid parameters and denied access belong to dispatcher exceptions.

## Hints and safe metadata

`CacheHint(ttl_ms=..., scope="private"|"public")` describes client caching; it does not store server results. TTL must be a nonnegative integer. Public policy must agree with identity/visibility; the dispatcher preserves privacy restrictions. `Icon` accepts HTTPS/data URIs without fetching them. `ContentAnnotations.priority` is limited to 0–1.

Metadata is validated and bounded by `MCP_MAX_METADATA_SIZE`. Application metadata and schema hooks cannot overwrite reserved protocol keys. Use namespaced keys and avoid putting sensitive context into diagnostics for convenience.

Evidence: [builders](../../responses.py), [normalization](../../normalization.py), [metadata](../../protocol/metadata.py), [validation](../../protocol/validation.py). Tests: [responses](../../../../tests/mcp/test_responses.py), [codecs](../../../../tests/mcp/protocol/test_codecs.py), [limit auditing](../../../../tests/mcp/test_audit_edges.py). See [transports](transports-and-configuration.md).
