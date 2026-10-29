# HTTP, STDIO and configuration

Register a Server class at boot through the `Mcp` facade. `web(path, server)` creates a native POST API route and returns its builder; paths must be fixed, without parameters, query or fragment. `local(name, server)` registers an explicit handle containing letters, digits, dots, hyphens or underscores. It does not start arbitrary modules named by a client.

```python
from orionis.mcp import McpResponse, Server, Tool
from orionis.schemas import Schema
from orionis.support.facades import Mcp

class GreetInput(Schema):
    name: str

class GreetTool(Tool[GreetInput, str]):
    def handle(self, payload: GreetInput) -> McpResponse:
        return McpResponse.structured(f"Hello, {payload.name}!")

class ApplicationServer(Server):
    name = "Application"
    tools = (GreetTool,)

Mcp.web("/mcp/application", ApplicationServer)
Mcp.local("application", ApplicationServer)
```

This block requires a booted application. Attach API authentication middleware to the web builder when the whole server requires credentials. Identity resolution does not automatically require authentication; `authorize` hooks still protect operations.

## The actual HTTP contract

The transport requires POST, one `Content-Type: application/json` and Accept explicitly including both `application/json` and `text/event-stream` with positive quality. Finite responses use JSON; progress/subscriptions may use SSE. This checkout's protocol mirrors envelope metadata in headers:

```http
POST /mcp/application HTTP/1.1
Content-Type: application/json
Accept: application/json, text/event-stream
MCP-Protocol-Version: 2026-07-28
MCP-Method: tools/call
MCP-Name: greet
```

The corresponding body reuses the tool from [the first chapter](servers-and-tools.md):

```json
{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"greet","arguments":{"name":"Ada"},"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{}}}}
```

Version, method and primitive name/URI headers must match the body. Parameters annotated with `x-mcp-header` additionally require compatible `MCP-Param-<name>` headers; only statically reachable primitive properties support these annotations. Binary resource content/MIME does not change the envelope's JSON Content-Type.

Absent Origin is allowed. A present Origin must match exactly one validated HTTP(S) `allowed_origins` entry. There are no wildcards or implicit same-origin exceptions. Bootstrap reads `CORS_ALLOW_ORIGINS`; HTTP CORS and WebSocket can apply different rules. Origin, method and media-type failures are rejected before reading a large body.

`allowed_origins` is an independently copied `list[str]`. When `CORS_ALLOW_ORIGINS`
is unset, the editable [config/mcp.py](../../../../config/mcp.py) supplies the Orionis
MCP Inspector origin. Core `McpConfig` defaults to `[]` without embedding application
URLs. Set the environment variable or edit the bootstrap list to replace this
default; an explicit empty list rejects every present Origin. Entries contain only
scheme, host and optional port, without a path or trailing slash.

## STDIO and console

Start a registered handle with `python -B reactor mcp:start application`; `python -B reactor mcp:list` lists servers. Generators are `make:mcp-server`, `make:mcp-tool`, `make:mcp-resource` and `make:mcp-prompt`. Commands run in the configured application's context.

STDIO uses line-delimited JSON; stdout is reserved for protocol frames and diagnostics belong on stderr. The transport bounds reads/concurrency, accepts cancellation notifications and shares the HTTP dispatcher. Never print ordinary logging to stdout inside handlers.

## Budgets

| Variable | Default |
|---|---:|
| `MCP_MAX_REQUEST_SIZE` | `HTTP_MAX_BODY_SIZE` or 1 MiB |
| `MCP_MAX_CONCURRENT_REQUESTS` | `HTTP_MAX_CONCURRENT_REQUESTS` or 32 |
| `MCP_DEFAULT_PAGE_SIZE`, `MCP_MAX_PAGE_SIZE` | 50, 100 |
| `MCP_MAX_RESPONSE_SIZE`, `MCP_MAX_METADATA_SIZE` | 4 MiB, 64 KiB |
| `MCP_SUBSCRIPTION_BUFFER_SIZE`, `MCP_MAX_SUBSCRIPTIONS` | 64, 1024 |
| `MCP_MAX_RESOURCE_SUBSCRIPTIONS` | 64 |
| `MCP_SUBSCRIPTION_KEEPALIVE` | 15 seconds |
| `MCP_TOOL_SEARCH_MAX_RESULTS`, `MCP_TOOL_SEARCH_MAX_CALLS` | 20, 5 |
| `MCP_TOOL_SEARCH_MAX_OUTPUT_BYTES` | 256 KiB |

All numeric budgets are positive; default page size cannot exceed maximum. Transport admission includes streams until closure. Manager APIs include `getWebServer`, `getLocalServer`, `servers`, `dispatchHttp`, `startLocal` and `shutdown`; integration usually owns dispatch/cleanup. Overload, invalid requests and oversized responses fail explicitly instead of building unbounded queues.

Evidence: [manager](../../manager.py), [HTTP](../../transport/http.py), [headers](../../transport/headers.py), [STDIO](../../transport/stdio.py), [config](../../../../config/mcp.py). Tests: [HTTP](../../../../tests/mcp/transport/test_http.py), [headers](../../../../tests/mcp/transport/test_headers.py), [STDIO](../../../../tests/mcp/transport/test_stdio.py), [disconnects](../../../../tests/mcp/transport/test_disconnect.py).
