# HTTP: from routes to responses

Orionis provides a common HTTP API over ASGI and RSGI. The same controller can receive a normalized request, validate input and return JSON, HTML, a file, a stream or SSE. WebSocket connections use a separate connection API within the same routing system.

You need Python 3.14+, the framework's declared dependencies and a booted application to use facades and container services. Function examples are application code executed when the kernel handles a request. Examples that only construct responses can run without starting a server.

## Recommended path

1. [Request lifecycle and controllers](request-lifecycle.md): services, scopes and asynchronous execution.
2. [Routes, parameters and groups](routing.md): design an API and organize access.
3. [Input and validation](requests-and-validation.md): read metadata and bodies correctly.
4. [Forms and uploads](forms-and-uploads.md): repeated input and temporary resources.
5. [Responses and cookies](responses.md): JSON, views, redirects and downloads.
6. [Streaming and SSE](streaming-and-sse.md): progressive delivery and cleanup.
7. [WebSocket](websockets.md): connections, messages and middleware.
8. [Middleware and security](middleware-and-security.md): CSRF, CORS, proxies and limits.
9. [Default pages and routes](default-responses.md): health, errors and optional authentication.

Continue with [sessions](../../../session/docs/en/README.md), [authentication](../../../auth/docs/en/README.md), [schemas](../../../schemas/docs/en/README.md), [views](../../../view/docs/en/README.md) and [Realtime hubs](../../../realtime/docs/en/README.md).

