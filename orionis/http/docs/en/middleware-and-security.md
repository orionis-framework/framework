# Middleware and security policies

HTTP middleware receives `Request` and a no-argument continuation. It may return early or modify the controller's response. Attach classes to routes; the kernel may reuse their instances across requests.

```python
from uuid import uuid4
from orionis.http import BaseMiddleware, Request, Response

class RequestIdMiddleware(BaseMiddleware):
    async def handle(self, request: Request, call_next) -> Response:
        request_id = uuid4().hex
        request.state.request_id = request_id
        result = await call_next()
        result.setHeader("X-Request-ID", request_id)
        return result
```

Register with `.middleware(RequestIdMiddleware)`. Do not store the identifier on `self`. Each continuation may be called once: calling `call_next()` twice raises `RuntimeError`. Return a response directly to short-circuit. Use `try/finally` for resources; cancellation must also clean them up.

## Session and CSRF

The web pipeline restores the session, checks CSRF and resolves identity, in that order. GET, HEAD, OPTIONS and TRACE are safe methods for CSRF checks. Other methods require the token in `X-CSRF-Token`, `X-XSRF-Token`, `_csrf` or form `csrf_token`. For JSON use a header; the layer does not search arbitrary JSON for tokens.

`request.csrfToken()` reads the token prepared by middleware. `CSRF_ENABLED` defaults to true; tokens use `CSRF_TOKEN_LENGTH=32` random bytes. `CSRF_SESSION_KEY`, `CSRF_XSRF_COOKIE`, `CSRF_COOKIE_NAME`, `CSRF_COOKIE_SECURE`, `CSRF_COOKIE_SAME_SITE`, `CSRF_COOKIE_PATH` and `CSRF_COOKIE_DOMAIN` customize storage and cookies. The XSRF cookie is script-readable by design; it is separate from the session cookie. Disabling CSRF or applying `public()` to a cookie-credential endpoint removes a required protection.

## Hosts, proxies and CORS

An empty `ALLOWED_HOSTS` accepts every host; configure it when deployment depends on a public hostname. Security middleware rejects CR/LF in headers and multiple Host headers. `TRUSTED_PROXIES` determines which peers may change scheme/IP through forwarded headers; bootstrap trusts localhost. Trust only your proxies so rate limits and URLs do not depend on forged headers.

CORS uses `CORS_ALLOW_ORIGINS`, `CORS_ALLOW_ORIGIN_REGEX`, `CORS_ALLOW_METHODS`, `CORS_ALLOW_HEADERS`, `CORS_EXPOSE_HEADERS`, `CORS_ALLOW_CREDENTIALS` and `CORS_MAX_AGE` (600 seconds). Credentials are disabled by default. Use explicit origins for cookies. CORS is browser policy, not server authentication. WebSocket and MCP read the same bootstrap `CORS_ALLOW_ORIGINS` but apply their own validation rules; MCP rejects wildcards.

## Capacity and rate limiting

`RATE_LIMIT_ENABLED` defaults to false. Once enabled, the initial budget is 100 requests per 60 seconds (`RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW`). The key is the resolved client IP. `RATE_LIMIT_STORE` selects worker-local memory or Redis. `RATE_LIMIT_MAX_KEYS` and `RATE_LIMIT_MAX_EVENTS` bound memory; `RATE_LIMIT_REDIS_PREFIX` and `RATE_LIMIT_REDIS_TIMEOUT` configure Redis. Connection settings share `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB` and `REDIS_PASSWORD`.

Excess requests receive 429 with `Retry-After`; recognized Redis errors receive 503 and a short retry interval. Memory storage is worker-local and does not enforce a global quota. HTTP concurrency admission includes response delivery and rejects excess work instead of building an unbounded queue.

Evidence: [kernel](../../kernel.py), [CSRF](../../layer/web/csrf_token.py), [proxies](../../layer/shared/proxies.py), [rate limiting](../../layer/shared/rate_limit.py), [config](../../../../config/http.py). Tests: [pipeline](../../../../tests/http/test_middleware.py), [security](../../../../tests/http/layer/shared/test_security.py), [CORS](../../../../tests/http/layer/shared/test_cors.py), [CSRF](../../../../tests/http/layer/web/test_csrf_token.py). Identity protection: [Auth](../../../auth/docs/en/README.md).
