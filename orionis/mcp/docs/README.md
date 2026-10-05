# Orionis MCP

MCP shares Orionis' container, HTTP responses, streaming cleanup and authentication
context. `McpProvider` binds `IMcpManager`, validated `McpConfig` and a bounded
`IMcpEventBus`; boot pins the facades and loads the application's `ai` route files.

## Registration

Declare `Server` subclasses with explicit tools, resources and prompts, then use
the `Mcp` facade's `web(path, server)` or `local(name, server)` registration in
`routes/ai.py`. HTTP registrations create native POST routes with the API profile.
Local registrations resolve configured handles; they do not import client-supplied
module names. The manager compiles each server once and never caches a request's
identity or handler instance.

`Tool[InputType, OutputType]` also supports explicit `input` and `output` attributes.
`McpInvoker` compiles trusted dependency sources before accepting requests. Payload
keys never become arbitrary constructor or handler keyword arguments. Primitive
instances are built through the application container for availability,
authorization and execution.

## Runtime And Limits

HTTP uses native `Response` and `EventStreamResponse`. STDIO uses bounded independent
request tasks and serialized output; shutdown joins owned cleanup. `OwnedStream`
implements the awaited `AsyncClosable` contract, including close-before-first-read.
The process-local event bus coalesces duplicate changes and has finite listener
and buffer capacities. It is not a distributed cross-worker broker.

All configuration fields in `config/mcp.py` read environment factories. Request
bytes and concurrency can share HTTP defaults; origins can share explicit CORS
entries, never CORS wildcards. Protocol-specific environment values take precedence.

Dispatcher list sources, server identity and result-type tables are prepared once.
Tool input validation owns the mutable copy of a request snapshot. Removing a
second copy matters for nested mappings; list-shaped payloads only avoid the extra
root dictionary. The synchronous payload/output helpers still run synchronous
custom schema rules: do not attach blocking I/O rules there. HTTP controller schema
injection uses the separate asynchronous validator.

## URI Matching

Expansion uses the existing RFC 6570 library. Automatic inverses require simple
variables separated by characters excluded from captures (`/`, `?`, `#`, `&`, `;`).
Adjacent captures and ambiguous textual separators require an explicit static or
class `Resource.match(uri)` hook. Every result must expand back to the requested URI;
extra undeclared variables and inconsistent repeated values are rejected.

This rejects previously accepted ambiguous templates during compilation. Supply
an explicit inverse to retain them. Custom inverse complexity remains application
code's responsibility. Regex variable-name checks use ASCII and possessive groups.

## Initialization Policy

Constructors capture configuration, immutable metadata and empty bounded state.
They must not open STDIO, start request tasks or advance streaming producers.
Schema/handler plans and dispatch tables are eager at server compilation. Resource
instances, authentication context, input payloads and stream cleanup remain local
to their invocation. See the [framework audit](../../docs/performance-audit.es.md)
for executed checks, measurements and verification limits.

## Testing

Use `TestCase` from `orionis.test` and create a client with
`client = await self.mcp(ServerType)` inside an async test or `asyncSetUp`.
The helper reuses the runner's booted application; `app=` selects an isolated
container and `config=` overrides client limits. Requests and streams still use
the native codecs, dispatcher and request scopes.

Run these tests with `reactor test`. The client, response assertions and API
reference belong to the [testing package](../../test/docs/README.md#mcp-clients).
