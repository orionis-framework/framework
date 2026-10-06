# orionis.mcp

> `orionis.mcp` provides native, typed, and transport-independent Model Context Protocol servers for Orionis applications.

## Overview

The package declares tools, resources, prompts, and servers as Python classes. Orionis validates and compiles those declarations once, then exposes the same immutable definition through HTTP, STDIO, dependency injection, the `Mcp` facade, and the testing client. The implemented protocol version is `2026-07-28`.

The runtime keeps request context isolated, validates JSON-RPC input and typed schemas, applies bounded concurrency and response sizes, and supports progress, elicitation, completion, subscriptions, pagination, cache hints, and extension methods.

## Requirements

- Python 3.14 or newer.
- A booted Orionis application for transport registration, dependency injection, authentication, and the `Mcp` facade.
- Input/output types supported by Orionis schemas and `msgspec` when using typed tools.
- Explicit trusted origins when browser clients send an HTTP `Origin` header.

## Quick start

```python
from orionis.mcp import McpResponse, Server, Tool, ToolAnnotations
from orionis.mcp.server.compiler import compile_server
from orionis.schemas import Schema


class GreetInput(Schema):
    name: str


class GreetTool(Tool[GreetInput, str]):
    description = "Return a greeting."
    annotations = ToolAnnotations(read_only=True, destructive=False)

    def handle(self, payload: GreetInput) -> str:
        return f"Hello, {payload.name}!"


class DemoServer(Server):
    name = "Demo"
    version = "1.0.0"
    tools = (GreetTool,)


compiled = compile_server(DemoServer)
assert tuple(compiled.tools) == ("greet",)
assert McpResponse.text("ready").content[0].text == "ready"
```

Validation: **Executed successfully** on CPython 3.14.6.

## Core concepts

### Declarations and compilation

`Tool`, `Resource`, `Prompt`, and `Server` contain static metadata and handler methods. `compile_server()` derives kebab-case names, compiles schemas and handler injection plans, validates metadata and URI templates, and produces a reusable `CompiledMcpServer`. Instances of handlers remain request-scoped; declarations must not hold mutable request state.

### Request context

`McpRequest` (also exported as `McpContext`) is a frozen snapshot containing the JSON-RPC id and method, server id, metadata, arguments, parameters, URI variables, transport, authentication context, and optional native HTTP request. Nested client mappings become read-only. `identity` delegates to Orionis authentication, while `client_capabilities` reads only the current request.

### Responses and protocol errors

`McpResponse` builds text, image, audio, embedded-resource, resource-link, structured, error, and progress results without knowing the transport. Tool-visible failures use `McpResponse.error()`; malformed JSON-RPC, invalid arguments, authorization failures, and internal failures use the typed exceptions in `exceptions.py` and become protocol errors.

### Transport independence

`McpManager.web()` and `local()` compile through one registry. HTTP registers a native fixed POST API route; STDIO is started only for a previously registered local handle. Both paths use the same dispatcher, invoker, configuration, and event bus.

### Hints are not policy

`ToolAnnotations`, `ContentAnnotations`, and `CacheHint` communicate behavior to clients. They do not authorize calls, cache server results, or replace application validation. Use authentication, `authorize()` hooks, and application services for enforcement.

## Module structure

| Path | Responsibility |
|---|---|
| `server/primitives.py` | Declarative `Tool`, `Resource`, `Prompt`, and `Server` bases. |
| `server/compiler.py` | Boot-time names, schemas, metadata, handlers, templates, and capabilities. |
| `server/catalog.py` | Bounded searchable catalogs exposed as synthetic tools. |
| `dispatcher.py` / `invoker.py` | JSON-RPC dispatch, validation, DI resolution, and handler invocation. |
| `responses.py` / `context.py` | Immutable response composition and request snapshots. |
| `transport/http.py` / `transport/stdio.py` | Native HTTP and standard-stream adapters. |
| `subscriptions/` | Scoped event publication, listeners, and resource subscriptions. |
| `protocol/` | Wire structs, constants, results, errors, and metadata validation. |
| `manager.py` / `provider.py` | Application registry, route integration, lifecycle, and facade binding. |
| `state.py` | Signed, request-bound continuation state. |

## Public API

The package root exports `MCP_PROTOCOL_VERSION`, `McpConfig`, `McpRequest`, `McpContext`, `McpResponse`, `McpState`, `Tool`, `Resource`, `Prompt`, `Server`, `ToolCatalog`, `McpExtension`, `CacheHint`, `Icon`, `ToolAnnotations`, `ContentAnnotations`, `PromptArgument`, `Completion`, and `InputRequiredResult`.

### Primitive declarations

- `Tool[InputType, OutputType]` declares input/output contracts and a `handle()` method. Optional `available()` and `authorize()` hooks are compiled when present.
- `Resource` declares exactly one absolute `uri` or RFC 6570 `uri_template`; a template handler receives decoded variables.
- `Prompt` declares string arguments and returns messages; an optional `complete()` supplies suggestions.
- `Server` aggregates primitives, extensions, cache policy, identity metadata, list-change support, and resource-subscription support.
- `ToolCatalog(*tools, search_name=..., execute_name=...)` hides a large group behind bounded search and execution tools.

### Response builders

`McpResponse.text()`, `image()`, `audio()`, `resource()`, `resourceLink()`, `structured()`, `error()`, and `progress()` create immutable values. `asAssistant()` and `asUser()` set prompt roles; `withMeta()`, `withContentMeta()`, and `withAnnotations()` return modified copies after validation.

### Manager and facade

`McpManager` provides `web`, `local`, `getWebServer`, `getLocalServer`, `servers`, `dispatchHttp`, `startLocal`, change notifications, and `shutdown`. Application code normally reaches the same singleton through `orionis.support.facades.Mcp`.

## Common workflows

### Register web and local endpoints

Declare servers under `app/mcp/servers`, then register them during application boot. `web()` accepts a fixed route without parameters, query, or fragment. `local()` accepts a stable handle containing letters, digits, dots, underscores, or hyphens.

### Model a typed tool

Use a `Schema` input when validation and JSON Schema are needed. Handler dependencies may be type-injected in addition to the payload/context. Declare an output type to make Orionis validate the returned value before serialization.

### Publish catalog changes

Enable the matching server capability, then call `toolsChanged`, `promptsChanged`, `resourcesChanged`, or `resourceUpdated`. Notifications require that the server class was registered in this manager and are scoped to its listeners.

### Test the wire contract

Use `orionis.test.McpTestClient` or `TestCase.mcp(...)`. The client uses the supplied application container, opens real scopes, passes bytes through the dispatcher, and returns decoded results plus notifications.

## Examples

### Declare resources and prompts

```python
from orionis.mcp import McpResponse, Prompt, PromptArgument, Resource, Server
from orionis.mcp.server.compiler import compile_server


class UserResource(Resource):
    uri_template = "demo://users/{user_id}"
    mime_type = "application/json"

    def handle(self, user_id: str) -> McpResponse:
        return McpResponse.structured({"id": user_id})


class ExplainPrompt(Prompt):
    arguments = (PromptArgument(name="topic", required=True),)

    def handle(self, topic: str) -> McpResponse:
        return McpResponse.text(f"Explain {topic}").asUser()


class ContentServer(Server):
    name = "Content"
    resources = (UserResource,)
    prompts = (ExplainPrompt,)


compiled = compile_server(ContentServer)
assert len(compiled.templates) == 1
assert "explain" in compiled.prompts
```

Validation: **Executed successfully** on CPython 3.14.6.

### Compose protocol content

```python
from orionis.mcp import ContentAnnotations, McpResponse

response = (
    McpResponse.structured({"status": "ok", "count": 2})
    .withMeta({"trace": "example"})
    .withContentMeta({"source": "docs"})
    .withAnnotations(ContentAnnotations(audience=("assistant",), priority=0.8))
)

assert response.structured_content == {"status": "ok", "count": 2}
assert response.meta["trace"] == "example"
assert response.content[0].meta["source"] == "docs"
```

Validation: **Executed successfully** on CPython 3.14.6.

### Inspect an immutable request

```python
from orionis.mcp import McpRequest

request = McpRequest(
    id=7,
    method="tools/call",
    arguments={"query": ["orionis"]},
    meta={"io.modelcontextprotocol/clientCapabilities": {"sampling": {}}},
)

assert request.transport == "test"
assert request.arguments["query"] == ("orionis",)
assert "sampling" in request.client_capabilities
```

Validation: **Executed successfully** on CPython 3.14.6.

### Group a large tool set

```python
from orionis.mcp import Server, Tool, ToolCatalog
from orionis.mcp.server.compiler import compile_server


class PingTool(Tool):
    description = "Return a health marker."

    def handle(self) -> str:
        return "pong"


class CatalogServer(Server):
    name = "Catalog"
    tools = (ToolCatalog(PingTool),)


compiled = compile_server(CatalogServer)
assert set(compiled.tools) == {"search_tools", "execute_tools"}
assert "ping" in compiled.catalog_tools
```

Validation: **Executed successfully** on CPython 3.14.6.

### Register through the facade

```python
from orionis.mcp import Server
from orionis.support.facades import Mcp


class ApplicationServer(Server):
    name = "Application"


Mcp.web("/mcp/application", ApplicationServer)
Mcp.local("application", ApplicationServer)
```

Validation: **Import and syntax validated** on CPython 3.14.6; registration requires a booted application and pinned facade.

### Verify response metadata

```python
from orionis.mcp import CacheHint, Icon, MCP_PROTOCOL_VERSION

hint = CacheHint(ttl_ms=30_000, scope="private")
icon = Icon(src="https://example.test/icon.png", mime_type="image/png")

assert MCP_PROTOCOL_VERSION == "2026-07-28"
assert hint.ttl_ms == 30_000
assert icon.src.startswith("https://")
```

Validation: **Executed successfully** on CPython 3.14.6.

## Configuration

| Environment variable | Default | Purpose |
|---|---:|---|
| `MCP_MAX_REQUEST_SIZE` | `HTTP_MAX_BODY_SIZE` or 1 MiB | Maximum request bytes. |
| `MCP_DEFAULT_PAGE_SIZE` / `MCP_MAX_PAGE_SIZE` | 50 / 100 | List pagination bounds. |
| `MCP_MAX_CONCURRENT_REQUESTS` | `HTTP_MAX_CONCURRENT_REQUESTS` or 32 | Per-transport concurrent request budget. |
| `MCP_SUBSCRIPTION_BUFFER_SIZE` | 64 | Buffered events per subscription. |
| `MCP_MAX_SUBSCRIPTIONS` | 1024 | Total event-bus subscription budget. |
| `MCP_MAX_RESOURCE_SUBSCRIPTIONS` | 64 | Resource subscriptions per request/client context. |
| `MCP_SUBSCRIPTION_KEEPALIVE` | 15.0 seconds | Streaming keepalive interval. |
| `CORS_ALLOW_ORIGINS` | empty | Browser HTTP origins shared with CORS and WebSocket. |
| `MCP_TOOL_SEARCH_MAX_RESULTS` | 20 | Catalog search result cap. |
| `MCP_TOOL_SEARCH_MAX_CALLS` | 5 | Calls in one catalog execution. |
| `MCP_TOOL_SEARCH_MAX_OUTPUT_BYTES` | 256 KiB | Catalog execution output cap. |
| `MCP_MAX_RESPONSE_SIZE` | 4 MiB | Serialized response cap. |
| `MCP_MAX_METADATA_SIZE` | 64 KiB | Metadata cap. |

Both `McpConfig` and `config/mcp.py` read `CORS_ALLOW_ORIGINS` directly. The developer may choose another environment key in the application configuration or supply explicit `allowed_origins`. No origins are silently removed before validation.

All numeric budgets must be positive; the default page size cannot exceed the maximum. An absent HTTP `Origin` is allowed, while a present origin must exactly match the validated HTTP(S) allowlist—there is no wildcard or implicit same-origin exception.

## Integration with Orionis

`McpProvider` binds the manager, configuration, and in-memory event bus and pins the `Mcp` facade. Native routing marks HTTP endpoints as API routes. Authentication is exposed through each `McpRequest`, and handler dependencies use normal container scopes.

The console offers `reactor mcp:list`, `reactor mcp:start <name>`, and generators for servers, tools, resources, and prompts. Only configured local names may be started; arbitrary dynamic imports are not accepted.

## Errors and edge cases

- Primitive names must match `[A-Za-z0-9_.-]{1,128}`; inferred class names become kebab-case.
- Resource URIs must be absolute. Complex RFC 6570 templates require a synchronous static/class `match(uri)` inverse.
- Reserved protocol metadata keys cannot be added by application metadata or extension schema hooks.
- Icon sources accept only HTTPS or `data:` URIs; content priority is limited to 0 through 1.
- Progress values must be finite. Progress is suppressed when the client did not provide the required opt-in token.
- Output validation occurs before serialization; return types that violate the declared tool output become protocol failures.
- Request snapshots are immutable, but injected services may have their own lifecycle and concurrency rules.

## Performance and concurrency

Compilation moves reflection, schema construction, route metadata, and URI-template work to boot. Compiled definitions are immutable and reused across requests and transports. Each request gets an application scope and independent handler resolution.

Concurrency, request bytes, response bytes, metadata bytes, pagination, catalog calls, and subscription buffers are bounded by `McpConfig`. Slow streaming clients can exhaust their bounded buffer; design consumers to drain events and always close streams. The in-memory event bus is process-local and is shut down with the manager.

## Compatibility

- Protocol version: `2026-07-28`; `SUPPORTED_VERSIONS` currently contains only that version.
- Python: 3.14+ because the public tool declaration uses PEP 695 generic syntax.
- HTTP clients must send supported JSON-RPC/MCP headers and accepted JSON or SSE media types as required by the transport.
- STDIO reserves standard output for protocol frames; diagnostic output belongs on standard error.

## Verification notes

- `tests/mcp`: **140 test methods passed** with the Orionis runner on CPython 3.14.6.
- Seven documentation programs were compiled; six standalone programs were executed successfully.
- The facade registration program was import/syntax validated because it requires a booted application.
- Documentation was checked against the public exports, compiler, dispatcher, transports, manager, configuration entity, metadata validators, console commands, and MCP testing client.

