# orionis.mcp

> API reference derived from the current implementation.

## Table of contents

- Requirements
- Functional overview
- Module structure
- API reference
- Usage examples
- Design characteristics
- Performance and concurrency
- Compatibility notes
- Verification and limitations

## Requirements

Python 3.14 or newer, as declared by pyproject.toml.

## Functional overview

The orionis.mcp initializer exports 19 public symbols. This reference uses __all__, export routes, and current source files as evidence.

## Module structure

| Path | Responsibility |
| --- | --- |
| ../__init__.py | Defines package exports. |
| orionis.mcp/ | Implementations and subpackages for those exports. |

## API reference

| Symbol | Verified import | Source | Declaration | Observed behavior |
| --- | --- | --- | --- | --- |
| MCP_PROTOCOL_VERSION | from orionis.mcp import MCP_PROTOCOL_VERSION | [protocol/constants.py](../protocol/constants.py) | exported constant or alias | Exported public constant or alias. |
| CacheHint | from orionis.mcp import CacheHint | [protocol/metadata.py](../protocol/metadata.py) | CacheHint | Describe client cache freshness without caching server-side results. |
| Completion | from orionis.mcp import Completion | [protocol/results.py](../protocol/results.py) | Completion | At most one hundred completion values. |
| ContentAnnotations | from orionis.mcp import ContentAnnotations | [protocol/metadata.py](../protocol/metadata.py) | ContentAnnotations | Resource/content audience, relevance, and modification hints. |
| Icon | from orionis.mcp import Icon | [protocol/metadata.py](../protocol/metadata.py) | Icon | An icon reference; the server never fetches its source. |
| InputRequiredResult | from orionis.mcp import InputRequiredResult | [protocol/results.py](../protocol/results.py) | InputRequiredResult | An MRTR interim result, never a pushed JSON-RPC request. |
| McpConfig | from orionis.mcp import McpConfig | [config.py](../config.py) | exported constant or alias | Exported public constant or alias. |
| McpContext | from orionis.mcp import McpContext | [context.py](../context.py) | exported constant or alias | Exported public constant or alias. |
| McpExtension | from orionis.mcp import McpExtension | [server/extension.py](../server/extension.py) | McpExtension | Declare negotiated capabilities and extension-owned method/schema hooks. |
| McpRequest | from orionis.mcp import McpRequest | [context.py](../context.py) | McpRequest | Hold only explicit input and native context for one independent call. |
| McpRequest.identity | from orionis.mcp import McpRequest | [context.py](../context.py) | def identity(self) -> IAuthenticatable / None | Read identity through Orionis' scoped authentication lifecycle. Returns ------- IAuthenticatable / None Result of the operation described above. |
| McpRequest.client_capabilities | from orionis.mcp import McpRequest | [context.py](../context.py) | def client_capabilities(self) -> Mapping[str, object] | Read capabilities declared on this request, never a previous call. Returns ------- Mapping[str, object] Result of the operation described above. |
| McpResponse | from orionis.mcp import McpResponse | [responses.py](../responses.py) | McpResponse | Compose protocol content without knowing the transport or DI container. |
| McpResponse.text | from orionis.mcp import McpResponse | [responses.py](../responses.py) | def text(cls, value: str) -> Self | Return text content. Parameters ---------- value : str Value to inspect, transform or validate. Returns ------- Self Text content. |
| McpResponse.image | from orionis.mcp import McpResponse | [responses.py](../responses.py) | def image(cls, value: bytes, mime_type: str) -> Self | Encode raw image bytes once. Parameters ---------- value : bytes Value to inspect, transform or validate. mime_type : str Value supplied for ``mime_type``. Returns ------- Self Result of the operation described above. |
| McpResponse.audio | from orionis.mcp import McpResponse | [responses.py](../responses.py) | def audio(cls, value: bytes, mime_type: str) -> Self | Encode raw audio bytes once. Parameters ---------- value : bytes Value to inspect, transform or validate. mime_type : str Value supplied for ``mime_type``. Returns ------- Self Result of the operation described above. |
| McpResponse.resource | from orionis.mcp import McpResponse | [responses.py](../responses.py) | def resource(cls, uri: str, value: str / bytes, mime_type: str / None) -> Self | Embed text or binary resource content at an explicit URI. Parameters ---------- uri : str Value supplied for ``uri``. value : str / bytes Value to inspect, transform or validate. mime_type : str / None Value supplied for ``mime_type``. Returns ------- Self Result of the operation described above. |
| McpResponse.resourceLink | from orionis.mcp import McpResponse | [responses.py](../responses.py) | def resourceLink(cls, uri: str, name: str, *, title: str / None, description: str / None, mime_type: str / None) -> Self | Link to a resource without loading it. Parameters ---------- uri : str Value supplied for ``uri``. name : str Value supplied for ``name``. title : str / None Value supplied for ``title``. description : str / None Value supplied for ``description``. mime_type : str / None Value supplied for ``mime_type``. Returns ------- Self Result of the operation described above. |
| McpResponse.structured | from orionis.mcp import McpResponse | [responses.py](../responses.py) | def structured(cls, value: object) -> Self | Return any JSON value and the recommended serialized text content. Parameters ---------- value : object Value to inspect, transform or validate. Returns ------- Self Any JSON value and the recommended serialized text content. |
| McpResponse.error | from orionis.mcp import McpResponse | [responses.py](../responses.py) | def error(cls, message: str) -> Self | Return an application-visible tool error, with an explicit safe message. Parameters ---------- message : str Value supplied for ``message``. Returns ------- Self An application-visible tool error, with an explicit safe message. |
| McpResponse.progress | from orionis.mcp import McpResponse | [responses.py](../responses.py) | def progress(cls, current: float, total: float / None, message: str / None) -> Self | Yield progress; the dispatcher suppresses it without client opt-in. Parameters ---------- current : float Value supplied for ``current``. total : float / None Value supplied for ``total``. message : str / None Value supplied for ``message``. Returns ------- Self Result of the operation described above. |
| McpResponse.asAssistant | from orionis.mcp import McpResponse | [responses.py](../responses.py) | def asAssistant(self) -> Self | Assign the assistant role for a prompt response. Returns ------- Self Result of the operation described above. |
| McpResponse.asUser | from orionis.mcp import McpResponse | [responses.py](../responses.py) | def asUser(self) -> Self | Assign the user role for a prompt response. Returns ------- Self Result of the operation described above. |
| McpResponse.withMeta | from orionis.mcp import McpResponse | [responses.py](../responses.py) | def withMeta(self, metadata: dict[str, object]) -> Self | Attach result metadata without allowing reserved protocol keys. Parameters ---------- metadata : dict[str, object] Metadata associated with the current operation. Returns ------- Self Result of the operation described above. |
| McpResponse.withContentMeta | from orionis.mcp import McpResponse | [responses.py](../responses.py) | def withContentMeta(self, metadata: dict[str, object]) -> Self | Attach application metadata to each content block. Parameters ---------- metadata : dict[str, object] Metadata associated with the current operation. Returns ------- Self Result of the operation described above. |
| McpResponse.withAnnotations | from orionis.mcp import McpResponse | [responses.py](../responses.py) | def withAnnotations(self, annotations: ContentAnnotations) -> Self | Set audience, priority and modification hints on content blocks. Parameters ---------- annotations : ContentAnnotations Value supplied for ``annotations``. Returns ------- Self Result of the operation described above. |
| McpState | from orionis.mcp import McpState | [state.py](../state.py) | McpState | Seal state across workers sharing an application key and GCM cipher. |
| McpState.seal | from orionis.mcp import McpState | [state.py](../state.py) | def seal(self, request: McpRequest, value: object, *, ttl: int) -> str | Encrypt data bound to its principal, arguments, method and expiry. Parameters ---------- request : McpRequest Current request and its trusted execution context. value : object Value to inspect, transform or validate. ttl : int Value supplied for ``ttl``. Returns ------- str Result of the operation described above. |
| McpState.open | from orionis.mcp import McpState | [state.py](../state.py) | def open(self, request: McpRequest) -> object | Authenticate and validate client-carried state before using its data. Parameters ---------- request : McpRequest Current request and its trusted execution context. Returns ------- object Result of the operation described above. |
| Prompt | from orionis.mcp import Prompt | [server/primitives.py](../server/primitives.py) | Prompt | Declare string arguments and return user/assistant prompt messages. |
| PromptArgument | from orionis.mcp import PromptArgument | [protocol/metadata.py](../protocol/metadata.py) | PromptArgument | Declare one string-valued prompt argument. |
| Resource | from orionis.mcp import Resource | [server/primitives.py](../server/primitives.py) | Resource | Read a declared URI or RFC 6570 template without implicit file access. |
| Server | from orionis.mcp import Server | [server/primitives.py](../server/primitives.py) | Server | Define a server independently of any connection or transport. |
| Tool | from orionis.mcp import Tool | [server/primitives.py](../server/primitives.py) | Tool | Declare a typed input, optional typed output, and an injectable handle method. |
| ToolAnnotations | from orionis.mcp import ToolAnnotations | [protocol/metadata.py](../protocol/metadata.py) | ToolAnnotations | Describe tool behavior as hints, never as authorization rules. |
| ToolCatalog | from orionis.mcp import ToolCatalog | [server/catalog.py](../server/catalog.py) | ToolCatalog | Hide catalog tools behind bounded search_tools and execute_tools tools. |

## Usage examples

    from orionis.mcp import MCP_PROTOCOL_VERSION

The import path matches the API table. Import status: failed: missing uri_template.

## Design characteristics

The package uses an explicit public surface. Private names are excluded; declarations link to their concrete owner.

## Performance and concurrency

No uniform guarantee is declared at package level. Inspect each linked file for I/O, coroutines, caches, locks, and shared state.

## Compatibility notes

Declared minimum: Python 3.14. Validation used Python 3.14.3. Dependency bounds are in pyproject.toml.

## Verification and limitations

Python files were analysed and exports verified. Failures from dependencies, callbacks, I/O, or configuration may propagate and are not presented as exhaustive.
