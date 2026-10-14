# Progress, continuation, subscriptions and extensions

These capabilities support flows longer than simple calls while keeping requests independent. Model business effects explicitly: transport alone provides no distributed transactions, durable delivery or idempotent retries.

## Progress with a final result

```python
from orionis.mcp import McpResponse, Tool

class ReportTool(Tool):
    async def handle(self):
        yield McpResponse.progress(0, total=2, message="Starting")
        yield McpResponse.progress(1, total=2, message="Collecting")
        yield McpResponse.text("Report ready")
```

The handler is an asynchronous generator. Updates become `notifications/progress` only when the request provides `progressToken`; otherwise they are suppressed. Numbers must be finite and progress must strictly increase. Other items are collected and normalized into the final result within `MCP_MAX_RESPONSE_SIZE`; this is not an unlimited stream of partial results. Use `try/finally` for resources and propagate cancellation.

## Requesting more input and resuming

Handlers can return `InputRequiredResult(inputRequests=..., requestState=...)`. Clients resolve inputs and retry with `inputResponses`/`requestState`; no server thread remains suspended retaining the previous call's memory. Supported input methods are `elicitation/create`, `sampling/createMessage` and `roots/list`, subject to current request capabilities.

```python
from orionis.mcp import InputRequiredResult, McpRequest, McpResponse, Tool

class ConfirmTool(Tool):
    async def handle(self, request: McpRequest):
        if request.input_responses:
            return McpResponse.text("Response received; validate before acting")
        return InputRequiredResult(inputRequests={
            "choice": {"method": "elicitation/create", "params": {
                "message": "Choose a label",
                "requestedSchema": {"type": "object", "properties": {
                    "label": {"type": "string"}
                }},
            }},
        })
```

The example demonstrates shape rather than acting on any response. Before effects, check the key, action and validated content; decline/cancel is not acceptance. Elicitation forms support flat objects with primitive fields, not arbitrary nested schemas. Clients announce compatible capabilities in `_meta`; missing capability declarations fail before requesting input.

For trusted continuation state use `McpState.seal(request, value, ttl=300)` and `open(request)`. It requires `app.cipher` AES-128-GCM or AES-256-GCM and encrypts/authenticates state bound to principal, trusted server, method, arguments and expiry. Workers must share key/cipher. Decrypt/validate before using state; copying `requestState` does not make client data trusted. General replay prevention for effects is not provided: coordinate idempotency in domain storage.

## Subscribing to changes

Declare `Server.list_changed=True` for catalog changes and `resource_subscriptions=True` for resources. Clients open `subscriptions/listen` with a `notifications` filter containing `toolsListChanged`, `promptsListChanged`, `resourcesListChanged` or `resourceSubscriptions`. URI access is checked at admission and during streaming as implemented by the dispatcher.

After catalog changes call `await Mcp.toolsChanged(ServerClass)`, `promptsChanged`, `resourcesChanged` or `resourceUpdated(ServerClass, uri)`. The class must be registered in that manager. Notifications are scoped to that server's listeners. The default event bus is process-local with bounded buffers/subscriptions; it provides neither cross-worker delivery nor replay. Close streams/listeners on disconnect and shutdown.

Tests should use `McpTestClient.stream(...)` for subscriptions; `request(...)` collects finite exchanges and would wait indefinitely for a live stream. The client retains the scope until stream consumption/closure.

## Large tool catalogs

`Server.tools = (ToolCatalog(ToolA, ToolB),)` exposes `search_tools` and `execute_tools` with configurable names. Search accepts `query` and `limit`, applies per-request policies and returns metadata/schemas. Execute accepts `calls=[{"name": ..., "arguments": ...}]`, checks every operation and bounds count/output. Calls execute sequentially, not as an atomic transaction. If one needs input, call it individually; do not replay effects already completed in a batch.

## Extending protocol methods

`McpExtension(identifier=..., capabilities=..., methods=..., decoders=..., schema_hook=...)` registers extension capabilities/handlers. Clients must negotiate the identifier. Schema hooks may attach extension metadata but cannot modify compiled names, schemas, URI, MIME or other standard fields, nor reserved keys. Use your own namespace and typed decoders; extensions must not bypass core validation.

Evidence: [dispatcher](../../dispatcher.py), [MRTR](../../protocol/mrtr.py), [state](../../state.py), [bus](../../subscriptions/event_bus.py), [catalog](../../server/catalog.py), [extensions](../../server/extension.py). Tests: [streams](../../../../tests/mcp/test_streams.py), [state](../../../../tests/mcp/test_state.py), [events](../../../../tests/mcp/test_event_bus.py), [auditing](../../../../tests/mcp/test_audit_edges.py). Review [budgets](transports-and-configuration.md).
