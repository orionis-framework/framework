# Native MCP for Orionis

[Español](README.es.md)

Orionis implements **MCP 2026-07-28** over Streamable HTTP and STDIO. A server
declaration uses the application's existing container, schemas, authentication,
router, exception reporting and lifecycle. HTTP works through both native ASGI
and RSGI adapters. There is no second application or external MCP runtime.

This revision is stateless: each request carries its protocol version and client
capabilities. `server/discover` is optional and does not establish a connection
session. `initialize`, `notifications/initialized`, `ping`, legacy session IDs,
standalone SSE endpoints and implicit downgrade are not supported.

## Declare and register a server

```python
# app/mcp/servers/weather_server.py
from orionis.mcp import McpResponse, Server, Tool, ToolAnnotations
from orionis.schemas import Schema
from orionis.schemas.constraints import MinLength
from orionis.schemas.fields import Field


class WeatherInput(Schema):
    location: Field[str, MinLength(2)]


class WeatherTool(Tool[WeatherInput]):
    name = "weather"
    description = "Return the forecast for a city."
    annotations = ToolAnnotations(read_only=True, destructive=False)

    async def handle(self, payload: WeatherInput) -> McpResponse:
        return McpResponse.text(f"Forecast for {payload.location}")


class WeatherServer(Server):
    name = "Weather"
    version = "1.0.0"
    tools = (WeatherTool,)
```

```python
# routes/ai.py
from app.mcp.servers.weather_server import WeatherServer
from orionis.support.facades.mcp import Mcp

Mcp.web("/mcp/weather", WeatherServer)
Mcp.local("weather", WeatherServer)
```

Configure `app.withRouting(ai="routes/ai.py")` before `app.create()`. AI route
files load during provider boot for both HTTP and CLI, including a warm HTTP
route cache. `Mcp.web` returns the native `FluentRoute`, so ordinary route groups
and `.middleware(...)` apply. Endpoints use a fixed path and the API pipeline;
local handles identify explicitly registered classes and never import client
supplied module paths.

```text
python reactor mcp:list
python reactor mcp:start weather
python reactor make:mcp-server Weather
python reactor make:mcp-tool Weather
python reactor make:mcp-resource Status
python reactor make:mcp-prompt Explain
```

## Typed input, dependency injection and access

`Tool[Input, Output]` declares an Orionis `Schema` or supported typed input and an
optional structured output schema. Explicit `input` and `output` class attributes
are also available. Native field constraints, documentation and JSON Schema
metadata are retained. Handler signatures and schema metadata compile at boot;
malformed declarations, conflicting names and invalid header annotations fail
before requests are admitted.

Only the declared payload parameter receives tool arguments. Constructors and
other typed handler parameters resolve through the existing container. Client
keys never become arbitrary DI keyword arguments. Keep injected service types
available at runtime so Orionis can resolve their annotations.

Inject `McpRequest` (also exported as `McpContext`) for immutable request input,
`arguments`, `params`, `meta`, `uri_variables`, `input_responses`, `request_state`
and the current native authentication context. `identity` comes from Orionis
authentication, never from client metadata. `native_request` is present only for
HTTP. STDIO does not invent an authenticated HTTP user.

Optional `shouldRegister(...)` and `authorize(...)` hooks run through compiled DI
plans for each request. They affect listing, direct invocation, completion and
catalog access. They can depend on the current identity or services. Tool
annotations and a successful `shouldRegister` check are not authorization.

The native HTTP request scope remains alive through response streaming. STDIO
creates one fresh application scope per concurrent invocation. Primitive
instances are resolved per operation; shared registries do not retain requests,
identities, payloads or scoped services. Async generators retain their scope until
completion or cancellation. Short synchronous handlers execute on the event loop;
use asynchronous services for I/O.

## Resources, prompts and responses

Declare `Resource.uri` for a literal URI or `Resource.uri_template` for an RFC 6570
template; template variables are available in `request.uri_variables`. A resource
URI never grants filesystem access. Declare `Prompt.arguments` as a tuple of
`PromptArgument` values; prompt arguments are strings. A prompt or resource
template can implement `complete(...)`, returning `Completion` or a list of
strings. Completion capability is advertised only when a provider exists.

`McpResponse` provides `text`, `image`, `audio`, `resource`, `resourceLink`,
`structured`, `error` and `progress` factories. Images/audio accept bytes and a
MIME type. `structured` accepts any JSON value, including arrays, scalars and
`null`; a declared output schema is validated. `asUser()` and `asAssistant()` set
prompt roles. `withMeta`, `withContentMeta` and `withAnnotations` attach supported
metadata and content hints without permitting applications to overwrite reserved
protocol metadata.

Return a response, a sequence of content responses, or yield responses from a
generator. Yielding `McpResponse.progress(...)` produces notifications only when
the current request provides `progressToken`; content is collected within the
response budget and ends in one final result. HTTP uses native SSE for generators
and subscriptions, and ordinary JSON for completed calls. Transport backpressure
controls producer reads. Closing a source, including one never started, releases
its generator and admission slot before the request scope is disposed.

Use `McpResponse.error("safe message")` for a tool execution failure. Validation
and internal tool failures produce `isError`; malformed protocol requests produce
JSON-RPC errors. Unexpected exceptions use native reporting and safe public
messages. HTTP authentication, middleware and debug failures cannot turn the MCP
endpoint into an HTML page or login redirect; challenges, retry and security
headers are preserved.

## Streamable HTTP

Send one JSON-RPC request per POST, with both supported response media types:

```http
POST /mcp/weather HTTP/1.1
Content-Type: application/json
Accept: application/json, text/event-stream
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tools/call
Mcp-Name: weather

{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"weather","arguments":{"location":"Bogotá"},"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{}}}}
```

`Mcp-Method` must match `method`. `Mcp-Name` must match `params.name` for tool and
prompt calls, or `params.uri` for resource reads. Header names are case
insensitive; duplicate required fields are rejected. Missing, malformed or
mismatched mirrored headers produce HTTP 400 / `-32020`. Missing intrinsic body
metadata produces `-32602` once the required version header is present. A matching
unsupported protocol version produces HTTP 400 / `-32022`; an unknown method with
valid metadata produces HTTP 404 / `-32601`. Notifications receive empty HTTP 202.
GET and DELETE receive 405; native OPTIONS handling remains available.

Every present `Origin` must match `McpConfig.allowed_origins` exactly, including
unsupported methods and preflight. An absent Origin is accepted; the default
empty allowlist rejects every present Origin. Set explicit serialized HTTP(S)
origins with `app.withConfigMcp(allowed_origins=("https://client.example",))`.
Configure ordinary authentication and CORS independently; allowing an origin does
not authenticate a caller. Bind local development listeners to loopback.

Native ASGI and RSGI disconnect monitoring is enabled **for MCP endpoints by
default**, including handlers that will return normal JSON. It reuses Orionis'
existing disconnect watchers even when the global `http.monitor_disconnects`
setting is false. Disconnect cancels the handler or stream; cancellation cleanup
is shielded while owned producers and scoped services close. Other routes retain
their normal monitoring configuration.

### Mirrored tool parameters

```python
from orionis.schemas.metadata import ExtraJsonSchema


class TenantInput(Schema):
    tenant: Field[str, ExtraJsonSchema({"x-mcp-header": "Tenant"})]
```

An HTTP call with `arguments.tenant="north"` must include
`Mcp-Param-Tenant: north`. Annotations are accepted only on statically reachable
`properties` chains with `string`, `integer` or `boolean` types. Names must be
valid HTTP field tokens and unique without regard to case. Array elements,
conditional/composed schema paths and unresolved reference paths cannot introduce
mirrors. Missing or null values require the corresponding header to be absent.
Integer values must be within the JSON safe integer range; numeric headers compare
numerically. Booleans use `true` or `false`.

Visible ASCII with no leading/trailing whitespace can be sent literally. Values
with non-ASCII, control characters or edge whitespace use
`=?base64?{BASE64_OF_UTF8}?=`. A literal that already looks like that sentinel must
also be encoded. Invalid Base64 or UTF-8 is rejected. These rules also apply to
the encoded name field. Mirror validation happens before tool execution; the
body remains the source of input and all ordinary validation and authorization
still run.

## STDIO

`mcp:start NAME` reads bounded newline-delimited UTF-8 JSON and writes complete
JSON-RPC frames followed by a newline. The entry boundary reserves stdout for the
protocol before application bootstrap, provider hooks and command parsing;
diagnostics go to stderr. Use stderr for application logging, and do not write
directly to the stdout file descriptor.

Independent requests execute concurrently with isolated scopes and one serialized
writer. The read loop remains available for `notifications/cancelled` with a
`requestId`; cancellation releases only that invocation. Duplicate active IDs and
capacity overflow are rejected. EOF cancels outstanding calls, awaits cleanup and
exits. Windows pipe readers/writers use bounded daemon bridges so a blocked OS
read does not hold the event loop's executor shutdown open.

## Subscriptions and explicit multi-round trips

`subscriptions/listen` is an ordinary long-lived request with a `notifications`
filter containing `toolsListChanged`, `promptsListChanged`, `resourcesListChanged`
and/or `resourceSubscriptions`. Opt in on the server with `list_changed=True` and
`resource_subscriptions=True`. The first notification is
`notifications/subscriptions/acknowledged`, containing the accepted subset.
Resource filters run availability and authorization checks at admission. Every
subscription notification carries
`_meta["io.modelcontextprotocol/subscriptionId"]` equal to the original request ID.

Publish through `await Mcp.toolsChanged(ServerClass)`, `promptsChanged`,
`resourcesChanged` or `resourceUpdated(ServerClass, uri)`. The default
`IMcpEventBus` implementation is worker-local and retains only server keys,
filters and bounded pending changes. Duplicate changes coalesce; an overloaded
subscriber ends gracefully. It provides no cross-worker delivery or reconnect
history. Bind a distributed `IMcpEventBus` implementation when an application
needs that behavior. HTTP heartbeats are SSE comments. Shutdown completes
subscriptions; HTTP disconnect and STDIO cancellation remove listeners promptly.

For additional input, return `InputRequiredResult(inputRequests={...},
requestState=...)`. Supported embedded inputs are elicitation, roots and sampling
as defined by this revision; sampling support is retained for protocol
compatibility and is deprecated upstream. Capabilities are checked on the current
request. The client retries the original method with `inputResponses` and any
explicit state. There are no pushed server JSON-RPC requests or hidden session
state. Applications must validate the meaning of returned input for their own
operation before taking action.

Optional `McpState.seal(request, value, ttl=300)` / `open(request)` uses the native
AEAD encrypter and requires `AES-128-GCM` or `AES-256-GCM`. State is bound to its
expiry, server, method, target, arguments and native authenticated principal.
Workers can validate it with the same application key. It does not provide
single-use replay prevention; implement durable idempotency for side effects.
The dispatcher supplies the trusted `server_id`; application code must not invent
or replace that identifier when sealing state.

## Catalogs and extensions

`Server.tools = (ToolCatalog(FirstTool, SecondTool),)` publishes bounded
`search_tools` and `execute_tools` entry points. Original catalog tools stay out of
the ordinary list. Search uses a precompiled deterministic lexical index and
applies per-request access checks. Execution reuses the normal input, access,
output and error pipeline; call counts and output bytes are bounded.

A single nested call can return MRTR. A multi-call batch encountering MRTR returns
a tool error directing the caller to invoke that tool individually, so completed
side effects are not automatically replayed. Nested progress is consumed without
accumulation and is not forwarded as another request's progress.

HTTP mirrors describe the actual `execute_tools` input schema. They cannot mirror
fields inside its `calls` array, so an inner tool's annotations do not create
additional outer HTTP headers. Expose that tool directly when a proxy or security
policy must inspect its mirrored arguments. Inner authorization always runs.
A direct call to a catalog tool by its own name validates that tool's HTTP mirrors.

`McpExtension` declares explicit capability metadata, method handlers, precompiled
decoders and an optional schema hook. No optional extension is enabled by default;
Tasks is not implemented. Schema hooks may add extension-owned fields but cannot
change standard metadata or native validation constraints. Applications own
extension semantics and compatibility.

## Budgets, architecture and tests

`app.withConfigMcp(...)` configures validated immutable budgets:

| Setting | Default | Scope |
| --- | ---: | --- |
| `max_request_size` | 1 MiB | One HTTP body / STDIO frame |
| `max_response_size` | 4 MiB | One encoded response / accumulated content |
| `max_metadata_size` | 64 KiB | Request / application result metadata |
| `max_concurrent_requests` | 32 | Each HTTP endpoint or STDIO transport, per worker |
| `default_page_size` / `max_page_size` | 50 / 100 | Server pagination configuration |
| `subscription_buffer_size` | 64 | Pending distinct changes per listener |
| `max_subscriptions` | 1024 | Default event bus, per worker |
| `max_resource_subscriptions` | 64 | Resource filters per listen request |
| `subscription_keepalive` | 15 s | HTTP idle comment interval |
| `tool_search_max_results` | 20 | Search results |
| `tool_search_max_calls` | 5 | Nested calls per execution |
| `tool_search_max_output_bytes` | 256 KiB | Catalog output |

Long-lived streams occupy admission slots until closed. HTTP also obeys the native
kernel's limits. Pagination uses opaque stateless cursors and rechecks access on
each request. Cache hints default to `ttlMs=0`, `cacheScope="private"`; setting
`CacheHint` is a client caching declaration, not a server-side result cache.

```text
Provider boot → compile immutable registry + schemas + DI/header plans
HTTP router → native middleware/scope → HTTP transport ┐
STDIO reader → bounded tasks + fresh native scope      ├→ dispatcher → primitive
TestCase.mcp → existing app + fresh native scope      ┘
Response bytes / owned iterator → native JSON/SSE or serialized STDIO writer
```

The generic HTTP endpoint policy is resolved once at boot. Its path lookup handles
Origin and protocol error presentation around the existing kernel pipeline; the
kernel does not import MCP or route requests through a second router. HTTP route
cache metadata still points to the stable native MCP controller.

```python
from orionis.test import TestCase

class TestWeather(TestCase):
    async def testWeather(self) -> None:
        """Verify the weather tool through the native test runner.

        Returns
        -------
        None
            Check the successful tool response and its text.
        """
        client = await self.mcp(WeatherServer)
        response = await client.tool("weather", {"location": "Bogotá"})
        response.assertOk()
        response.assertTextContains("Bogotá")
```

Use `client.stream(...)` for subscriptions and cancellation; `request(...)` collects
finite exchanges. The helper uses the application already booted by `reactor test`;
pass `app=` for an isolated container or `config=` for explicit client limits.
Close streams when stopping early, for example with `contextlib.aclosing`.
The client exercises encoded input/output through the native dispatcher. HTTP
adapter, routing, headers, Origin and middleware have separate integration tests.

```text
python reactor test --start-dir=tests/mcp --verbosity=1
python reactor test --start-dir=tests/test --verbosity=1
python reactor test --start-dir=tests/http --verbosity=0
```

External conformance and Inspector checks require separate tooling and fixtures.
The repository's test tree contains native Orionis test modules; it does not
bundle those runners, schema snapshots or generated verification reports.

Protocol decisions follow the [dated official specification](https://github.com/modelcontextprotocol/modelcontextprotocol/tree/75db1e987cbbba6d170315dc99d0dfc440754aef/docs/specification/2026-07-28)
and its [dated schema](https://github.com/modelcontextprotocol/modelcontextprotocol/tree/75db1e987cbbba6d170315dc99d0dfc440754aef/schema/2026-07-28).
