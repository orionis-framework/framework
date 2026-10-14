# Native MCP servers

Orionis declares tools, resources and prompts as Python classes and compiles their contract once for HTTP, STDIO and tests. This checkout implements protocol `2026-07-28`, the only value in `SUPPORTED_VERSIONS`; check compatibility with your intended client.

1. [Your first server and typed tools](servers-and-tools.md).
2. [Resources, URI templates and prompts](resources-and-prompts.md).
3. [Content, serialization and metadata](responses-and-content.md).
4. [HTTP, STDIO and configuration](transports-and-configuration.md).
5. [Progress, continuation, subscriptions and extensions](advanced-workflows.md).

Requires Python 3.14+, schemas/msgspec for typed contracts and a booted application for transport registration. Examples using `compile_server` and `McpTestClient(Container(), ServerClass)` work without a server or external data. RFC 6570 expansion uses the declared `uritemplate` dependency; publishing resources does not implicitly grant filesystem access.

Each call has independent context. Descriptive annotations never replace [authentication/authorization](../../../auth/docs/en/README.md). Web endpoints use the [HTTP kernel](../../../http/docs/en/README.md) and handlers use the [container](../../../container/docs/en/README.md).
