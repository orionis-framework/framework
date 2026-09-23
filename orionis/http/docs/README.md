# orionis.http

> Requests, routing, middleware, payload parsing and HTTP responses for ASGI/RSGI applications.

## Table of contents

- [Functional overview](#functional-overview)
- [API reference](#api-reference)
- [Usage examples](#usage-examples)
- [Performance and concurrency considerations](#performance-and-concurrency-considerations)
- [Compatibility notes](#compatibility-notes)

<details>
<summary>API index</summary>

- [UnsupportedMediaTypeException](#api-001)
- [Request](#api-002)
- [Response](#api-003)
- [HTMLResponse](#api-004)
- [PlainTextResponse](#api-005)
- [JSONResponse](#api-006)
- [RedirectResponse](#api-007)
- [StreamingResponse](#api-008)
- [FileResponse](#api-009)
- [ResponseFactory](#api-010)
- [BaseMiddleware](#api-011)
- [BaseController](#api-012)
- [KernelHTTP](#api-013)
- [DefaultResponses](#api-014)
- [LoginController](#api-015)
- [RegisterController](#api-016)
- [IRequest](#api-017)
- [IResponse](#api-018)
- [IKernelHTTP](#api-019)
- [IDefaultResponses](#api-020)
- [validation_response](#api-021)
- [previous_url](#api-022)
- [Interface](#api-023)
- [HTTPStatus](#api-024)
- [WebSocketStatus](#api-025)
- [LoginSchema](#api-026)
- [RegisterSchema](#api-027)
- [HttpResponse](#api-028)
- [`Router`](#api-029)
- [`FluentRoute`](#api-030)
- [`RouteGroup`](#api-031)
- [`RouteID`](#api-032)
- [`RouteCompiler`](#api-033)
- [`RouteCache`](#api-034)
- [`RouteLoader`](#api-035)
- [`RouteResolver`](#api-036)
- [`RouterProvider`](#api-037)
- [`CompiledRoute`](#api-038)
- [`ResolvedRoute`](#api-039)
- [`RouteType`](#api-040)
- [`FallbackRouteAlreadyRegisteredException`](#api-041)
- [`MethodNotAllowed`](#api-042)
- [`RouteNotFound`](#api-043)
- [`normalize_path`](#api-044)
- [`normalize_request_path`](#api-045)
- [`strip_regex_anchors`](#api-046)
- [`flatten_middleware`](#api-047)
- [`is_valid_handler`](#api-048)
- [`parse_action`](#api-049)
- [`RouteAction`](#api-050)
- [`MiddlewareInput`](#api-051)
- [`PARAM_TYPES`](#api-052)
- [`ParamConverter`](#api-053)
- [`Extractor`](#api-054)
- [`BucketEntry`](#api-055)
- [`DepthTable`](#api-056)
- [`IRouter`](#api-057)
- [`IFluentRoute`](#api-058)
- [`IRouteLoader`](#api-059)
- [`IRouteCompiler`](#api-060)
- [`IRouteCache`](#api-061)
- [`IRouteResolver`](#api-062)
- [PayloadTooLargeException](#api-063)
- [BodyStream](#api-064)
- [Headers](#api-065)
- [Cookies](#api-066)
- [QueryParams](#api-067)
- [FormData](#api-068)
- [MediaTypeRegistry](#api-069)
- [BodyParser](#api-070)
- [DEFAULT_MEDIA_TYPES](#api-071)
- [parse_content_type](#api-072)
- [parse_json](#api-073)
- [parse_msgpack](#api-074)
- [parse_urlencoded](#api-075)
- [parse_urlencoded_multi](#api-076)
- [parse_xml](#api-077)
- [parse_text](#api-078)
- [parse_binary](#api-079)
- [UploadedFile](#api-080)
- [MultipartPart](#api-081)
- [complete_in_thread](#api-082)
- [MultipartStreamParser](#api-083)
- [IBodyStream](#api-084)
- [IFormData](#api-085)
- [IMediaTypeRegistry](#api-086)
- [IUploadedFile](#api-087)
- [IMultipartPart](#api-088)
- [IMultipartStreamParser](#api-089)
- [TransportAdapter](#api-090)
- [ASGITransportAdapter](#api-091)
- [RSGITransportAdapter](#api-092)
- [ResponseAdapter](#api-093)
- [ASGIResponseAdapter](#api-094)
- [RSGIResponseAdapter](#api-095)
- [open_file](#api-096)
- [complete_file_read](#api-097)
- [parse_range](#api-098)
- [IBaseMiddleware](#api-099)
- [MemoryRateLimitStore](#api-100)
- [RateLimitMiddleware](#api-101)
- [CORSException](#api-102)
- [CORSMiddleware](#api-103)
- [SecurityMiddleware](#api-104)
- [ProxiesMiddleware](#api-105)
- [UnderMaintenanceMiddleware](#api-106)
- [StartSessionMiddleware](#api-107)
- [CSRFTokenMismatchException](#api-108)
- [CSRFTokenMiddleware](#api-109)

</details>

## Functional overview

`orionis.http` turns ASGI/RSGI input into requests, resolves routes, runs middleware and handlers, and sends typed HTTP responses. It includes body/form/upload parsers, route compilation/cache support and default pages/controllers. It integrates the application container (`orionis.foundation.contracts.application`), authentication, sessions, schema validation, views and background tasks.

The package root exports the following names; other APIs in this reference must be imported from their defining modules:

```python
from orionis.http import (
    BaseMiddleware, FileResponse, HTMLResponse, HttpResponse, JSONResponse,
    NextCallable, PlainTextResponse, RedirectResponse, Request, Response,
    ResponseFactory, StreamingResponse, response,
)
```

`orionis.http.base` exports `BaseController`; `orionis.http.enums` exports `Interface`, `HTTPStatus` and `WebSocketStatus`. The `routes` and `payload` initializers are empty.

### Request lifecycle

1. `KernelHTTP.boot()` loads routes and prepares handlers, middleware, response adapters and application services.
2. `handleASGI()` or `handleRSGI()` opens an application scope and applies transport middleware.
3. The resolver selects route metadata; the kernel creates `BodyStream` and `Request` and registers the request in the scope.
4. Web/API middleware and route middleware run before the handler; the container resolves handler arguments.
5. The kernel handles supported exceptions, applies CORS output headers and sends through the transport adapter; background work is awaited after successful delivery.

### Design decisions

- **Adapters and ABC contracts:** ASGI/RSGI share request/response APIs, while transport-specific methods retain their own signatures.
- **Factory:** `response` is one import-time `ResponseFactory` instance; calls create response objects and support cookie/flash chaining.
- **Fluent builders:** `FluentRoute` and `RouteGroup` mutate registered route objects immediately; group membership is stored as a tuple.
- **Container Singleton:** `RouterProvider` binds `IRouter` to `Router` as a singleton and pins the `Route` facade during boot.
- **Frozen dataclasses:** `CompiledRoute` and `ResolvedRoute` protect field reassignment; nested containers have the exact mutability described in their API entries.
- **Slots and lazy caches:** request, transport and payload classes use `__slots__` and cache selected values; this does not make the returned mappings immutable.
- **Streaming and spooling:** body/upload processing can consume data incrementally and move file content to temporary storage; resource ownership is part of the public API.
- **Per-request continuation:** `_MiddlewarePipeline` keeps traversal state outside shared middleware instances and rejects repeated continuation calls in a layer.

### Source inventory

All 104 Python files, including package initializers, are listed below. Definitions with a leading underscore are internal; public API entries include locally defined methods and selected lifecycle/mapping dunders. Inherited methods are documented with their defining class. The inventory also includes bundled non-Python response resources.

<details>
<summary>Expand the complete file inventory</summary>

| File | Definitions / package exports |
|---|---|
| [`__init__.py`](../__init__.py) | `ResponseFactory`, `response`, `BaseMiddleware`, `NextCallable`, `Request`, `FileResponse`, `HTMLResponse`, `JSONResponse`, `PlainTextResponse`, `RedirectResponse`, `Response`, `StreamingResponse`, `HttpResponse` |
| [`adapters/__init__.py`](../adapters/__init__.py) | No local class/function definitions. |
| [`adapters/request/__init__.py`](../adapters/request/__init__.py) | No local class/function definitions. |
| [`adapters/request/asgi.py`](../adapters/request/asgi.py) | `ASGITransportAdapter` |
| [`adapters/request/contracts/__init__.py`](../adapters/request/contracts/__init__.py) | No local class/function definitions. |
| [`adapters/request/contracts/transport.py`](../adapters/request/contracts/transport.py) | `TransportAdapter` |
| [`adapters/request/rsgi.py`](../adapters/request/rsgi.py) | `RSGITransportAdapter` |
| [`adapters/response/__init__.py`](../adapters/response/__init__.py) | No local class/function definitions. |
| [`adapters/response/asgi.py`](../adapters/response/asgi.py) | `ASGIResponseAdapter` |
| [`adapters/response/contracts/__init__.py`](../adapters/response/contracts/__init__.py) | No local class/function definitions. |
| [`adapters/response/contracts/response.py`](../adapters/response/contracts/response.py) | `ResponseAdapter` |
| [`adapters/response/files.py`](../adapters/response/files.py) | `open_file`, `complete_file_read` |
| [`adapters/response/ranges.py`](../adapters/response/ranges.py) | `parse_range` |
| [`adapters/response/rsgi.py`](../adapters/response/rsgi.py) | `RSGIResponseAdapter` |
| [`base/__init__.py`](../base/__init__.py) | `BaseController` |
| [`base/controller.py`](../base/controller.py) | `BaseController` |
| [`contracts/__init__.py`](../contracts/__init__.py) | No local class/function definitions. |
| [`contracts/kernel.py`](../contracts/kernel.py) | `IKernelHTTP` |
| [`contracts/request.py`](../contracts/request.py) | `IRequest` |
| [`contracts/response.py`](../contracts/response.py) | `IResponse` |
| [`default/__init__.py`](../default/__init__.py) | No local class/function definitions. |
| [`default/contracts/__init__.py`](../default/contracts/__init__.py) | No local class/function definitions. |
| [`default/contracts/responses.py`](../default/contracts/responses.py) | `IDefaultResponses` |
| [`default/controllers/__init__.py`](../default/controllers/__init__.py) | No local class/function definitions. |
| [`default/controllers/login_controller.py`](../default/controllers/login_controller.py) | `LoginController` |
| [`default/controllers/register_controller.py`](../default/controllers/register_controller.py) | `RegisterController` |
| [`default/responses.py`](../default/responses.py) | `_validate_status_code`, `_compile_placeholders`, `DefaultResponses` |
| [`default/schemas/__init__.py`](../default/schemas/__init__.py) | No local class/function definitions. |
| [`default/schemas/login.py`](../default/schemas/login.py) | `LoginSchema` |
| [`default/schemas/register.py`](../default/schemas/register.py) | `RegisterSchema` |
| [`enums/__init__.py`](../enums/__init__.py) | `Interface`, `HTTPStatus`, `WebSocketStatus` |
| [`enums/interfaces.py`](../enums/interfaces.py) | `Interface` |
| [`enums/status.py`](../enums/status.py) | `HTTPStatus`, `WebSocketStatus` |
| [`factory.py`](../factory.py) | `ResponseFactory` |
| [`kernel.py`](../kernel.py) | `_MiddlewarePipeline`, `KernelHTTP` |
| [`layer/__init__.py`](../layer/__init__.py) | No local class/function definitions. |
| [`layer/api/__init__.py`](../layer/api/__init__.py) | No local class/function definitions. |
| [`layer/contracts/__init__.py`](../layer/contracts/__init__.py) | No local class/function definitions. |
| [`layer/contracts/middleware.py`](../layer/contracts/middleware.py) | `IBaseMiddleware` |
| [`layer/shared/__init__.py`](../layer/shared/__init__.py) | No local class/function definitions. |
| [`layer/shared/cors.py`](../layer/shared/cors.py) | `CORSException`, `CORSMiddleware` |
| [`layer/shared/maintenance.py`](../layer/shared/maintenance.py) | `UnderMaintenanceMiddleware` |
| [`layer/shared/proxies.py`](../layer/shared/proxies.py) | `ProxiesMiddleware` |
| [`layer/shared/rate_limit.py`](../layer/shared/rate_limit.py) | `RateLimitMiddleware` |
| [`layer/shared/security.py`](../layer/shared/security.py) | `SecurityMiddleware` |
| [`layer/store/__init__.py`](../layer/store/__init__.py) | No local class/function definitions. |
| [`layer/store/memory_rate_limit.py`](../layer/store/memory_rate_limit.py) | `_RateLimitBucket`, `MemoryRateLimitStore` |
| [`layer/web/__init__.py`](../layer/web/__init__.py) | No local class/function definitions. |
| [`layer/web/csrf_token.py`](../layer/web/csrf_token.py) | `CSRFTokenMiddleware` |
| [`layer/web/exceptions.py`](../layer/web/exceptions.py) | `CSRFTokenMismatchException` |
| [`layer/web/start_session.py`](../layer/web/start_session.py) | `StartSessionMiddleware` |
| [`middleware.py`](../middleware.py) | `BaseMiddleware` |
| [`payload/__init__.py`](../payload/__init__.py) | No local class/function definitions. |
| [`payload/body.py`](../payload/body.py) | `PayloadTooLargeException`, `BodyStream` |
| [`payload/contracts/__init__.py`](../payload/contracts/__init__.py) | No local class/function definitions. |
| [`payload/contracts/body_stream.py`](../payload/contracts/body_stream.py) | `IBodyStream` |
| [`payload/contracts/form_data.py`](../payload/contracts/form_data.py) | `IFormData` |
| [`payload/contracts/media_types.py`](../payload/contracts/media_types.py) | `IMediaTypeRegistry` |
| [`payload/contracts/part.py`](../payload/contracts/part.py) | `IMultipartPart` |
| [`payload/contracts/stream_parser.py`](../payload/contracts/stream_parser.py) | `IMultipartStreamParser` |
| [`payload/contracts/uploaded_file.py`](../payload/contracts/uploaded_file.py) | `IUploadedFile` |
| [`payload/estructures/__init__.py`](../payload/estructures/__init__.py) | No local class/function definitions. |
| [`payload/estructures/cookies.py`](../payload/estructures/cookies.py) | `Cookies` |
| [`payload/estructures/headers.py`](../payload/estructures/headers.py) | `Headers` |
| [`payload/estructures/query_params.py`](../payload/estructures/query_params.py) | `QueryParams` |
| [`payload/form_data.py`](../payload/form_data.py) | `FormData` |
| [`payload/media_types.py`](../payload/media_types.py) | `MediaTypeRegistry` |
| [`payload/parsers.py`](../payload/parsers.py) | `_split_header_parameters`, `parse_content_type`, `parse_json`, `parse_msgpack`, `parse_urlencoded`, `parse_urlencoded_multi`, `parse_xml`, `parse_text`, `parse_binary` |
| [`payload/part.py`](../payload/part.py) | `MultipartPart` |
| [`payload/stream_parser.py`](../payload/stream_parser.py) | `complete_in_thread`, `MultipartStreamParser` |
| [`payload/uploaded_file.py`](../payload/uploaded_file.py) | `UploadedFile` |
| [`request.py`](../request.py) | `UnsupportedMediaTypeException`, `Request` |
| [`responses.py`](../responses.py) | `Response`, `HTMLResponse`, `PlainTextResponse`, `JSONResponse`, `RedirectResponse`, `StreamingResponse`, `FileResponse` |
| [`routes/__init__.py`](../routes/__init__.py) | No local class/function definitions. |
| [`routes/contracts/__init__.py`](../routes/contracts/__init__.py) | No local class/function definitions. |
| [`routes/contracts/fluent.py`](../routes/contracts/fluent.py) | `IFluentRoute` |
| [`routes/contracts/loader.py`](../routes/contracts/loader.py) | `IRouteLoader` |
| [`routes/contracts/route_cache.py`](../routes/contracts/route_cache.py) | `IRouteCache` |
| [`routes/contracts/route_compiler.py`](../routes/contracts/route_compiler.py) | `IRouteCompiler` |
| [`routes/contracts/route_resolver.py`](../routes/contracts/route_resolver.py) | `IRouteResolver` |
| [`routes/contracts/router.py`](../routes/contracts/router.py) | `IRouter` |
| [`routes/entities/__init__.py`](../routes/entities/__init__.py) | No local class/function definitions. |
| [`routes/entities/compiled_route.py`](../routes/entities/compiled_route.py) | `CompiledRoute` |
| [`routes/entities/resolved_route.py`](../routes/entities/resolved_route.py) | `ResolvedRoute` |
| [`routes/enums/__init__.py`](../routes/enums/__init__.py) | No local class/function definitions. |
| [`routes/enums/route_types.py`](../routes/enums/route_types.py) | `RouteType` |
| [`routes/exceptions/__init__.py`](../routes/exceptions/__init__.py) | No local class/function definitions. |
| [`routes/exceptions/fallback_route_already_registered.py`](../routes/exceptions/fallback_route_already_registered.py) | `FallbackRouteAlreadyRegisteredException` |
| [`routes/exceptions/method_not_allowed.py`](../routes/exceptions/method_not_allowed.py) | `MethodNotAllowed` |
| [`routes/exceptions/route_not_found.py`](../routes/exceptions/route_not_found.py) | `RouteNotFound` |
| [`routes/fluent.py`](../routes/fluent.py) | `FluentRoute` |
| [`routes/functions.py`](../routes/functions.py) | `normalize_path`, `normalize_request_path`, `strip_regex_anchors`, `flatten_middleware`, `_middleware_key`, `is_valid_handler`, `parse_action` |
| [`routes/group.py`](../routes/group.py) | `RouteGroup` |
| [`routes/loader.py`](../routes/loader.py) | `RouteLoader` |
| [`routes/params_types.py`](../routes/params_types.py) | No local class/function definitions. |
| [`routes/provider.py`](../routes/provider.py) | `RouterProvider` |
| [`routes/route_cache.py`](../routes/route_cache.py) | `RouteCache` |
| [`routes/route_compiler.py`](../routes/route_compiler.py) | `_validate_literal`, `_action_name`, `_register_name`, `RouteCompiler` |
| [`routes/route_id.py`](../routes/route_id.py) | `RouteID` |
| [`routes/route_resolver.py`](../routes/route_resolver.py) | `_DepthBucket`, `_PrefixIndex`, `_select_bucket`, `_path_allowed_for_method`, `_build_extractors`, `_build_matching_bucket`, `_build_depth_bucket`, `_build_overlapping_index`, `_extract_result`, `RouteResolver`, `DepthTable` |
| [`routes/router.py`](../routes/router.py) | `Router` |
| [`routes/types.py`](../routes/types.py) | `RouteAction`, `MiddlewareInput` |
| [`types.py`](../types.py) | `HttpResponse` |
| [`validation.py`](../validation.py) | `_url_origin`, `_is_local_reference`, `validation_response`, `previous_url` |
| [`default/assets/favicon.ico`](../default/assets/favicon.ico) | Bundled response asset/template. |
| [`default/assets/robots.txt`](../default/assets/robots.txt) | Bundled response asset/template. |
| [`default/pages/down.html`](../default/pages/down.html) | Bundled response asset/template. |
| [`default/pages/error.html`](../default/pages/error.html) | Bundled response asset/template. |
| [`default/pages/exception.html`](../default/pages/exception.html) | Bundled response asset/template. |
| [`default/pages/up.html`](../default/pages/up.html) | Bundled response asset/template. |

</details>

### Internal dependencies

Direct imports outside `orionis.http` are listed here, including imports under `TYPE_CHECKING` and lazy imports. `default/controllers/register_controller.py` also directly imports the application-specific `app.models.user.User`.

<details>
<summary>Exact Orionis module names</summary>

- `orionis.auth.contracts.manager`
- `orionis.auth.middleware.authenticate`
- `orionis.auth.middleware.guest`
- `orionis.auth.middleware.resolve_identity`
- `orionis.background.task`
- `orionis.cache.contracts.file_based_cache`
- `orionis.cache.file_based_cache`
- `orionis.console.output.http_request`
- `orionis.container.providers.service_provider`
- `orionis.failure.contracts.catch`
- `orionis.failure.enums.kernel_type`
- `orionis.foundation.config.http.entitites.cors`
- `orionis.foundation.config.http.entitites.csrf`
- `orionis.foundation.config.http.entitites.proxies`
- `orionis.foundation.config.http.entitites.rate_limit`
- `orionis.foundation.config.http.entitites.security`
- `orionis.foundation.contracts.application`
- `orionis.foundation.contracts.directory`
- `orionis.foundation.directory`
- `orionis.metadata`
- `orionis.schemas`
- `orionis.schemas.constraints`
- `orionis.schemas.exceptions.validation`
- `orionis.schemas.fields`
- `orionis.schemas.metadata`
- `orionis.session.contracts.session`
- `orionis.session.flash`
- `orionis.session.manager`
- `orionis.support.facades`
- `orionis.support.facades.datetime`
- `orionis.support.facades.router`
- `orionis.support.facades.view`
- `orionis.support.formatter.exceptions.parser`
- `orionis.support.patterns.final.meta`
- `orionis.view.pending`

</details>

## API reference

Signature blocks are declarations copied from source, not standalone execution examples. They preserve annotations, defaults, decorators, casing and even source discrepancies. `self`/`cls` refer to the bound instance/class and are not additional caller arguments; constructor `None` annotations describe `__init__`, not the object produced by class construction. Properties are read as attributes. Async-generator methods yield items; coroutine methods must be awaited. Each entry explains observable behavior, parameters, results, relevant errors and state/I/O effects. Abstract contracts link parameter meanings to their concrete counterparts without claiming that a docstring enforces implementation behavior.

Exceptions from supplied callables, application services, filesystem operations and transport implementations can propagate where not caught locally; this reference does not invent a closed exception set for those collaborators. Unspecified guarantees are marked with the required literal warning in both languages.
<a id="api-001"></a>

### UnsupportedMediaTypeException

[`orionis.http.request.UnsupportedMediaTypeException`](../request.py)

```python
class UnsupportedMediaTypeException(Exception):
```

Exception subclass raised by Request MIME checks; no custom constructor or methods.

<a id="api-002"></a>

### Request

[`orionis.http.request.Request`](../request.py)

```python
class Request(IRequest):
```

Transport-independent request implementing IRequest. Properties and decoded data are cached per instance; mutable results are not defensive copies. The class and its contract declare __slots__, but cached dictionaries and state remain mutable. Read/stream ownership follows the injected IBodyStream.

```python
def __init__(
    self,
    interface: Interface,
    adapter: TransportAdapter,
    body_stream: IBodyStream,
    *,
    registry: MediaTypeRegistry | None = None,
    params: Mapping[str, Any] | None = None,
) -> None:
```

Retains adapter scope and body reader, initializes lazy caches, and copies path parameters. Returns None. Invalid interface values raise ValueError during Interface conversion; adapter failures propagate.

| Parameter | Type | Meaning |
|---|---|---|
| `interface` | `Interface` | Transport interface. |
| `adapter` | `TransportAdapter` | Transport adapter supplying the scope and headers. |
| `body_stream` | `IBodyStream` | Body reader supplied by the caller. |
| `registry` | `MediaTypeRegistry \| None` | MIME parser registry; None selects DEFAULT_MEDIA_TYPES. |
| `params` | `Mapping[str, Any] \| None` | Path parameters, copied into an internal dict when nonempty. |

Declared return type: `None`.

```python
@property
def method(self) -> str:
```

Returns the cached scope["method"]; missing method raises KeyError.

Declared return type: `str`.

```python
@property
def scheme(self) -> str:
```

Returns and caches scope scheme, default "http".

Declared return type: `str`.

```python
@property
def path(self) -> str:
```

Returns and caches scope path, default "/".

Declared return type: `str`.

```python
@property
def httpVersion(self) -> str:
```

Returns and caches http_version, default "1.1".

Declared return type: `str`.

```python
@property
def interface(self) -> Interface:
```

Returns the normalized Interface enum.

Declared return type: `Interface`.

```python
@property
def url(self) -> str:
```

Lazily builds the URL from scheme, Host (or server), path and query. ASGI without Host/server returns a relative path; RSGI reads required scope keys directly and can raise KeyError.

Declared return type: `str`.

```python
@property
def baseUrl(self) -> str:
```

Lazily builds the origin; ASGI appends root_path and uses localhost if Host/server is absent. RSGI uses Host or server without root_path; missing required RSGI keys raise KeyError.

Declared return type: `str`.

```python
@property
def headers(self) -> Headers:
```

Returns the lazily cached adapter Headers object, without copying.

Declared return type: `Headers`.

```python
@property
def queryParams(self) -> QueryParams:
```

Lazily parses query_string with QueryParams; ASGI bytes use Latin-1. RSGI expects a string in scope["query_string"].

Declared return type: `QueryParams`.

```python
@property
def cookies(self) -> Cookies:
```

Lazily parses the Cookie header into Cookies.

Declared return type: `Cookies`.

```python
@property
def ip(self) -> str | None:
```

Returns client[0] as str for list/tuple clients, otherwise str(client), or None; caches non-None results.

Declared return type: `str | None`.

```python
@property
def port(self) -> int | None:
```

Returns scope.get("port") and caches non-None results; it does not extract the port from a raw ASGI client tuple.

Declared return type: `int | None`.

```python
@property
def forwarded(self) -> dict[str, Any]:
```

Caches and returns the forwarded mapping from scope, or an empty dict.

Declared return type: `dict[str, Any]`.

```python
@property
def userAgent(self) -> str | None:
```

Returns the user-agent header or None.

Declared return type: `str | None`.

```python
@property
def authorization(self) -> str | None:
```

Returns the authorization header or None.

Declared return type: `str | None`.

```python
@property
def bearerToken(self) -> str | None:
```

Returns a stripped token only for exactly one Authorization header with a case-insensitive "bearer " prefix; otherwise None.

Declared return type: `str | None`.

```python
@property
def apiKey(self) -> str | None:
```

Returns x-api-key or None.

Declared return type: `str | None`.

```python
@property
def accept(self) -> str | None:
```

Returns Accept or None.

Declared return type: `str | None`.

```python
@property
def state(self) -> SimpleNamespace:
```

Creates a SimpleNamespace on first access and returns the mutable object.

Declared return type: `SimpleNamespace`.

```python
@property
def scope(self) -> dict[str, Any]:
```

Returns the underlying scope dict by reference.

Declared return type: `dict[str, Any]`.

```python
async def stream(self) -> AsyncGenerator[bytes]:
```

Yields body-stream chunks; consumes the underlying stream and propagates its state, size-limit and transport errors.

Declared return type: `AsyncGenerator[bytes]`.

```python
async def body(self) -> bytes:
```

Awaits body_stream.read() and returns bytes; propagates BodyStream/transport errors.

Declared return type: `bytes`.

```python
async def raw(self) -> bytes:
```

Alias in behavior for body(): reads through the same body reader.

Declared return type: `bytes`.

```python
async def text(self) -> str:
```

Reads all bytes and decodes UTF-8 strictly; UnicodeDecodeError and body-reader errors propagate.

Declared return type: `str`.

```python
async def json(self) -> object:
```

Caches and returns the decoded JSON value as object: dict, list, str, int, float, bool or None. Accepts application/json and media types ending in +json. Raises UnsupportedMediaTypeException for other types, ValueError for empty or invalid JSON; body-reader errors propagate.

Declared return type: `object`.

```python
async def xml(self) -> XMLElement:
```

Reads the body and delegates to `parse_xml` without a Content-Type check. Propagates `xml.etree.ElementTree.ParseError` for malformed XML, `defusedxml.common.EntitiesForbidden` for internal or external entity declarations, and body-reader errors. `EntitiesForbidden` belongs to the `DefusedXmlException` family. DTDs without entity declarations are allowed; external resources are not resolved.

Declared return type: `XMLElement`.

```python
async def msgpack(self) -> object:
```

Reads and delegates to parse_msgpack without a MIME or mapping-shape check. Returns the decoded MessagePack value as object, including maps, arrays, scalars, binary data, extension values or None. Invalid MessagePack raises msgspec.DecodeError; body-reader errors propagate.

Declared return type: `object`.

```python
async def formUrlEncoded(self) -> dict[str, Any]:
```

Caches a URL-encoded dict using parse_urlencoded (last repeated value). Wrong Content-Type raises UnsupportedMediaTypeException; decoder/body-reader errors propagate.

Declared return type: `dict[str, Any]`.

```python
async def form(self) -> FormData:
```

Streams multipart/form-data through MultipartStreamParser and caches FormData. Wrong MIME raises UnsupportedMediaTypeException; missing boundary raises ValueError. Parser limits, temporary-file I/O and transport errors propagate; returned uploads require closing.

Declared return type: `FormData`.

```python
async def payload(self) -> object:
```

Returns raw bytes for missing/unregistered MIME, FormData for multipart, otherwise the synchronous registry parser result. Consumes the body; parser and body-reader exceptions propagate.

Declared return type: `object`.

```python
async def data(self) -> dict[str, Any]:
```

Caches a dict for exactly application/json, application/x-www-form-urlencoded, multipart/form-data or application/msgpack. Decoded JSON/MessagePack values must be mappings (TypeError otherwise); empty bodies or JSON/MessagePack decoding failures raise ValueError. Repeated form values become lists; multipart values can include UploadedFile. Other MIME values, including +json, raise UnsupportedMediaTypeException. Multipart parsing can raise ValueError; other body/parser errors propagate.

Declared return type: `dict[str, Any]`.

```python
def wantsJson(self) -> bool:
```

Tests whether lowercase Accept contains application/json or +json; no quality-factor negotiation.

Declared return type: `bool`.

```python
def wantsHtml(self) -> bool:
```

Tests for text/html or */* in lowercase Accept.

Declared return type: `bool`.

```python
def wantsXml(self) -> bool:
```

Tests for application/xml or text/xml in lowercase Accept.

Declared return type: `bool`.

```python
def accepts(self, mime: str) -> bool:
```

Returns whether mime.lower() is a substring of lowercase Accept; does not implement wildcard negotiation.

| Parameter | Type | Meaning |
|---|---|---|
| `mime` | `str` | MIME string to search for in the lowercased Accept header. |

Declared return type: `bool`.

```python
def isAjax(self) -> bool:
```

Tests exact equality of X-Requested-With with "XMLHttpRequest".

Declared return type: `bool`.

```python
def routeParam(self, key: str) -> object:
```

Returns the named route parameter or None.

| Parameter | Type | Meaning |
|---|---|---|
| `key` | `str` | Header, cookie, flash or lookup key, as indicated by the method. |

Declared return type: `object`.

```python
def routeParams(self) -> dict[str, Any]:
```

Returns the internal mutable parameter dict, creating an empty dict when needed.

Declared return type: `dict[str, Any]`.

```python
def csrfToken(self) -> str | None:
```

Returns state.csrf_token if present, otherwise None. Also exposed as the csrf_token property.

Declared return type: `str | None`.

The following alias is also public:

```python
csrf_token = property(csrfToken)
```

<a id="api-003"></a>

### Response

[`orionis.http.responses.Response`](../responses.py)

```python
class Response(IResponse):
```

Mutable response implementing IResponse. Common response parameters are described at each signature. Header lookups ignore name case. Set-Cookie may occur multiple times. No network I/O occurs until a transport adapter sends the response.

```python
    charset: ClassVar[str] = "utf-8"
```

```python
def __init__( # NOSONAR
    self,
    content: Any = None,
    status_code: HTTPStatus | int = 200,
    headers: Mapping[str, str] | None = None,
    media_type: str | None = None,
    background: BackgroundTask | None = None,
) -> None:
```

Stores status, headers and background task; renders ordinary content immediately, retaining async iterables as streams. TypeError: non-int status, truthy non-mapping headers, or invalid background; ValueError: status outside 100–599. Rendering errors propagate. The bare class does not create Content-Type or Content-Length headers.

| Parameter | Type | Meaning |
|---|---|---|
| `content` | `Any` | Body or value to render; interpretation depends on the response class. |
| `status_code` | `HTTPStatus \| int` | HTTP status code; the response base validates integer values from 100 to 599. |
| `headers` | `Mapping[str, str] \| None` | Initial response headers, with names stored in lowercase. |
| `media_type` | `str \| None` | Response MIME type. |
| `background` | `BackgroundTask \| None` | BackgroundTask to await when runBackground() is called. |

Declared return type: `None`.

```python
def render(self, content: Any) -> bytes:
```

Returns b"" for None, preserves bytes, copies bytearray/memoryview, encodes str with self.charset (default utf-8), and otherwise encodes str(content) with that charset. Conversion/encoding exceptions propagate; does not replace the stored body.

| Parameter | Type | Meaning |
|---|---|---|
| `content` | `Any` | Body or value to render; interpretation depends on the response class. |

Declared return type: `bytes`.

```python
def addHeader(self, key: str, value: str) -> None:
```

Appends value under key.lower(); mutates headers and preserves duplicate values. Returns None.

| Parameter | Type | Meaning |
|---|---|---|
| `key` | `str` | Header, cookie, flash or lookup key, as indicated by the method. |
| `value` | `str` | Value associated with key. |

Declared return type: `None`.

```python
def setHeader(self, key: str, value: str) -> None:
```

Replaces all values under key.lower() with one value. Returns None.

| Parameter | Type | Meaning |
|---|---|---|
| `key` | `str` | Header, cookie, flash or lookup key, as indicated by the method. |
| `value` | `str` | Value associated with key. |

Declared return type: `None`.

```python
def getHeader(self, key: str) -> list[str] | None:
```

Returns the internal value list or None; callers can mutate that list.

| Parameter | Type | Meaning |
|---|---|---|
| `key` | `str` | Header, cookie, flash or lookup key, as indicated by the method. |

Declared return type: `list[str] | None`.

```python
def hasHeader(self, key: str) -> bool:
```

Returns whether key.lower() is stored.

| Parameter | Type | Meaning |
|---|---|---|
| `key` | `str` | Header, cookie, flash or lookup key, as indicated by the method. |

Declared return type: `bool`.

```python
def removeHeader(self, key: str) -> None:
```

Removes key.lower() if present; missing keys are ignored. Returns None.

| Parameter | Type | Meaning |
|---|---|---|
| `key` | `str` | Header, cookie, flash or lookup key, as indicated by the method. |

Declared return type: `None`.

```python
def getRawHeaders(self) -> list[tuple[bytes, bytes]]:
```

Returns a new flattened list of Latin-1 byte pairs; UnicodeEncodeError for unencodable names/values.

Declared return type: `list[tuple[bytes, bytes]]`.

```python
def getStringHeaders(self) -> list[tuple[str, str]]:
```

Returns a new flattened list of string header pairs, preserving duplicate values.

Declared return type: `list[tuple[str, str]]`.

```python
def setCookie( # NOSONAR
    self,
    key: str,
    value: str = "",
    *,
    max_age: int | None = None,
    expires: datetime | str | int | None = None,
    path: str | None = "/",
    domain: str | None = None,
    secure: bool = False,
    http_only: bool = False,
    same_site: Literal["lax", "strict", "none"] | None = "lax",
    partitioned: bool = False,
) -> None:
```

Appends a Set-Cookie header via SimpleCookie, percent-encoding the value. Naive datetimes are treated as UTC. ValueError for invalid same_site or "none" without secure=True; cookie-name and encoding/type errors propagate. Returns None.

| Parameter | Type | Meaning |
|---|---|---|
| `key` | `str` | Header, cookie, flash or lookup key, as indicated by the method. |
| `value` | `str` | Value associated with key. |
| `max_age` | `int \| None` | Cookie lifetime in seconds; None omits Max-Age. |
| `expires` | `datetime \| str \| int \| None` | Cookie expiration; datetimes are normalized to UTC, other values are stringified. |
| `path` | `str \| None` | Filesystem path for file responses; cookie URL path for cookie methods. |
| `domain` | `str \| None` | Cookie domain; None omits the attribute. |
| `secure` | `bool` | Set the Secure cookie attribute. |
| `http_only` | `bool` | Set the HttpOnly cookie attribute. |
| `same_site` | `Literal["lax", "strict", "none"] \| None` | SameSite policy; None omits it, while the string "none" requires secure=True. |
| `partitioned` | `bool` | Set the Partitioned cookie attribute. |

Declared return type: `None`.

```python
def deleteCookie(
    self,
    key: str,
    *,
    path: str = "/",
    domain: str | None = None,
) -> None:
```

Appends an expired cookie (Max-Age=0, 1970-01-01 UTC) for key/path/domain; returns None and propagates setCookie errors.

| Parameter | Type | Meaning |
|---|---|---|
| `key` | `str` | Header, cookie, flash or lookup key, as indicated by the method. |
| `path` | `str` | Filesystem path for file responses; cookie URL path for cookie methods. |
| `domain` | `str \| None` | Cookie domain; None omits the attribute. |

Declared return type: `None`.

```python
def withCookie( # NOSONAR
    self,
    key: str,
    value: str = "",
    *,
    max_age: int | None = None,
    expires: datetime | str | int | None = None,
    path: str | None = "/",
    domain: str | None = None,
    secure: bool = False,
    http_only: bool = False,
    same_site: Literal["lax", "strict", "none"] | None = "lax",
    partitioned: bool = False,
) -> Self:
```

Calls setCookie and returns this same response; same errors and mutation.

| Parameter | Type | Meaning |
|---|---|---|
| `key` | `str` | Header, cookie, flash or lookup key, as indicated by the method. |
| `value` | `str` | Value associated with key. |
| `max_age` | `int \| None` | Cookie lifetime in seconds; None omits Max-Age. |
| `expires` | `datetime \| str \| int \| None` | Cookie expiration; datetimes are normalized to UTC, other values are stringified. |
| `path` | `str \| None` | Filesystem path for file responses; cookie URL path for cookie methods. |
| `domain` | `str \| None` | Cookie domain; None omits the attribute. |
| `secure` | `bool` | Set the Secure cookie attribute. |
| `http_only` | `bool` | Set the HttpOnly cookie attribute. |
| `same_site` | `Literal["lax", "strict", "none"] \| None` | SameSite policy; None omits it, while the string "none" requires secure=True. |
| `partitioned` | `bool` | Set the Partitioned cookie attribute. |

Declared return type: `Self`.

```python
def withCookies(
    self,
    cookies: Mapping[str, str | Mapping[str, Any]],
) -> Self:
```

Calls setCookie for each mapping entry and returns self. Errors propagate; earlier cookies remain attached if a later entry fails.

| Parameter | Type | Meaning |
|---|---|---|
| `cookies` | `Mapping[str, str \| Mapping[str, Any]]` | Cookie names mapped to string values or keyword-option mappings for setCookie(). |

Declared return type: `Self`.

```python
def withoutCookie(
    self,
    key: str,
    *,
    path: str = "/",
    domain: str | None = None,
) -> Self:
```

Calls deleteCookie and returns self; same errors and mutation.

| Parameter | Type | Meaning |
|---|---|---|
| `key` | `str` | Header, cookie, flash or lookup key, as indicated by the method. |
| `path` | `str` | Filesystem path for file responses; cookie URL path for cookie methods. |
| `domain` | `str \| None` | Cookie domain; None omits the attribute. |

Declared return type: `Self`.

```python
def withFlash(self, key: str, value: Any = None) -> Self:
```

Queues key/value in the response flash dict and returns self. Session persistence happens later in StartSessionMiddleware.

| Parameter | Type | Meaning |
|---|---|---|
| `key` | `str` | Header, cookie, flash or lookup key, as indicated by the method. |
| `value` | `Any` | Value associated with key. |

Declared return type: `Self`.

```python
def withInput(self, values: Mapping[str, Any]) -> Self:
```

Merges filtered old input into the flash bag and returns self. Excludes top-level _csrf, csrf_token, current_password, new_password, password and password_confirmation; does not recursively filter nested values.

| Parameter | Type | Meaning |
|---|---|---|
| `values` | `Mapping[str, Any]` | Submitted input mapping to queue as old input. |

Declared return type: `Self`.

```python
def withErrors(self, errors: Mapping[str, Any] | Exception) -> Self:
```

Normalizes field errors into message lists, merges the flash error bag and returns self. TypeError when a non-mapping exception provides neither a mapping errors attribute nor failure data.

| Parameter | Type | Meaning |
|---|---|---|
| `errors` | `Mapping[str, Any] \| Exception` | Field-message mapping or exception accepted by normalize_errors(). |

Declared return type: `Self`.

```python
def getFlashData(self) -> dict[str, Any] | None:
```

Returns the internal flash dict or None without copying.

Declared return type: `dict[str, Any] | None`.

```python
def getBody(self) -> bytes | None:
```

Returns stored bytes or None for streaming content.

Declared return type: `bytes | None`.

```python
def getStream(self) -> AsyncIterable[bytes] | None:
```

Returns the stored async iterable or None.

Declared return type: `AsyncIterable[bytes] | None`.

```python
def hasStream(self) -> bool:
```

Returns whether a stream is stored.

Declared return type: `bool`.

```python
async def runBackground(self) -> None:
```

Awaits the stored background task if present; returns None and propagates task failures. Repeated calls execute it again.

Declared return type: `None`.

```python
def getStatusCode(self) -> int:
```

Returns status_code.

Declared return type: `int`.

```python
def getMediaType(self) -> str | None:
```

Returns media_type.

Declared return type: `str | None`.

<a id="api-004"></a>

### HTMLResponse

[`orionis.http.responses.HTMLResponse`](../responses.py)

```python
class HTMLResponse(Response):
```

Inherits Response; sets media_type='text/html' and Content-Type with UTF-8 unless already supplied. Other methods and exceptions are inherited.

```python
def __init__(
    self,
    content: str | bytes = "",
    status_code: HTTPStatus | int = 200,
    headers: Mapping[str, str] | None = None,
    background: BackgroundTask | None = None,
) -> None:
```

Renders content immediately and returns None; inherits Response validation and rendering errors.

| Parameter | Type | Meaning |
|---|---|---|
| `content` | `str \| bytes` | Body or value to render; interpretation depends on the response class. |
| `status_code` | `HTTPStatus \| int` | HTTP status code; the response base validates integer values from 100 to 599. |
| `headers` | `Mapping[str, str] \| None` | Initial response headers, with names stored in lowercase. |
| `background` | `BackgroundTask \| None` | BackgroundTask to await when runBackground() is called. |

Declared return type: `None`.

<a id="api-005"></a>

### PlainTextResponse

[`orionis.http.responses.PlainTextResponse`](../responses.py)

```python
class PlainTextResponse(Response):
```

Inherits Response; sets media_type='text/plain' and Content-Type with UTF-8 unless already supplied. Other methods and exceptions are inherited.

```python
def __init__(
    self,
    content: str | bytes = "",
    status_code: HTTPStatus | int = 200,
    headers: Mapping[str, str] | None = None,
    background: BackgroundTask | None = None,
) -> None:
```

Renders content immediately and returns None; inherits Response validation and rendering errors.

| Parameter | Type | Meaning |
|---|---|---|
| `content` | `str \| bytes` | Body or value to render; interpretation depends on the response class. |
| `status_code` | `HTTPStatus \| int` | HTTP status code; the response base validates integer values from 100 to 599. |
| `headers` | `Mapping[str, str] \| None` | Initial response headers, with names stored in lowercase. |
| `background` | `BackgroundTask \| None` | BackgroundTask to await when runBackground() is called. |

Declared return type: `None`.

<a id="api-006"></a>

### JSONResponse

[`orionis.http.responses.JSONResponse`](../responses.py)

```python
class JSONResponse(Response):
```

Response with application/json; default output uses msgspec.json.encode. Formatting options can switch encoding to json.dumps. The private default hook converts datetime/date/time to ISO text, Decimal/UUID to strings, Enum to its value, and sets to lists when the encoder delegates to it.

```python
def __init__(
    self,
    content: Any,
    status_code: HTTPStatus | int = 200,
    headers: Mapping[str, str] | None = None,
    background: BackgroundTask | None = None,
    *,
    indent: int | None = None,
    ensure_ascii: bool = False,
    separators: tuple[str, str] | None = None,
    default: Any | None = None,
) -> None:
```

Stores JSON options before Response renders content; adds Content-Type if absent. Inherits Response validation and JSON encoding errors.

| Parameter | Type | Meaning |
|---|---|---|
| `content` | `Any` | Body or value to render; interpretation depends on the response class. |
| `status_code` | `HTTPStatus \| int` | HTTP status code; the response base validates integer values from 100 to 599. |
| `headers` | `Mapping[str, str] \| None` | Initial response headers, with names stored in lowercase. |
| `background` | `BackgroundTask \| None` | BackgroundTask to await when runBackground() is called. |
| `indent` | `int \| None` | JSON indentation; None enables compact output. |
| `ensure_ascii` | `bool` | Escape non-ASCII characters through the standard JSON encoder when true. |
| `separators` | `tuple[str, str] \| None` | JSON item/key separator pair; forwarded to json.dumps on its path. |
| `default` | `Any \| None` | Custom encoder hook; None selects JSONResponse._defaultEncoder. |

Declared return type: `None`.

```python
def render(self, content: Any) -> bytes:
```

Returns JSON bytes. Uses msgspec only when indent=None, ensure_ascii=False and separators=None, otherwise json.dumps; unsupported objects raise TypeError through the default hook, and encoder/hook errors propagate. No stored-body mutation.

| Parameter | Type | Meaning |
|---|---|---|
| `content` | `Any` | Body or value to render; interpretation depends on the response class. |

Declared return type: `bytes`.

<a id="api-007"></a>

### RedirectResponse

[`orionis.http.responses.RedirectResponse`](../responses.py)

```python
class RedirectResponse(Response):
```

Response carrying a text body and Location header; inherits all response methods.

```python
def __init__(
    self,
    url: str,
    status_code: HTTPStatus | int = 302,
    headers: Mapping[str, str] | None = None,
    background: BackgroundTask | None = None,
) -> None:
```

Requires str url (TypeError otherwise) and a 300–399 status (ValueError outside the range). Sets Location to url and body to "Redirecting to {url}"; Response errors also propagate. Does not check target origin.

| Parameter | Type | Meaning |
|---|---|---|
| `url` | `str` | Redirect target string. |
| `status_code` | `HTTPStatus \| int` | HTTP status code; the response base validates integer values from 100 to 599. |
| `headers` | `Mapping[str, str] \| None` | Initial response headers, with names stored in lowercase. |
| `background` | `BackgroundTask \| None` | BackgroundTask to await when runBackground() is called. |

Declared return type: `None`.

<a id="api-008"></a>

### StreamingResponse

[`orionis.http.responses.StreamingResponse`](../responses.py)

```python
class StreamingResponse(Response):
```

Response retaining an async stream; getBody() is None. Synchronous iterables are wrapped in an async generator but iteration itself remains synchronous.

```python
def __init__(
    self,
    content: AsyncIterable[bytes] | Iterable[bytes],
    status_code: HTTPStatus | int = 200,
    headers: Mapping[str, str] | None = None,
    media_type: str | None = None,
    background: BackgroundTask | None = None,
) -> None:
```

Accepts AsyncIterable or Iterable, otherwise TypeError. The synchronous wrapper accepts bytes and converts bytearray/memoryview, raising TypeError for other chunks during iteration; async chunks are retained for adapters. Adds Content-Type from media_type if absent. Inherits Response errors; iteration errors occur when consumed.

| Parameter | Type | Meaning |
|---|---|---|
| `content` | `AsyncIterable[bytes] \| Iterable[bytes]` | Body or value to render; interpretation depends on the response class. |
| `status_code` | `HTTPStatus \| int` | HTTP status code; the response base validates integer values from 100 to 599. |
| `headers` | `Mapping[str, str] \| None` | Initial response headers, with names stored in lowercase. |
| `media_type` | `str \| None` | Response MIME type. |
| `background` | `BackgroundTask \| None` | BackgroundTask to await when runBackground() is called. |

Declared return type: `None`.

<a id="api-009"></a>

### FileResponse

[`orionis.http.responses.FileResponse`](../responses.py)

```python
class FileResponse(StreamingResponse):
```

StreamingResponse for a regular file. Constructor performs synchronous stat; the iterator opens, reads and closes through executor helpers, with a default 64 KiB read size. File content is not snapshotted.

```python
def __init__(
    self,
    path: str | Path,
    status_code: int = 200,
    headers: Mapping[str, str] | None = None,
    media_type: str | None = None,
    filename: str | None = None,
    chunk_size: int = 64 * 1024,
    background: BackgroundTask | None = None,
) -> None:
```

stats path, checks regular-file status, guesses media type and sets Content-Length; filename optionally sets attachment disposition. FileNotFoundError/OSError for stat, ValueError for non-file or nonpositive chunk_size, TypeError for non-int chunk_size; inherited response errors propagate. Later reads can fail separately.

| Parameter | Type | Meaning |
|---|---|---|
| `path` | `str \| Path` | Filesystem path for file responses; cookie URL path for cookie methods. |
| `status_code` | `int` | HTTP status code; the response base validates integer values from 100 to 599. |
| `headers` | `Mapping[str, str] \| None` | Initial response headers, with names stored in lowercase. |
| `media_type` | `str \| None` | Response MIME type. |
| `filename` | `str \| None` | Attachment filename; download() falls back to the file basename. |
| `chunk_size` | `int` | Positive integer file-read chunk size in bytes. |
| `background` | `BackgroundTask \| None` | BackgroundTask to await when runBackground() is called. |

Declared return type: `None`.

```python
def getPath(self) -> Path:
```

Returns the stored Path without resolving it.

Declared return type: `Path`.

```python
def getFileSize(self) -> int:
```

Returns size recorded by constructor stat, not a refreshed measurement.

Declared return type: `int`.

<a id="api-010"></a>

### ResponseFactory

[`orionis.http.factory.ResponseFactory`](../factory.py)

```python
class ResponseFactory:
```

Stateless factory with __slots__=(). The module creates response: ResponseFactory = ResponseFactory() once at import; direct factory construction remains possible. It is a shared convenience instance, not an enforced Singleton.

```python
def view(self, template: str, **context: Any) -> PendingView:
```

Returns View.make(template, **context), a PendingView to await for rendering. Uses the bound view facade and propagates resolution/rendering errors when the delegated operation runs.

| Parameter | Type | Meaning |
|---|---|---|
| `template` | `str` | Template identifier passed to View.make. |
| `context` | `Any` | Template context keyword arguments. |

Declared return type: `PendingView`.

```python
def html(
    self,
    content: str | bytes = "",
    status_code: HTTPStatus | int = 200,
    headers: Mapping[str, str] | None = None,
    background: BackgroundTask | None = None,
) -> HTMLResponse:
```

Constructs and returns HTMLResponse with these arguments; parameter meaning, side effects and exceptions are those of its constructor.

| Parameter | Type | Meaning |
|---|---|---|
| `content` | `str \| bytes` | Body or value to render; interpretation depends on the response class. |
| `status_code` | `HTTPStatus \| int` | HTTP status code; the response base validates integer values from 100 to 599. |
| `headers` | `Mapping[str, str] \| None` | Initial response headers, with names stored in lowercase. |
| `background` | `BackgroundTask \| None` | BackgroundTask to await when runBackground() is called. |

Declared return type: `HTMLResponse`.

```python
def json(
    self,
    content: Any,
    status_code: HTTPStatus | int = 200,
    headers: Mapping[str, str] | None = None,
    background: BackgroundTask | None = None,
    *,
    indent: int | None = None,
    ensure_ascii: bool = False,
    separators: tuple[str, str] | None = None,
    default: Any | None = None,
) -> JSONResponse:
```

Constructs and returns JSONResponse with these arguments; parameter meaning, side effects and exceptions are those of its constructor.

| Parameter | Type | Meaning |
|---|---|---|
| `content` | `Any` | Body or value to render; interpretation depends on the response class. |
| `status_code` | `HTTPStatus \| int` | HTTP status code; the response base validates integer values from 100 to 599. |
| `headers` | `Mapping[str, str] \| None` | Initial response headers, with names stored in lowercase. |
| `background` | `BackgroundTask \| None` | BackgroundTask to await when runBackground() is called. |
| `indent` | `int \| None` | JSON indentation; None enables compact output. |
| `ensure_ascii` | `bool` | Escape non-ASCII characters through the standard JSON encoder when true. |
| `separators` | `tuple[str, str] \| None` | JSON item/key separator pair; forwarded to json.dumps on its path. |
| `default` | `Any \| None` | Custom encoder hook; None selects JSONResponse._defaultEncoder. |

Declared return type: `JSONResponse`.

```python
def text(
    self,
    content: str | bytes = "",
    status_code: HTTPStatus | int = 200,
    headers: Mapping[str, str] | None = None,
    background: BackgroundTask | None = None,
) -> PlainTextResponse:
```

Constructs and returns PlainTextResponse with these arguments; parameter meaning, side effects and exceptions are those of its constructor.

| Parameter | Type | Meaning |
|---|---|---|
| `content` | `str \| bytes` | Body or value to render; interpretation depends on the response class. |
| `status_code` | `HTTPStatus \| int` | HTTP status code; the response base validates integer values from 100 to 599. |
| `headers` | `Mapping[str, str] \| None` | Initial response headers, with names stored in lowercase. |
| `background` | `BackgroundTask \| None` | BackgroundTask to await when runBackground() is called. |

Declared return type: `PlainTextResponse`.

```python
def redirect(
    self,
    url: str,
    status_code: HTTPStatus | int = 302,
    headers: Mapping[str, str] | None = None,
    background: BackgroundTask | None = None,
) -> RedirectResponse:
```

Constructs and returns RedirectResponse with these arguments; parameter meaning, side effects and exceptions are those of its constructor.

| Parameter | Type | Meaning |
|---|---|---|
| `url` | `str` | Redirect target string. |
| `status_code` | `HTTPStatus \| int` | HTTP status code; the response base validates integer values from 100 to 599. |
| `headers` | `Mapping[str, str] \| None` | Initial response headers, with names stored in lowercase. |
| `background` | `BackgroundTask \| None` | BackgroundTask to await when runBackground() is called. |

Declared return type: `RedirectResponse`.

```python
def stream(
    self,
    content: AsyncIterable[bytes] | Iterable[bytes],
    status_code: HTTPStatus | int = 200,
    headers: Mapping[str, str] | None = None,
    media_type: str | None = None,
    background: BackgroundTask | None = None,
) -> StreamingResponse:
```

Constructs and returns StreamingResponse with these arguments; parameter meaning, side effects and exceptions are those of its constructor.

| Parameter | Type | Meaning |
|---|---|---|
| `content` | `AsyncIterable[bytes] \| Iterable[bytes]` | Body or value to render; interpretation depends on the response class. |
| `status_code` | `HTTPStatus \| int` | HTTP status code; the response base validates integer values from 100 to 599. |
| `headers` | `Mapping[str, str] \| None` | Initial response headers, with names stored in lowercase. |
| `media_type` | `str \| None` | Response MIME type. |
| `background` | `BackgroundTask \| None` | BackgroundTask to await when runBackground() is called. |

Declared return type: `StreamingResponse`.

```python
def file(
    self,
    path: str | Path,
    status_code: HTTPStatus | int = 200,
    headers: Mapping[str, str] | None = None,
    media_type: str | None = None,
    filename: str | None = None,
    chunk_size: int = 64 * 1024,
    background: BackgroundTask | None = None,
) -> FileResponse:
```

Constructs and returns FileResponse with these arguments; parameter meaning, side effects and exceptions are those of its constructor.

| Parameter | Type | Meaning |
|---|---|---|
| `path` | `str \| Path` | Filesystem path for file responses; cookie URL path for cookie methods. |
| `status_code` | `HTTPStatus \| int` | HTTP status code; the response base validates integer values from 100 to 599. |
| `headers` | `Mapping[str, str] \| None` | Initial response headers, with names stored in lowercase. |
| `media_type` | `str \| None` | Response MIME type. |
| `filename` | `str \| None` | Attachment filename; download() falls back to the file basename. |
| `chunk_size` | `int` | Positive integer file-read chunk size in bytes. |
| `background` | `BackgroundTask \| None` | BackgroundTask to await when runBackground() is called. |

Declared return type: `FileResponse`.

```python
def download(
    self,
    path: str | Path,
    filename: str | None = None,
    headers: Mapping[str, str] | None = None,
    media_type: str | None = None,
    background: BackgroundTask | None = None,
) -> FileResponse:
```

Constructs FileResponse at its default 200 status, forces Content-Disposition attachment using filename or path basename, and returns it. Same file/response exceptions and filesystem stat side effect.

| Parameter | Type | Meaning |
|---|---|---|
| `path` | `str \| Path` | Filesystem path for file responses; cookie URL path for cookie methods. |
| `filename` | `str \| None` | Attachment filename; download() falls back to the file basename. |
| `headers` | `Mapping[str, str] \| None` | Initial response headers, with names stored in lowercase. |
| `media_type` | `str \| None` | Response MIME type. |
| `background` | `BackgroundTask \| None` | BackgroundTask to await when runBackground() is called. |

Declared return type: `FileResponse`.

```python
def noContent(
    self,
    status_code: HTTPStatus | int = 204,
    headers: Mapping[str, str] | None = None,
    background: BackgroundTask | None = None,
) -> Response:
```

Returns Response with an empty body and default status 204; accepts another valid status. Same Response constructor exceptions.

| Parameter | Type | Meaning |
|---|---|---|
| `status_code` | `HTTPStatus \| int` | HTTP status code; the response base validates integer values from 100 to 599. |
| `headers` | `Mapping[str, str] \| None` | Initial response headers, with names stored in lowercase. |
| `background` | `BackgroundTask \| None` | BackgroundTask to await when runBackground() is called. |

Declared return type: `Response`.

```python
def make(
    self,
    content: Any = None,
    status_code: HTTPStatus | int = 200,
    headers: Mapping[str, str] | None = None,
    media_type: str | None = None,
    background: BackgroundTask | None = None,
) -> Response:
```

Constructs and returns Response with these arguments; parameter meaning, side effects and exceptions are those of its constructor.

| Parameter | Type | Meaning |
|---|---|---|
| `content` | `Any` | Body or value to render; interpretation depends on the response class. |
| `status_code` | `HTTPStatus \| int` | HTTP status code; the response base validates integer values from 100 to 599. |
| `headers` | `Mapping[str, str] \| None` | Initial response headers, with names stored in lowercase. |
| `media_type` | `str \| None` | Response MIME type. |
| `background` | `BackgroundTask \| None` | BackgroundTask to await when runBackground() is called. |

Declared return type: `Response`.

<a id="api-011"></a>

### BaseMiddleware

[`orionis.http.middleware.BaseMiddleware`](../middleware.py)

```python
class BaseMiddleware(IBaseMiddleware):
```

Implements IBaseMiddleware and declares __slots__=(). Subclasses provide handle; the base implementation always raises NotImplementedError.

```python
async def handle(
    self,
    request: Request,
    call_next: NextCallable,
) -> Response:
```

Receives request and the next continuation; declared return Response, but this implementation always raises NotImplementedError naming the concrete class.

| Parameter | Type | Meaning |
|---|---|---|
| `request` | `Request` | Current Request. |
| `call_next` | `NextCallable` | Awaitable continuation for the following middleware layer. |

Declared return type: `Response`.

<a id="api-012"></a>

### BaseController

[`orionis.http.base.controller.BaseController`](../base/controller.py)

```python
class BaseController:
```

Empty marker class for controller inheritance; no locally defined constructor, fields or methods, and no dispatch behavior of its own.

<a id="api-013"></a>

### KernelHTTP

[`orionis.http.kernel.KernelHTTP`](../kernel.py)

```python
class KernelHTTP(IKernelHTTP):
```

HTTP dispatch coordinator implementing IKernelHTTP. Global order: proxies, maintenance if enabled, security, CORS preflight, then rate limit. OPTIONS is answered from the resolver before a Request is built. Web order: StartSessionMiddleware, CSRFTokenMiddleware, ResolveSessionIdentityMiddleware; API: ResolveTokenIdentityMiddleware; then route middleware and handler. CORS post-processing runs before transport output.

```python
def __init__(
    self,
    app: IApplication,
    catch: ICatch,
) -> None:
```

Retains application/exception services, sets the boot flag false and creates a middleware-instance cache. Returns None; performs no boot.

| Parameter | Type | Meaning |
|---|---|---|
| `app` | `IApplication` | Application service providing configuration, dependency resolution and scopes. |
| `catch` | `ICatch` | Application exception handler. |

Declared return type: `None`.

```python
async def boot(self) -> None:
```

Loads/compiles routes, preloads handler imports and route middleware, builds default responses, security/session/auth layers, transport senders and debug logging. Returns None; sequential subsequent calls are no-ops. Import, route, configuration and DI failures propagate. There is no lock against concurrent boot calls.

Declared return type: `None`.

```python
async def handleRSGI(
    self,
    scope: Scope,
    protocol: HTTPProtocol,
) -> object | None:
```

Creates an RSGI adapter, enters application.beginScope(), processes the request and sends it. Annotated object | None; current sender returns None. Requires prior boot; missing initialized fields can raise AttributeError. Processing exceptions delegate to ICatch (or validation/fallback paths); scope, sender, background and exception-handler failures can escape.

| Parameter | Type | Meaning |
|---|---|---|
| `scope` | `Scope` | Incoming ASGI dict or Granian RSGI Scope, according to the signature. |
| `protocol` | `HTTPProtocol` | Granian RSGI HTTP protocol used for body input and response output. |

Declared return type: `object | None`.

```python
async def handleASGI(
    self,
    scope: dict,
    receive: object,
    send: object,
) -> None:
```

Creates an ASGI adapter, enters application.beginScope(), processes and sends through receive/send; returns None. Same boot requirement and exception boundaries as handleRSGI.

| Parameter | Type | Meaning |
|---|---|---|
| `scope` | `dict` | Incoming ASGI dict or Granian RSGI Scope, according to the signature. |
| `receive` | `object` | ASGI receive callable, annotated object; BodyStream invokes it to read the body, while ASGIResponseAdapter receives it without using it. |
| `send` | `object` | ASGI send callable used to emit response messages. |

Declared return type: `None`.

The private _MiddlewarePipeline stores continuation state per request and raises RuntimeError if a layer calls next twice. Handler dispatch uses application.invoke/build/call; only Response, dict and msgspec.Struct results are accepted (the latter two become JSONResponse). Other results raise TypeError. Fallback handlers must return Response. Validation errors on web routes use validation_response; API validation errors become JSON 422. The Request is inserted into the application scope for injection.

<a id="api-014"></a>

### DefaultResponses

[`orionis.http.default.responses.DefaultResponses`](../default/responses.py)

```python
class DefaultResponses(IDefaultResponses):
```

Implements IDefaultResponses using bundled pages/assets and application public storage. Keeps instance caches and a module-level status-label cache; responses are freshly constructed. Template files are read synchronously on cache misses.

```python
def __init__(
    self,
    app: IApplication,
    directory: Directory,
) -> None:
```

Reads app.name/app.locale and initializes an instance cache; returns None. Configuration/service failures propagate.

| Parameter | Type | Meaning |
|---|---|---|
| `app` | `IApplication` | Application service providing configuration, dependency resolution and scopes. |
| `directory` | `Directory` | Application directory service; storagePublic() locates public assets. |

Declared return type: `None`.

```python
def __getitem__(self, key: str) -> object | None:
```

Returns cached object for key, or None without raising KeyError.

| Parameter | Type | Meaning |
|---|---|---|
| `key` | `str` | Header, cookie, flash or lookup key, as indicated by the method. |

Declared return type: `object | None`.

```python
def __setitem__(self, key: str, value: object) -> None:
```

Stores value under key; returns None.

| Parameter | Type | Meaning |
|---|---|---|
| `key` | `str` | Header, cookie, flash or lookup key, as indicated by the method. |
| `value` | `object` | Value associated with key. |

Declared return type: `None`.

```python
def __contains__(self, key: str) -> bool:
```

Returns whether key is cached.

| Parameter | Type | Meaning |
|---|---|---|
| `key` | `str` | Header, cookie, flash or lookup key, as indicated by the method. |

Declared return type: `bool`.

```python
def __delitem__(self, key: str) -> None:
```

Removes cached key if present; returns None, ignoring missing keys.

| Parameter | Type | Meaning |
|---|---|---|
| `key` | `str` | Header, cookie, flash or lookup key, as indicated by the method. |

Declared return type: `None`.

```python
def favicon(self) -> FileResponse | Response:
```

Returns a new FileResponse, caching its path/type. Searches storagePublic() for favicon.ico, .png, .svg, then bundled assets/favicon.ico; otherwise returns HTML 404. Sets public max-age=31536000, immutable. Filesystem and response errors propagate, including a cached file subsequently removed.

Declared return type: `FileResponse | Response`.

```python
def robotsTxt(self) -> FileResponse | Response:
```

Uses storagePublic()/robots.txt, then the bundled file, otherwise HTML 404; caches path and returns a new FileResponse with public max-age=3600. Filesystem/response errors propagate.

Declared return type: `FileResponse | Response`.

```python
def sitemapXml(self) -> FileResponse | Response:
```

Uses storagePublic()/sitemap.xml with public max-age=600; caches path and returns FileResponse, or HTML 404 when absent. No bundled sitemap fallback; filesystem/response errors propagate.

Declared return type: `FileResponse | Response`.

```python
def health(self, request: Request) -> HTMLResponse | JSONResponse:
```

Reads app.maintenance each call: false yields 200 with the up template, true yields 503 with down. JSON message values are "Online Application" and "Application in Maintenance", respectively. Uses wantsJson() for JSON, otherwise reads/caches HTML bytes with app name/locale substitutions. Returns a new response with no-cache/no-store. Invalid maintenance dictionary keys, file and encoding failures can propagate.

| Parameter | Type | Meaning |
|---|---|---|
| `request` | `Request` | Current Request. |

Declared return type: `HTMLResponse | JSONResponse`.

```python
def error(
    self,
    status_code: int | HTTPStatus,
    content: str | dict,
    *,
    expects_json: bool,
    headers: dict[str, str] | None = None,
) -> HTMLResponse | JSONResponse:
```

Validates status_code through the private _validate_status_code helper before rendering either format or reading a template: non-integer values raise TypeError and values outside 100–599 raise ValueError. JSON preserves dict content or wraps text as {"message": content}. HTML reads/caches a placeholder plan and uses the HTTPStatus label when available, otherwise "HTTP {code}" for a valid unlisted integer. Its description is the supplied text, str(content["message"]) when present, or json.dumps(content); html.escape makes it HTML text before substitution. The template's console logging reads the title and description through DOM textContent instead of interpolating them into JavaScript literals. Adds no-cache unless supplied. File, serialization and response errors propagate.

| Parameter | Type | Meaning |
|---|---|---|
| `status_code` | `int \| HTTPStatus` | Integer from 100 to 599, validated before rendering; unlisted HTML codes use the label HTTP {code}. |
| `content` | `str \| dict` | Error text or dictionary; JSON preserves the values and the HTML description is escaped text. |
| `expects_json` | `bool` | Choose JSON when true, otherwise HTML. |
| `headers` | `dict[str, str] \| None` | Initial response headers, with names stored in lowercase. |

Declared return type: `HTMLResponse | JSONResponse`.

```python
def exception(
    self,
    request_path: str,
    request_method: str,
    exception: BaseException,
    status_code: int | HTTPStatus = HTTPStatus.INTERNAL_SERVER_ERROR,
) -> HTMLResponse:
```

Reads/caches the exception template, obtains DateTime timezone/config/runtime metadata, parses the exception and substitutes request/traceback data. Returns HTMLResponse with no-cache. Does not itself gate the page on app.debug; file, facade, parser and serialization errors propagate.

| Parameter | Type | Meaning |
|---|---|---|
| `request_path` | `str` | Request path inserted into the exception page. |
| `request_method` | `str` | Request method inserted into the exception page. |
| `exception` | `BaseException` | Exception inspected by ExceptionParser. |
| `status_code` | `int \| HTTPStatus` | HTTP status code; the response base validates integer values from 100 to 599. |

Declared return type: `HTMLResponse`.

<a id="api-015"></a>

### LoginController

[`orionis.http.default.controllers.login_controller.LoginController`](../default/controllers/login_controller.py)

```python
class LoginController(BaseController):
```

Default BaseController for login/logout, dependent on configured views and IAuthManager. Its remember checkbox remembers the email in usrname; it does not pass a remember option to auth.attempt.

```python
    HOME_REDIRECT_PATH: str = "/home"
    DEFAULT_LOGIN_PATH: str = "/login"
    LOGOUT_REDIRECT_PATH: str = "/"
    LOGIN_VIEW_NAME: str = "auth.login"
    REMEMBER_COOKIE_MAX_AGE: int = 259200
    REMEMBER_COOKIE_NAME: str = "usrname"
```

```python
def __init__(
    self,
    application: IApplication,
) -> None:
```

Sets redirect_to from auth.session.home, falling back to /home; returns None. Configuration errors propagate.

| Parameter | Type | Meaning |
|---|---|---|
| `application` | `IApplication` | Application configuration used to select the login redirect. |

Declared return type: `None`.

```python
async def index(
    self,
) -> HttpResponse:
```

Awaits auth.login via response.view and returns the rendered response; view/service errors propagate.

Declared return type: `HttpResponse`.

```python
async def login(
    self,
    request: Request,
    payload: LoginSchema,
    auth: IAuthManager,
) -> HttpResponse:
```

Reads request.data(), calls auth.attempt with payload email/password. Failure returns /login redirect with filtered old input and email errors. Success redirects to redirect_to and sets usrname email for 259200 seconds only when raw remember == "on", otherwise an empty cookie with Max-Age=0. Auth, body, cookie and response errors propagate; authentication mutates external auth/session state.

| Parameter | Type | Meaning |
|---|---|---|
| `request` | `Request` | Current Request. |
| `payload` | `LoginSchema` | Validated LoginSchema with email and password. |
| `auth` | `IAuthManager` | Authentication manager invoked for attempt() or logout(). |

Declared return type: `HttpResponse`.

```python
async def logout(
    self,
    auth: IAuthManager,
) -> HttpResponse:
```

Awaits auth.logout(), then returns a redirect to /. Propagates auth/response failures and changes auth/session state.

| Parameter | Type | Meaning |
|---|---|---|
| `auth` | `IAuthManager` | Authentication manager invoked for attempt() or logout(). |

Declared return type: `HttpResponse`.

<a id="api-016"></a>

### RegisterController

[`orionis.http.default.controllers.register_controller.RegisterController`](../default/controllers/register_controller.py)

```python
class RegisterController(BaseController):
```

Application-coupled BaseController: directly imports app.models.user.User and uses DB/Hash facades and auth.register view.

```python
    REGISTER_VIEW_NAME: str = "auth.register"
    REGISTER_REDIRECT_PATH: str = "/login"
```

```python
async def index(
    self,
) -> HttpResponse:
```

Awaits auth.register and returns its response; view/service errors propagate.

Declared return type: `HttpResponse`.

```python
async def register(
    self,
    request: RegisterSchema,
) -> HttpResponse:
```

Begins a transaction, hashes password, strips name, strips/lowercases email, saves User and commits; returns /login redirect with success flash. Exceptions inside the try trigger rollback and rendering auth.register with errors/old input. beginTransaction runs outside try; rollback/render failures can propagate. Performs database writes and password hashing.

| Parameter | Type | Meaning |
|---|---|---|
| `request` | `RegisterSchema` | Validated RegisterSchema, despite the parameter name request. |

Declared return type: `HttpResponse`.

<a id="api-017"></a>

### IRequest

[contracts/request.py](../contracts/request.py)

Abstract ABC contract for Request. Parameters and return meanings are those of the corresponding method documented above; these declarations provide no concrete I/O or state policy. Unimplemented abstract members prevent instantiation (TypeError). The base bodies contain only docstrings and do not enforce the documented concrete behavior.

```python
class IRequest(ABC):
```

```python
@property
@abstractmethod
def url(self) -> str:
```

`url`: parameter/return semantics: `Request.url`. Concrete exceptions and side effects depend on the implementation.

```python
@property
@abstractmethod
def baseUrl(self) -> str:
```

`baseUrl`: parameter/return semantics: `Request.baseUrl`. Concrete exceptions and side effects depend on the implementation.

```python
@property
@abstractmethod
def headers(self) -> Headers:
```

`headers`: parameter/return semantics: `Request.headers`. Concrete exceptions and side effects depend on the implementation.

```python
@property
@abstractmethod
def queryParams(self) -> QueryParams:
```

`queryParams`: parameter/return semantics: `Request.queryParams`. Concrete exceptions and side effects depend on the implementation.

```python
@property
@abstractmethod
def cookies(self) -> Cookies:
```

`cookies`: parameter/return semantics: `Request.cookies`. Concrete exceptions and side effects depend on the implementation.

```python
@property
@abstractmethod
def ip(self) -> str | None:
```

`ip`: parameter/return semantics: `Request.ip`. Concrete exceptions and side effects depend on the implementation.

```python
@property
@abstractmethod
def port(self) -> int | None:
```

`port`: parameter/return semantics: `Request.port`. Concrete exceptions and side effects depend on the implementation.

```python
@property
@abstractmethod
def forwarded(self) -> dict[str, Any]:
```

`forwarded`: parameter/return semantics: `Request.forwarded`. Concrete exceptions and side effects depend on the implementation.

```python
@property
@abstractmethod
def method(self) -> str:
```

`method`: parameter/return semantics: `Request.method`. Concrete exceptions and side effects depend on the implementation.

```python
@property
@abstractmethod
def scheme(self) -> str:
```

`scheme`: parameter/return semantics: `Request.scheme`. Concrete exceptions and side effects depend on the implementation.

```python
@property
@abstractmethod
def path(self) -> str:
```

`path`: parameter/return semantics: `Request.path`. Concrete exceptions and side effects depend on the implementation.

```python
@property
@abstractmethod
def interface(self) -> Interface:
```

`interface`: parameter/return semantics: `Request.interface`. Concrete exceptions and side effects depend on the implementation.

```python
@property
@abstractmethod
def httpVersion(self) -> str:
```

`httpVersion`: parameter/return semantics: `Request.httpVersion`. Concrete exceptions and side effects depend on the implementation.

```python
@property
@abstractmethod
def userAgent(self) -> str | None:
```

`userAgent`: parameter/return semantics: `Request.userAgent`. Concrete exceptions and side effects depend on the implementation.

```python
@property
@abstractmethod
def apiKey(self) -> str | None:
```

`apiKey`: parameter/return semantics: `Request.apiKey`. Concrete exceptions and side effects depend on the implementation.

```python
@property
@abstractmethod
def bearerToken(self) -> str | None:
```

`bearerToken`: parameter/return semantics: `Request.bearerToken`. Concrete exceptions and side effects depend on the implementation.

```python
@property
@abstractmethod
def authorization(self) -> str | None:
```

`authorization`: parameter/return semantics: `Request.authorization`. Concrete exceptions and side effects depend on the implementation.

```python
@property
@abstractmethod
def accept(self) -> str | None:
```

`accept`: parameter/return semantics: `Request.accept`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def wantsJson(self) -> bool:
```

`wantsJson`: parameter/return semantics: `Request.wantsJson`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def accepts(self, mime: str) -> bool:
```

`accepts`: parameter/return semantics: `Request.accepts`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def isAjax(self) -> bool:
```

`isAjax`: parameter/return semantics: `Request.isAjax`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def wantsHtml(self) -> bool:
```

`wantsHtml`: parameter/return semantics: `Request.wantsHtml`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def wantsXml(self) -> bool:
```

`wantsXml`: parameter/return semantics: `Request.wantsXml`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
async def stream(self) -> AsyncGenerator[bytes]:
```

`stream`: parameter/return semantics: `Request.stream`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
async def body(self) -> bytes:
```

`body`: parameter/return semantics: `Request.body`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
async def json(self) -> object:
```

`json`: parameter/return semantics: `Request.json`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
async def payload(self) -> Any:
```

`payload`: parameter/return semantics: `Request.payload`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
async def formUrlEncoded(self) -> dict[str, Any]:
```

`formUrlEncoded`: parameter/return semantics: `Request.formUrlEncoded`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
async def raw(self) -> bytes:
```

`raw`: parameter/return semantics: `Request.raw`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
async def text(self) -> str:
```

`text`: parameter/return semantics: `Request.text`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
async def xml(self) -> ET.Element:
```

`xml`: parameter/return semantics: `Request.xml`. The contract documents `xml.etree.ElementTree.ParseError` for malformed XML and `defusedxml.common.EntitiesForbidden`, a `DefusedXmlException` subclass, for internal or external entity declarations. DTDs without entity declarations are allowed; external resources are not resolved. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
async def msgpack(self) -> object:
```

`msgpack`: declares object for any decoded MessagePack value, matching `Request.msgpack`; the docstring declares msgspec.DecodeError for invalid input. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
async def form(self) -> FormData:
```

`form`: parameter/return semantics: `Request.form`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
async def data(self) -> dict[str, Any]:
```

`data`: parameter/return semantics: `Request.data`. The contract documents TypeError for a decoded JSON/MessagePack value that is not a mapping, and ValueError for an empty/undecodable JSON or MessagePack body or multipart parsing failure. Concrete exceptions and side effects depend on the implementation.

```python
@property
@abstractmethod
def state(self) -> SimpleNamespace:
```

`state`: parameter/return semantics: `Request.state`. Concrete exceptions and side effects depend on the implementation.

```python
@property
@abstractmethod
def scope(self) -> dict[str, Any]:
```

`scope`: parameter/return semantics: `Request.scope`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def routeParam(self, key: str) -> object:
```

`routeParam`: parameter/return semantics: `Request.routeParam`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def routeParams(self) -> dict[str, Any]:
```

`routeParams`: parameter/return semantics: `Request.routeParams`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def csrfToken(self) -> str | None:
```

`csrfToken`: parameter/return semantics: `Request.csrfToken`. Concrete exceptions and side effects depend on the implementation.

The contract spells xml() return as ET.Element (ET is imported only under TYPE_CHECKING); Request uses XMLElement. payload() declares Any here and object in Request. These source annotations are preserved, not normalized.

<a id="api-018"></a>

### IResponse

[contracts/response.py](../contracts/response.py)

Abstract ABC contract for Response. Parameters and return meanings are those of the corresponding method documented above; these declarations provide no concrete I/O or state policy. Unimplemented abstract members prevent instantiation (TypeError). The base bodies contain only docstrings and do not enforce the documented concrete behavior.

```python
class IResponse(ABC):
```

```python
@abstractmethod
def render(self, content: Any) -> bytes:
```

`render`: parameter/return semantics: `Response.render`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def addHeader(self, key: str, value: str) -> None:
```

`addHeader`: parameter/return semantics: `Response.addHeader`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def setHeader(self, key: str, value: str) -> None:
```

`setHeader`: parameter/return semantics: `Response.setHeader`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def getHeader(self, key: str) -> list[str] | None:
```

`getHeader`: parameter/return semantics: `Response.getHeader`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def hasHeader(self, key: str) -> bool:
```

`hasHeader`: parameter/return semantics: `Response.hasHeader`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def removeHeader(self, key: str) -> None:
```

`removeHeader`: parameter/return semantics: `Response.removeHeader`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def getRawHeaders(self) -> list[tuple[bytes, bytes]]:
```

`getRawHeaders`: parameter/return semantics: `Response.getRawHeaders`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def setCookie(
    self,
    key: str,
    value: str = "",
    *,
    max_age: int | None = None,
    expires: datetime | str | int | None = None,
    path: str | None = "/",
    domain: str | None = None,
    secure: bool = False,
    http_only: bool = False,
    same_site: Literal["lax", "strict", "none"] | None = "lax",
    partitioned: bool = False,
) -> None:
```

`setCookie`: parameter/return semantics: `Response.setCookie`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def deleteCookie(
    self,
    key: str,
    *,
    path: str = "/",
    domain: str | None = None,
) -> None:
```

`deleteCookie`: parameter/return semantics: `Response.deleteCookie`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def withCookie(
    self,
    key: str,
    value: str = "",
    *,
    max_age: int | None = None,
    expires: datetime | str | int | None = None,
    path: str | None = "/",
    domain: str | None = None,
    secure: bool = False,
    http_only: bool = False,
    same_site: Literal["lax", "strict", "none"] | None = "lax",
    partitioned: bool = False,
) -> Self:
```

`withCookie`: parameter/return semantics: `Response.withCookie`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def withCookies(
    self,
    cookies: Mapping[str, str | Mapping[str, Any]],
) -> Self:
```

`withCookies`: parameter/return semantics: `Response.withCookies`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def withoutCookie(
    self,
    key: str,
    *,
    path: str = "/",
    domain: str | None = None,
) -> Self:
```

`withoutCookie`: parameter/return semantics: `Response.withoutCookie`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def withFlash(self, key: str, value: Any = None) -> Self:
```

`withFlash`: parameter/return semantics: `Response.withFlash`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def withInput(self, values: Mapping[str, Any]) -> Self:
```

`withInput`: parameter/return semantics: `Response.withInput`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def withErrors(self, errors: Mapping[str, Any] | Exception) -> Self:
```

`withErrors`: parameter/return semantics: `Response.withErrors`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def getFlashData(self) -> dict[str, Any] | None:
```

`getFlashData`: parameter/return semantics: `Response.getFlashData`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def getBody(self) -> bytes | None:
```

`getBody`: parameter/return semantics: `Response.getBody`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def getStream(self) -> AsyncIterable[bytes] | None:
```

`getStream`: parameter/return semantics: `Response.getStream`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def hasStream(self) -> bool:
```

`hasStream`: parameter/return semantics: `Response.hasStream`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
async def runBackground(self) -> None:
```

`runBackground`: parameter/return semantics: `Response.runBackground`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def getStatusCode(self) -> int:
```

`getStatusCode`: parameter/return semantics: `Response.getStatusCode`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def getMediaType(self) -> str | None:
```

`getMediaType`: parameter/return semantics: `Response.getMediaType`. Concrete exceptions and side effects depend on the implementation.

<a id="api-019"></a>

### IKernelHTTP

[contracts/kernel.py](../contracts/kernel.py)

Abstract ABC contract for KernelHTTP. Parameters and return meanings are those of the corresponding method documented above; these declarations provide no concrete I/O or state policy. Unimplemented abstract members prevent instantiation (TypeError). The base bodies contain only docstrings and do not enforce the documented concrete behavior.

```python
class IKernelHTTP(ABC):
```

```python
@abstractmethod
async def boot(self) -> None:
```

`boot`: parameter/return semantics: `KernelHTTP.boot`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
async def handleRSGI(
    self,
    scope: Scope,
    protocol: HTTPProtocol,
) -> object | None:
```

`handleRSGI`: parameter/return semantics: `KernelHTTP.handleRSGI`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
async def handleASGI(
    self,
    scope: dict,
    receive: object,
    send: object,
) -> None:
```

`handleASGI`: parameter/return semantics: `KernelHTTP.handleASGI`. Concrete exceptions and side effects depend on the implementation.

<a id="api-020"></a>

### IDefaultResponses

[default/contracts/responses.py](../default/contracts/responses.py)

Abstract ABC contract for DefaultResponses. Parameters and return meanings are those of the corresponding method documented above; these declarations provide no concrete I/O or state policy. Unimplemented abstract members prevent instantiation (TypeError). The base bodies contain only docstrings and do not enforce the documented concrete behavior.

```python
class IDefaultResponses(ABC):
```

```python
@abstractmethod
def favicon(self) -> FileResponse | Response:
```

`favicon`: parameter/return semantics: `DefaultResponses.favicon`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def robotsTxt(self) -> FileResponse | Response:
```

`robotsTxt`: parameter/return semantics: `DefaultResponses.robotsTxt`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def sitemapXml(self) -> FileResponse | Response:
```

`sitemapXml`: parameter/return semantics: `DefaultResponses.sitemapXml`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def health(self, request: Request) -> HTMLResponse | JSONResponse:
```

`health`: parameter/return semantics: `DefaultResponses.health`. Concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def error(
    self,
    status_code: int | HTTPStatus,
    content: str | dict,
    *,
    expects_json: bool,
    headers: dict[str, str] | None = None,
) -> HTMLResponse | JSONResponse:
```

`error`: parameter/return semantics: `DefaultResponses.error`. The contract documents integer status codes from 100 to 599, escaped HTML descriptions, TypeError for non-integer status and ValueError for out-of-range status. The abstract body performs no validation or rendering; concrete exceptions and side effects depend on the implementation.

```python
@abstractmethod
def exception(
    self,
    request_path: str,
    request_method: str,
    exception: BaseException,
    status_code: int | HTTPStatus = HTTPStatus.INTERNAL_SERVER_ERROR,
) -> HTMLResponse:
```

`exception`: parameter/return semantics: `DefaultResponses.exception`. Concrete exceptions and side effects depend on the implementation.

<a id="api-021"></a>

### validation_response

[validation.py](../validation.py)

```python
async def validation_response(
    exc: ValidationException,
    request: Request,
    responses: IDefaultResponses,
) -> Response:
```

For wantsJson() or isAjax(), returns default JSON error 422 with exc.error(). Otherwise returns a 302 redirect to previous_url, queues exc.errors and filters/queues request.data() as old input. Data-reading exceptions are swallowed only for repopulation; response/error-normalization failures propagate. Session persistence occurs in middleware.

| Parameter | Type | Meaning |
|---|---|---|
| `exc` | `ValidationException` | Schema validation exception supplying structured errors. |
| `request` | `Request` | Current Request. |
| `responses` | `IDefaultResponses` | Default response builder used for JSON validation errors. |

Declared return type: `Response`.

<a id="api-022"></a>

### previous_url

[validation.py](../validation.py)

```python
def previous_url(request: Request) -> str:
```

Returns nonempty session.getPreviousUrl() without origin revalidation; otherwise accepts Referer only when it is a single-slash absolute path or shares scheme/host/effective port with baseUrl. Rejects backslashes, control characters, // references and user credentials in absolute references. Falls back to request.url. Session/header access failures propagate; invalid Referer parsing is treated as nonlocal.

| Parameter | Type | Meaning |
|---|---|---|
| `request` | `Request` | Current Request. |

Declared return type: `str`.

<a id="api-023"></a>

### Interface

[enums/interfaces.py](../enums/interfaces.py)

```python
class Interface(StrEnum):
    """Represent the supported HTTP interface types.

    Attributes
    ----------
    ASGI : str
        Represents the ASGI interface.
    RSGI : str
        Represents the RSGI interface.
    """

    ASGI = "asgi"
    RSGI = "rsgi"
```

Enum declaration with exact member values. Construction from an unlisted value raises ValueError. WebSocketStatus supplies codes only; it does not implement a WebSocket transport.

<a id="api-024"></a>

### HTTPStatus

[enums/status.py](../enums/status.py)

```python
class HTTPStatus(IntEnum):
    CONTINUE = 100
    SWITCHING_PROTOCOLS = 101
    PROCESSING = 102
    EARLY_HINTS = 103
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NON_AUTHORITATIVE_INFORMATION = 203
    NO_CONTENT = 204
    RESET_CONTENT = 205
    PARTIAL_CONTENT = 206
    MULTI_STATUS = 207
    ALREADY_REPORTED = 208
    IM_USED = 226
    MULTIPLE_CHOICES = 300
    MOVED_PERMANENTLY = 301
    FOUND = 302
    SEE_OTHER = 303
    NOT_MODIFIED = 304
    USE_PROXY = 305
    UNUSED = 306
    TEMPORARY_REDIRECT = 307
    PERMANENT_REDIRECT = 308
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    PAYMENT_REQUIRED = 402
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    NOT_ACCEPTABLE = 406
    PROXY_AUTHENTICATION_REQUIRED = 407
    REQUEST_TIMEOUT = 408
    CONFLICT = 409
    GONE = 410
    LENGTH_REQUIRED = 411
    PRECONDITION_FAILED = 412
    CONTENT_TOO_LARGE = 413
    URI_TOO_LONG = 414
    UNSUPPORTED_MEDIA_TYPE = 415
    RANGE_NOT_SATISFIABLE = 416
    EXPECTATION_FAILED = 417
    IM_A_TEAPOT = 418
    PAGE_EXPIRED = 419
    MISDIRECTED_REQUEST = 421
    UNPROCESSABLE_CONTENT = 422
    LOCKED = 423
    FAILED_DEPENDENCY = 424
    TOO_EARLY = 425
    UPGRADE_REQUIRED = 426
    PRECONDITION_REQUIRED = 428
    TOO_MANY_REQUESTS = 429
    REQUEST_HEADER_FIELDS_TOO_LARGE = 431
    UNAVAILABLE_FOR_LEGAL_REASONS = 451
    INTERNAL_SERVER_ERROR = 500
    NOT_IMPLEMENTED = 501
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504
    HTTP_VERSION_NOT_SUPPORTED = 505
    VARIANT_ALSO_NEGOTIATES = 506
    INSUFFICIENT_STORAGE = 507
    LOOP_DETECTED = 508
    NOT_EXTENDED = 510
    NETWORK_AUTHENTICATION_REQUIRED = 511
```

Enum declaration with exact member values. Construction from an unlisted value raises ValueError. WebSocketStatus supplies codes only; it does not implement a WebSocket transport.

<a id="api-025"></a>

### WebSocketStatus

[enums/status.py](../enums/status.py)

```python
class WebSocketStatus(IntEnum):
    NORMAL_CLOSURE = 1000
    GOING_AWAY = 1001
    PROTOCOL_ERROR = 1002
    UNSUPPORTED_DATA = 1003
    RESERVED = 1004
    NO_STATUS_RCVD = 1005
    ABNORMAL_CLOSURE = 1006
    INVALID_FRAME_PAYLOAD_DATA = 1007
    POLICY_VIOLATION = 1008
    MESSAGE_TOO_BIG = 1009
    MANDATORY_EXT = 1010
    INTERNAL_ERROR = 1011
    SERVICE_RESTART = 1012
    TRY_AGAIN_LATER = 1013
    BAD_GATEWAY = 1014
    TLS_HANDSHAKE = 1015
    UNAUTHORIZED = 3000
    FORBIDDEN = 3003
    TIMEOUT = 3008
```

Enum declaration with exact member values. Construction from an unlisted value raises ValueError. WebSocketStatus supplies codes only; it does not implement a WebSocket transport.

<a id="api-026"></a>

### LoginSchema

[default/schemas/login.py](../default/schemas/login.py)

```python
class LoginSchema(Schema):

    # ruff: noqa: TC001

    email: Field[
        str,
        Message("Email must be a string."),
        MinLength(5, message="Email must be at least 5 characters long."),
        Email(message="Email must be a valid email address."),
    ]

    password: Field[
        str,
        Message("Password must be a string."),
        MinLength(8, message="Password must be at least 8 characters long."),
    ]

    remember: Nullable[str] = None
```

Declarative Schema subclass; no local constructor or methods. Field types, constraints, defaults and messages are copied above. Validation behavior is supplied by orionis.schemas. LoginSchema.remember is nullable str; RegisterSchema.Unique consults users.email and therefore depends on database configuration.

<a id="api-027"></a>

### RegisterSchema

[default/schemas/register.py](../default/schemas/register.py)

```python
class RegisterSchema(Schema):

    # ruff: noqa: TC001

    name: Field[
        str,
        Message("Name must be a string."),
        MinLength(6, message="Name must be at least 6 characters long."),
    ]

    email: Field[
        str,
        Message("Email must be a string."),
        Email(message="Email must be a valid email address."),
        Unique(
            table="users",
            column="email",
            message="Email already exists. Please use a different email address.",
        ),
    ]

    password: Field[
        str,
        Message("Password must be a string."),
        StrongPassword(
            message=(
                "Password must contain at least one uppercase letter,"
                " one lowercase letter, one number, and one special character."
            ),
        ),
    ]

    password_confirmation: Field[
        str,
        Message("Password confirmation must be a string."),
        ConfirmPassword(message="Password confirmation does not match the password."),
    ]
```

Declarative Schema subclass; no local constructor or methods. Field types, constraints, defaults and messages are copied above. Validation behavior is supplied by orionis.schemas. LoginSchema.remember is nullable str; RegisterSchema.Unique consults users.email and therefore depends on database configuration.

<a id="api-028"></a>

### HttpResponse

[types.py](../types.py)

```python
type HttpResponse = Response
```

Python type alias for Response, not a separate response implementation or constructor.

<a id="api-029"></a>

### `Router`

[router.py](../routes/router.py)

```python
class Router(IRouter):
```

Implements `IRouter`; stores mutable registration state and creates `FluentRoute` builders. No constructor or registration method performs request dispatch. HTTP methods available here are GET, POST, QUERY, PUT, DELETE and PATCH. Supplied controller actions use `parse_action`: an abstract class, whether bare or in a controller/method pair, raises `TypeError` before the route registry is changed.

**`__init__`**

```python
def __init__(
    self,
    app: IApplication,
) -> None:
```

`app: IApplication` supplies `routeHealthCheck`. Returns `None`; stores the application, starts in kind `"web"` and immediately registers GET routes for `/favicon.ico`, `/robots.txt`, `/sitemap.xml` and `app.routeHealthCheck` using `DefaultResponses`. Registration errors from `FluentRoute` propagate. A subsequent GET on one of the first three paths removes the previous default-path entry only if its current path is still that path; a prefixed previous route is retained. The health path has no corresponding special replacement rule.

**`_setKind`**

```python
def _setKind(self, kind: str) -> None:
```

Internal loader hook: `kind: str` becomes the context for subsequent registrations. Returns `None`, mutating only this context; the method itself does not validate the value. `FluentRoute._kind` validates and normalizes it when a route is added.

**`auth`**

```python
def auth(self) -> None:
```

No parameters; returns `None`. Lazily imports the login and registration controllers, then registers GET/POST `/login`, GET/POST `/sign-up` under `GuestMiddleware`, and POST `/logout` under `AuthenticateSessionMiddleware`. The POST names are `login`, `register`, `logout`. Raises `ValueError` outside the web context; import and registration errors propagate. Repeated calls are not guarded here and create route conflicts detected during compilation.

**`view`**

```python
def view(
    self,
    path: str,
    view: str,
) -> FluentRoute:
```

`path: str` is normalized as a route path; `view: str` is a template name, stripped before storage. Returns the registered GET `FluentRoute`. Raises `ValueError` for a non-string or blank `view`, and `TypeError` for a non-string path. Mutates the route registry; it does not render the template.

**`post`**

```python
def post(
    self,
    path: str,
    action: RouteAction | None = None,
) -> FluentRoute:
```

`path: str` is normalized; `action: RouteAction | None = None` is parsed immediately when non-`None`. Omitting it or passing `None` registers an unfinished builder; call `.action(Controller, "method")` before exporting. Returns the registered POST `FluentRoute` and mutates the registry. Raises `TypeError` for a non-string path or an unsupported non-`None` action; malformed controller pairs raise the `TypeError`/`ValueError` described under `parse_action`. Duplicate ordinary method/path registrations remain until compilation rejects them.

**`query`**

```python
def query(
    self,
    path: str,
    action: RouteAction | None = None,
) -> FluentRoute:
```

`path: str` is normalized; `action: RouteAction | None = None` is parsed immediately when non-`None`. Omitting it or passing `None` registers an unfinished builder; call `.action(Controller, "method")` before exporting. Returns the registered QUERY `FluentRoute` and mutates the registry. Raises `TypeError` for a non-string path or an unsupported non-`None` action; malformed controller pairs raise the `TypeError`/`ValueError` described under `parse_action`. Duplicate ordinary method/path registrations remain until compilation rejects them.

**`get`**

```python
def get(
    self,
    path: str,
    action: RouteAction | None = None,
) -> FluentRoute:
```

`path: str` is normalized; `action: RouteAction | None = None` is parsed immediately when non-`None`. Omitting it or passing `None` registers an unfinished builder; call `.action(Controller, "method")` before exporting. Returns the registered GET `FluentRoute` and mutates the registry. Raises `TypeError` for a non-string path or an unsupported non-`None` action; malformed controller pairs raise the `TypeError`/`ValueError` described under `parse_action`. Duplicate ordinary method/path registrations remain until compilation rejects them.

**`put`**

```python
def put(
    self,
    path: str,
    action: RouteAction | None = None,
) -> FluentRoute:
```

`path: str` is normalized; `action: RouteAction | None = None` is parsed immediately when non-`None`. Omitting it or passing `None` registers an unfinished builder; call `.action(Controller, "method")` before exporting. Returns the registered PUT `FluentRoute` and mutates the registry. Raises `TypeError` for a non-string path or an unsupported non-`None` action; malformed controller pairs raise the `TypeError`/`ValueError` described under `parse_action`. Duplicate ordinary method/path registrations remain until compilation rejects them.

**`delete`**

```python
def delete(
    self,
    path: str,
    action: RouteAction | None = None,
) -> FluentRoute:
```

`path: str` is normalized; `action: RouteAction | None = None` is parsed immediately when non-`None`. Omitting it or passing `None` registers an unfinished builder; call `.action(Controller, "method")` before exporting. Returns the registered DELETE `FluentRoute` and mutates the registry. Raises `TypeError` for a non-string path or an unsupported non-`None` action; malformed controller pairs raise the `TypeError`/`ValueError` described under `parse_action`. Duplicate ordinary method/path registrations remain until compilation rejects them.

**`patch`**

```python
def patch(
    self,
    path: str,
    action: RouteAction | None = None,
) -> FluentRoute:
```

`path: str` is normalized; `action: RouteAction | None = None` is parsed immediately when non-`None`. Omitting it or passing `None` registers an unfinished builder; call `.action(Controller, "method")` before exporting. Returns the registered PATCH `FluentRoute` and mutates the registry. Raises `TypeError` for a non-string path or an unsupported non-`None` action; malformed controller pairs raise the `TypeError`/`ValueError` described under `parse_action`. Duplicate ordinary method/path registrations remain until compilation rejects them.

**`fallback`**

```python
def fallback(
    self,
    action: RouteAction,
) -> None:
```

`action: RouteAction` is required and parsed immediately; returns `None` and stores one fallback tuple, without a fluent builder. Functions become `(None, function)`, invokable classes become `(Class, "__call__")`, and controller pairs keep `(Class, method)`. Omitting the argument raises `TypeError`; explicit `None` is rejected by parsing. Raises `FallbackRouteAlreadyRegisteredException` when a fallback is already registered, before parsing the supplied action; other parsing errors propagate.

**`group`**

```python
def group(
    self,
    *,
    prefix: str | None = None,
    middleware: MiddlewareInput | None = None,
    without_middleware: MiddlewareInput | None = None,
    routes: Sequence[FluentRoute | RouteGroup] | None = None,
) -> RouteGroup:
```

Keyword-only parameters: `prefix: str | None` is normalized and prepended; `middleware: MiddlewareInput | None` is prepended to each member stack; `without_middleware: MiddlewareInput | None` adds exclusions; `routes: Sequence[FluentRoute | RouteGroup] | None` is flattened to unique leaf routes. Returns `RouteGroup`. Raises `TypeError` for non-sequence membership, string/bytes membership or invalid members; `ValueError` for empty membership, duplicate route IDs, a non-string prefix, or invalid middleware. Validation completes before group mutation. Inner registration expressions have already registered their routes. Groups mutate the same route objects, including externally created members, and insert them into this router. Nested parents run before descendant middleware; exclusions are finalized by the compiler.

**`export`**

```python
def export(self) -> dict:
```

No parameters; returns `dict` with `routes: list[dict]` and `fallback: tuple`. Produces a fresh outer mapping/list but each route export retains references to its middleware list and exclusion set. An unset fallback is `(None, None)`. Propagates `ValueError` from any route that still has no action or view; the message identifies its method and current path. No I/O.

<a id="api-030"></a>

### `FluentRoute`

[fluent.py](../routes/fluent.py)

```python
class FluentRoute(IFluentRoute):
```

Mutable `IFluentRoute` builder. Fluent setters return the same instance (`Self`). Its generated ID remains unchanged when prefixes alter the path; `_ALLOWED_METHODS` is `{"GET", "POST", "PUT", "DELETE", "PATCH", "QUERY"}`.

**`__init__`**

```python
def __init__(
    self,
    method: str,
    path: str,
    action: RouteAction | None = None,
    *,
    view: str | None = None,
) -> None:
```

`method: str` is uppercased and checked against the allowed set; `path: str` is normalized. `action: RouteAction | None` supplies a parsed function/controller, or leaves the route unfinished when omitted or `None`. Keyword-only `view: str | None` bypasses action parsing and stores a stripped template name. Returns `None`, creates a route ID and initializes empty middleware/name state with kind `"web"`. Raises `TypeError` for a non-string method/path or invalid action; `ValueError` for an unsupported method, blank/non-string view, or invalid controller pair. Without a view, an unfinished route must receive `.action(controller, handler)` before `export()`, which otherwise raises `ValueError` with the method and current path. ID allocation happens before action/view validation.

**`path`**

```python
@property
def path(self) -> str:
```

Read-only property; no parameters. Returns the current canonical path (`str`), including inherited prefixes. No mutation or explicit exceptions.

**`id`**

```python
@property
def id(self) -> str:
```

Read-only property; no parameters. Returns the original route identifier (`str`). No mutation or explicit exceptions.

**`action`**

```python
def action(self, controller: type, handler: str) -> Self:
```

`controller: type` and `handler: str` are validated as `[controller, handler]` by `parse_action`; returns `Self`. Completes an unfinished route or replaces its class/method, clearing the standalone callable and view. An abstract controller raises `TypeError` before method lookup; a concrete subclass may use an inherited callable method. Parsing `TypeError`/`ValueError` propagate before mutation.

**`name`**

```python
def name(self, name: str) -> Self:
```

`name: str` is stripped and stored; returns `Self`. Raises `TypeError` for non-strings and `ValueError` for blank names. Name uniqueness across paths is checked only by the compiler.

**`middleware`**

```python
def middleware(
    self,
    *middleware: MiddlewareInput,
) -> Self:
```

`*middleware: MiddlewareInput` accepts classes or one-level sequences/sets; returns `Self` and appends the validated flattened entries without deduplicating. Invalid entries raise `TypeError` before the extension. Set input is sorted by module/qualified name.

**`withOutMiddleware`**

```python
def withOutMiddleware(
    self,
    *middleware: MiddlewareInput,
) -> Self:
```

`*middleware: MiddlewareInput` uses the same validation/flattening; returns `Self` and updates the exclusion set. Invalid entries raise `TypeError` before mutation. The exact spelling is `withOutMiddleware`.

**`prefix`**

```python
def prefix(self, prefix: str) -> Self:
```

`prefix: str` is normalized and prepended to the current path; returns `Self`. Raises `TypeError` for non-strings. Root paths avoid an extra trailing slash. Mutates the path without regenerating the ID.

**`inheritGroup`**

```python
def inheritGroup(
    self,
    prefix: str,
    middleware: tuple[type[BaseMiddleware], ...],
    without_middleware: frozenset[type[BaseMiddleware]],
) -> Self:
```

`prefix: str` must already be canonical without a trailing slash; `middleware: tuple[type[BaseMiddleware], ...]` is prepended; `without_middleware: frozenset[type[BaseMiddleware]]` is merged. Returns `Self` and mutates the builder. This public helper trusts the caller/`Router.group` validation; it adds no explicit validation or exceptions.

**`_kind`**

```python
def _kind(self, kind: str) -> Self:
```

Internal registration hook: `kind: str` is stripped/lowercased, stored, and returned through `Self`. Raises `TypeError` for non-strings; it does not restrict the result to `web`/`api`.

**`export`**

```python
def export(self) -> dict:
```

No parameters; returns a new `dict` containing `id`, `method`, `path`, `class`, `handler`, `callable_handler`, `view`, `name`, `middleware`, `without_middleware`, `kind`. Middleware and exclusions are shared mutable containers, not copies. Raises `ValueError` if neither an action nor a view is assigned; the message contains the method and current path and asks for `.action(controller, handler)` before export. No I/O.

<a id="api-031"></a>

### `RouteGroup`

[group.py](../routes/group.py)

```python
@dataclass(frozen=True, slots=True)
class RouteGroup:
```

`@dataclass(frozen=True, slots=True)` stores `routes: tuple[FluentRoute, ...]`, the flattened membership produced by `Router.group`. Its generated constructor accepts that field; no explicit `__init__` is defined in the source. Freezing prevents field reassignment, but the contained route builders remain mutable. No custom validation, exceptions or I/O; assignment to frozen fields raises `dataclasses.FrozenInstanceError`.

```python
routes: tuple[FluentRoute, ...]
```

<a id="api-032"></a>

### `RouteID`

[route_id.py](../routes/route_id.py)

```python
class RouteID:
```

Stateless class with `__slots__ = ()`. Module globals cache the process ID and `time.time_ns`, plus an `itertools.count(1)` counter.

**`next`**

```python
@staticmethod
def next(method: str, path: str) -> str:
```

`method: str` and `path: str` are interpolated without validation. Returns `str` in the form `method:path:pid:time_ns:counter`; reads the clock and increments the process-local counter. No explicit exceptions. The code contains no lock or explicit cross-process/thread uniqueness guarantee.

<a id="api-033"></a>

### `RouteCompiler`

[route_compiler.py](../routes/route_compiler.py)

```python
class RouteCompiler(IRouteCompiler):
```

`IRouteCompiler` implementation that converts exported builders into per-method static maps and ordered dynamic route lists. It has no explicit constructor or instance state.

**`compile`**

```python
def compile(
    self,
    routes: list[dict],
    fallback: tuple | None,
    app_middleware: list[type] | None = None,
) -> tuple[dict[str, dict], tuple | None]:
```

`routes: list[dict]` is the router export; `fallback: tuple | None` is passed through unchanged; `app_middleware: list[type] | None` supplies the global stack. Returns `(dict[str, dict], tuple | None)` with each method mapped to `{"static": {path: CompiledRoute}, "dynamic": [CompiledRoute, ...]}`. Global middleware precedes route middleware, exclusions apply to both, and class identity removes duplicates while preserving first occurrence. Dynamic routes sort stably by descending `static_segments * 10 - dynamic_segments`. `ValueError`: duplicate static method/path; structurally identical dynamic regex for the same method; the same name on different path templates; malformed/duplicate/unknown path parameters; handler qualified names containing `<locals>`. Action validation also raises `TypeError`/`ValueError`. Missing required dictionary keys propagate `KeyError`. No I/O or mutation of input route containers; produced dataclasses contain copied middleware/exclusion containers.

**`compilePath`**

```python
@staticmethod
def compilePath(
    path: str,
) -> tuple[bool, re.Pattern | None, dict[str, Callable]]:
```

`path: str` is a route template; returns `(is_static: bool, regex: re.Pattern | None, converters: dict[str, Callable])`. Static paths return `(True, None, {})`. Dynamic `{name}` defaults to `str`; `{name:type}` uses `PARAM_TYPES`, escapes literal fragments and anchors the regex with `^`/`$`. Raises `ValueError` for unmatched/malformed braces, invalid or duplicate parameter identifiers and unknown types; regex compilation errors can propagate for modified converter patterns. It neither normalizes the path nor mutates external state.

<a id="api-034"></a>

### `RouteCache`

[route_cache.py](../routes/route_cache.py)

```python
class RouteCache(IRouteCache):
```

`IRouteCache` implementation; `VERSION = 2`. Serializes metadata to dictionaries; file persistence is a separate `RouteLoader` responsibility. The cache omits regexes/converter callables and regenerates them from each path.

**`toCache`**

```python
def toCache(
    self,
    routes: dict[str, dict],
    fallback: tuple | None,
) -> dict:
```

`routes: dict[str, dict]` is compiler output; `fallback: tuple | None` is the raw fallback. Returns a `dict` with `version`, `fallback`, and method-grouped `routes`. Stores enum values, action descriptors, metrics, kind and middleware dotted import names; no file I/O. `None`/`(None, None)` fallback becomes `None`. Invalid input structures can propagate `KeyError`, `AttributeError` or unpacking errors; there is no explicit schema validation. `action` dictionaries are retained by reference in the returned structure.

**`fromCache`**

```python
def fromCache(
    self,
    cached: dict,
) -> tuple[dict[str, dict], tuple | None]:
```

`cached: dict` supplies serialized metadata. Returns `(routes: dict[str, dict], fallback: tuple | None)`, recompiles paths and imports middleware classes/fallback objects. Middleware class resolutions are memoized within this call. Does not check `version` itself; the loader does. Raises/propagates `ValueError` for invalid `RouteType`, invalid paths or a fallback function qualified name containing `<locals>`; malformed schemas can raise `KeyError`/`TypeError`, and missing imports/attributes propagate import/attribute errors. Import execution is a side effect; no file I/O occurs here.

<a id="api-035"></a>

### `RouteLoader`

[loader.py](../routes/loader.py)

```python
class RouteLoader(IRouteLoader):
```

`IRouteLoader` implementation with lazy, once-per-instance loading. Its private flow is cache lookup → import route modules in `("web", "api")` order → compile → normalize an absent fallback → optionally persist. A `finally` restores router kind to `"web"`, including failed imports. `__loaded` is set only after successful restoration from cache or compilation/persistence.

**`__init__`**

```python
def __init__(
    self,
    app: IApplication,
    router: IRouter,
    compiler: RouteCompiler,
    cache: RouteCache,
) -> None:
```

`app: IApplication` provides middleware, routing paths and compilation settings; `router: IRouter` stores registrations; `compiler: RouteCompiler` builds routes; `cache: RouteCache` serializes them. Returns `None`, captures `app.getMiddleware()`, and when `app.compiled` is true creates `FileBasedCache(path=app.compiledPath, filename="routes", monitored_dirs=app.compiledInvalidationPathsDirs, monitored_files=app.compiledInvalidationPathsFiles)`. Collaborator/configuration and cache-construction errors propagate; route modules are not loaded yet.

**`load`**

```python
def load(self) -> dict[str, dict]:
```

No parameters; returns the stored `dict[str, dict]` directly. On first access, reads persistent cache if enabled and accepts only a truthy mapping whose version is `RouteCache.VERSION`; otherwise imports application route files relative to `app.path("root")`, compiles, normalizes an absent fallback to `None` and saves when persistence is enabled. After compilation and before persistence, `case (None, None)` matches the router sentinel using identity checks for `None`, without invoking handler equality methods; valid fallback tuples remain unchanged. Imports execute registration side effects, and cache operations perform delegated file I/O. `Path.relative_to` can raise `ValueError`; export also raises `ValueError` for unfinished routes. Import, compiler, cache and persistence exceptions propagate. A second successful call reuses the same mapping, including an empty route table.

**`fallback`**

```python
@property
def fallback(self) -> tuple | None:
```

Read-only property; no parameters. Triggers the same load operation and returns `tuple | None`: `(Class, method_name)` for controller fallbacks, `(None, callable)` for function fallbacks, or `None` when none is registered. An absent fallback is `None` with caching disabled, after a cache miss and compilation, and after cache restoration. `Router.export()` still produces the raw `(None, None)` sentinel and `RouteCompiler.compile()` passes it through; the loader normalizes it before exposure and persistence. Side effects and exceptions are the same as `load()`.

<a id="api-036"></a>

### `RouteResolver`

[route_resolver.py](../routes/route_resolver.py)

```python
class RouteResolver(IRouteResolver):
```

`IRouteResolver` implementation with `__slots__`. Builds static lookups and dynamic tables partitioned by path depth; larger groups may also partition by literal prefixes while retaining priority order. Successful dynamic results share a bounded FIFO cache. No user handler runs during lookup.

**`__init__`**

```python
def __init__(
    self,
    routes: dict[str, dict],
    hot_cache_size: int = 512,
    fallback: tuple | None = None,
) -> None:
```

`routes: dict[str, dict]` is compiled method/static/dynamic data; `hot_cache_size: int = 512` bounds successful dynamic entries (`0` disables caching); `fallback: tuple | None` is stored with `(None, None)` normalized to `None`. Returns `None` and builds lookup structures, static `ResolvedRoute` objects and a deduplicated route tuple by object identity. Raises `TypeError` for a non-int capacity, including `bool`, and `ValueError` for a negative capacity; malformed compiled input may propagate structural/regex errors. No I/O.

**`resolve`**

```python
def resolve(self, method: str, path: str) -> ResolvedRoute:
```

`method: str` is uppercased when needed and `HEAD` maps to `GET`; `path: str` passes through `normalize_request_path`. Returns `ResolvedRoute` with converted, read-only parameters; static matches precede dynamic matches. Successful dynamic lookups mutate the FIFO cache; cache hits do not refresh eviction order. Raises `MethodNotAllowed(path)` when the normalized path matches another method (or any static path), otherwise `RouteNotFound(path)`. Conversion `ValueError`/`OverflowError` is treated as a failed dynamic match; other converter exceptions propagate. Other-method checks test regexes without conversion. Does not execute or automatically return the fallback.

**`options`**

```python
def options(self, path: str) -> list[str]:
```

`path: str` is normalized; returns sorted `list[str]` of methods whose static table or dynamic regex matches, with implicit `HEAD` for GET and `OPTIONS` for any matching path. If no route matches but a fallback exists, returns `["GET", "HEAD", "OPTIONS"]`; otherwise `[]`. Performs no parameter conversion and no cache mutation. No explicit exceptions for valid input.

**`fallback`**

```python
def fallback(self) -> tuple | None:
```

No parameters; returns the stored `tuple | None` fallback without executing it. No mutation or explicit exceptions.

**`allRoutes`**

```python
def allRoutes(self) -> list[CompiledRoute]:
```

No parameters; returns a new `list[CompiledRoute]` in method-table traversal order, each original route object once by identity. No mutation or explicit exceptions.

**`invalidateCache`**

```python
def invalidateCache(self) -> None:
```

No parameters; returns `None` and clears the dynamic result mapping and FIFO queue. Static tables and route descriptors remain available. No explicit exceptions.

<a id="api-037"></a>

### `RouterProvider`

[provider.py](../routes/provider.py)

```python
class RouterProvider(ServiceProvider):
```

Inherits `ServiceProvider`; integrates the router with the application container and `orionis.support.facades.router.Route`. No constructor is declared in this file.

**`register`**

```python
def register(self) -> None:
```

No parameters; returns `None`. Registers `IRouter` with implementation `Router` as a singleton under alias `"x-orionis-IRouter"` by calling `self.app.singleton(IRouter, Router, alias="x-orionis-IRouter")`, mutating container registrations. Container exceptions propagate; no explicit local exceptions.

**`boot`**

```python
async def boot(self) -> None:
```

Async method with no parameters; awaiting it returns `None` after `await RouteFacade.pin()`. Initializes shared facade state; facade exceptions propagate. The method contains no additional local synchronization.

<a id="api-038"></a>

### `CompiledRoute`

[entities/compiled_route.py](../routes/entities/compiled_route.py)

```python
@dataclass(slots=True, frozen=True)
class CompiledRoute:
```

Frozen/slotted dataclass; its generated constructor accepts the fields below in declaration order (no explicit constructor signature exists in this file). Required fields are `path`, `method`, `type`, `action`, `name`, `regex`, `segment_count`. `path: str` is the template; `method: str` is the method; `type: RouteType` selects dispatch; `action: dict` contains `view`, or `module` plus `function`, or `module`/`class`/`method`; `name: str | None` is the URL name; `regex: Pattern | None` is absent for static paths. `segment_count: int` narrows dynamic matching; `priority_score: int` orders specificity; `kind: str` carries pipeline kind. `converters: dict[str, Callable]` converts parameters; `middleware: list` and `without_middleware: set` preserve route declarations; `compiled_middlewares: tuple` is the final execution order. Factory defaults create fresh containers. Freezing is shallow: nested dictionaries, lists and sets remain mutable. No custom validation or I/O; field reassignment raises the standard frozen-dataclass error.

```python
path: str
method: str
type: RouteType
action: dict
name: str | None
regex: Pattern | None
segment_count: int
priority_score: int = 0
kind: str = "web"
converters: dict[str, Callable] = field(default_factory=dict)
middleware: list = field(default_factory=list)
without_middleware: set = field(default_factory=set)
compiled_middlewares: tuple = field(default_factory=tuple)
```

<a id="api-039"></a>

### `ResolvedRoute`

[entities/resolved_route.py](../routes/entities/resolved_route.py)

```python
@dataclass(slots=True, frozen=True)
class ResolvedRoute:
```

Frozen/slotted dataclass with generated constructor fields `route: CompiledRoute` (matched descriptor) and `params: Mapping[str, Any]` (converted path parameters). The source has no explicit constructor signature. The route reference is preserved; parameter mapping structure is made read-only, without deep-copying values.

```python
route: CompiledRoute
params: Mapping[str, Any]
```

**`__post_init__`**

```python
def __post_init__(self) -> None:
```

Generated-constructor hook; no parameters, returns `None`. Copies a nonempty supplied mapping through `dict` and wraps it in `MappingProxyType`; uses a shared empty proxy for empty mappings. Invalid mapping inputs can propagate `TypeError`/`ValueError`. Mutating the resulting mapping raises `TypeError`; frozen field reassignment raises the dataclass error.

**`_fromOwnedParams`**

```python
@classmethod
def _fromOwnedParams(
    cls,
    route: CompiledRoute,
    params: dict[str, Any],
) -> ResolvedRoute:
```

Internal classmethod: `route: CompiledRoute` is the descriptor; `params: dict[str, Any]` transfers an exclusively owned dictionary. Returns `ResolvedRoute` without copying that dictionary or invoking the normal constructor. The resolver must discard mutable references; retaining and mutating them changes the proxy contents. No explicit validation or I/O.

**`kind`**

```python
@property
def kind(self) -> str:
```

Read-only property; no parameters. Returns `str` directly from `route.kind`; it does not enforce the docstring restriction to `web` or `api`. No mutation or explicit exceptions.

<a id="api-040"></a>

### `RouteType`

[enums/route_types.py](../routes/enums/route_types.py)

```python
class RouteType(StrEnum):
```

`StrEnum` dispatch discriminator with the exact members below. Standard enum construction from an unknown value raises `ValueError`; there are no custom methods or side effects.

```python
CONTROLLER = "controller"
FUNCTION = "function"
INVOKABLE = "invokable"
VIEW = "view"
```

<a id="api-041"></a>

### `FallbackRouteAlreadyRegisteredException`

[exceptions/fallback_route_already_registered.py](../routes/exceptions/fallback_route_already_registered.py)

```python
class FallbackRouteAlreadyRegisteredException(Exception):
```

Plain `Exception` subclass raised by `Router.fallback` when a fallback is already registered.

No local constructor, fields, methods or return value are declared. Custom argument types/validation:

> ⚠️ No especificado en el código fuente

<a id="api-042"></a>

### `MethodNotAllowed`

[exceptions/method_not_allowed.py](../routes/exceptions/method_not_allowed.py)

```python
class MethodNotAllowed(Exception):
```

Plain `Exception` subclass raised by `RouteResolver.resolve` when the path exists for another method. The path is supplied as its exception argument; this class itself does not construct an HTTP response.

No local constructor, fields, methods or return value are declared. Custom argument types/validation:

> ⚠️ No especificado en el código fuente

<a id="api-043"></a>

### `RouteNotFound`

[exceptions/route_not_found.py](../routes/exceptions/route_not_found.py)

```python
class RouteNotFound(Exception):
```

Plain `Exception` subclass raised when route resolution fails. `resolve` supplies the path as its argument; the private combined-regex extractor may supply an invariant-error message.

No local constructor, fields, methods or return value are declared. Custom argument types/validation:

> ⚠️ No especificado en el código fuente

<a id="api-044"></a>

### `normalize_path`

[functions.py](../routes/functions.py)

```python
def normalize_path(path: str) -> str:
```

`path: str` is stripped, consecutive slashes collapse, a leading slash is ensured and trailing slashes are removed except at root. Returns canonical `str`; empty/whitespace-only input becomes `/`. Does not mutate external state or explicitly validate types; non-string inputs can propagate `AttributeError`/`TypeError` from string/regex operations.

<a id="api-045"></a>

### `normalize_request_path`

[functions.py](../routes/functions.py)

```python
def normalize_request_path(path: str) -> str:
```

`path: str` receives a leading slash if missing and loses trailing slashes except at root; empty input becomes `/`. Returns `str`. Unlike registration normalization, it preserves whitespace and repeated internal slashes. No external mutation or explicit type validation; invalid types can propagate indexing/string-operation errors.

<a id="api-046"></a>

### `strip_regex_anchors`

[functions.py](../routes/functions.py)

```python
def strip_regex_anchors(pattern: str) -> str:
```

`pattern: str` is processed textually: removes at most one leading `^` and one trailing `$`. Returns `str`; no regex parsing, external mutation or explicit exceptions for valid strings. A trailing escaped dollar is still treated as a trailing character.

<a id="api-047"></a>

### `flatten_middleware`

[functions.py](../routes/functions.py)

```python
def flatten_middleware(
    *middleware: MiddlewareInput,
) -> list[type[BaseMiddleware]]:
```

`*middleware: MiddlewareInput` accepts `BaseMiddleware` subclasses directly or in a `Sequence`/abstract `Set`, flattened one level. Returns a new `list[type[BaseMiddleware]]`; preserves sequence order and sorts each set by `(class.__module__, class.__qualname__)`. Does not deduplicate. Raises `TypeError` for any member that is not a `BaseMiddleware` subclass; nested containers and instances fail. No mutation of supplied containers or I/O.

<a id="api-048"></a>

### `is_valid_handler`

[functions.py](../routes/functions.py)

```python
def is_valid_handler(action: object) -> bool:
```

`action: object` is checked by calling `parse_action(action)`. Returns `True` when parsing succeeds and `False` when it raises `TypeError` or `ValueError`. Accepted Python functions (including coroutine functions), concrete invokable controller classes and valid concrete controller/method pairs therefore return `True`; abstract controllers in either form, callable instances, bound methods, builtins, `functools.partial` objects, coroutine objects, lambdas and `None` return `False`.

This is structural validation; it does not guarantee importability or dependency resolution. It neither instantiates controllers nor invokes handlers itself. Controller attribute lookup may execute descriptors with side effects; exceptions other than `TypeError` and `ValueError` propagate.

<a id="api-049"></a>

### `parse_action`

[functions.py](../routes/functions.py)

```python
def parse_action( # NOSONAR
    action: object,
) -> tuple[Callable, None] | tuple[type, str]:
```

`action: object` accepts a concrete invokable class defining/inheriting callable `__call__`, a non-lambda Python function (including `async def`), or a two-element list/tuple `(concrete_class, method_name)`. A concrete subclass may use an inherited callable method. Returns `(callable_or_class, None)` or `(class, str)` exactly as annotated. Python functions are checked directly with `inspect.isfunction`, `callable`, the coroutine-object exclusion and the non-lambda name check; the parser does not call `is_valid_handler`.

Raises `TypeError` for abstract controller classes in either form, non-invokable bare classes, wrong pair element types, callable instances, bound methods, builtins, `functools.partial` objects, coroutine objects, lambdas, `None` or other unsupported forms; `ValueError` for pair length other than two or an absent/non-callable method. An abstract class in a pair is rejected before method lookup with `TypeError("First element of action list must be a concrete class")`. The unsupported-form error lists the accepted forms and explicitly excludes callable instances and bound methods.

Ordinary route registration, `FluentRoute.action` and `Router.fallback` use this parser; `RouteCompiler.compile` also applies it to raw handler/controller route declarations. Validation is structural and does not guarantee importability or dependency resolution. No controller instantiation or handler invocation occurs here; attribute lookup during pair validation may execute descriptors with side effects, and their exceptions propagate.

<a id="api-050"></a>

### `RouteAction`

[types.py](../routes/types.py)

```python
type RouteAction = Callable | type | list[type | str] | tuple[type, str]
```

Public type alias for route registration inputs. It retains `Callable` for typing compatibility, representing Python functions here; runtime acceptance is narrower. `parse_action` rejects callable instances, bound methods, builtins and lambdas, as the source comment explains. Use `is_valid_handler` for the parser's structural acceptance check. No runtime validation or side effects belong to the alias.

<a id="api-051"></a>

### `MiddlewareInput`

[types.py](../routes/types.py)

```python
type MiddlewareInput = (
    type[BaseMiddleware]
    | Sequence[type[BaseMiddleware]]
    | AbstractSet[type[BaseMiddleware]]
)
```

Public type alias for one middleware class or a sequence/set of classes. `flatten_middleware` performs runtime validation and deterministic ordering for sets.

<a id="api-052"></a>

### `PARAM_TYPES`

[params_types.py](../routes/params_types.py)

```python
PARAM_TYPES = {
    "str": {
        "pattern": r"[^/]+",
        "converter": str,
    },
    "slug": {
        "pattern": r"[a-z0-9-]+",
        "converter": str,
    },
    "int": {
        "pattern": r"\d+",
        "converter": int,
    },
    "uuid": {
        "pattern": (
            r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
        ),
        "converter": uuid.UUID,
    },
}
```

Mutable converter registry consumed by `RouteCompiler.compilePath`. `str` matches one or more non-slash characters; `slug` matches lowercase ASCII letters/digits/hyphens; `int` matches `\d+` and converts with `int`; `uuid` matches the shown canonical hexadecimal shape and converts with `uuid.UUID`. No optional segments, negative-integer pattern or catch-all path type is declared. Cache restoration consults the current registry again.

<a id="api-053"></a>

### `ParamConverter`

[route_resolver.py](../routes/route_resolver.py)

```python
ParamConverter = Callable[[str], object]
```

Converter callable: input `str`, output `object`; actual converter exceptions propagate except the resolver catches `ValueError`/`OverflowError` as failed matches.

<a id="api-054"></a>

### `Extractor`

[route_resolver.py](../routes/route_resolver.py)

```python
Extractor = tuple[str, int, ParamConverter]
```

Tuple `(parameter_name: str, capture_group_index: int, converter: ParamConverter)` used to extract typed path parameters.

<a id="api-055"></a>

### `BucketEntry`

[route_resolver.py](../routes/route_resolver.py)

```python
BucketEntry = tuple[list[Extractor], "CompiledRoute"]
```

Pairs a list of extraction descriptors with a compiled route. Used by private dynamic-matching buckets.

<a id="api-056"></a>

### `DepthTable`

[route_resolver.py](../routes/route_resolver.py)

```python
type DepthTable = dict[int, _DepthBucket | _PrefixIndex]
```

Maps segment depth (`int`) to a private `_DepthBucket` combined regex or `_PrefixIndex` branching structure. No public construction/validation function is defined for these internals.

<a id="api-057"></a>

### `IRouter`

[contracts/router.py](../routes/contracts/router.py)

```python
class IRouter(ABC):
```

Abstract base class (`ABC`). Each declaration below uses `@abstractmethod`; incomplete subclasses cannot be instantiated (`TypeError`). Method bodies contain only documentation and do not implement validation, I/O or state changes. `Router` provides the concrete behavior documented separately. Additional exceptions or effects for arbitrary third-party implementations:

> ⚠️ No especificado en el código fuente

**`auth`**

```python
@abstractmethod
def auth(self) -> None:
```

No parameters; declares registration of built-in authentication routes, returning `None`; documents `ValueError` outside the web context. The abstract body performs no operation; see `Router.auth` for implementation effects and actual errors.

**`view`**

```python
@abstractmethod
def view(
    self,
    path: str,
    view: str,
) -> FluentRoute:
```

`path: str` is the URL; `view: str` is the template. Returns the registered `FluentRoute`. The abstract body performs no operation; see `Router.view` for implementation effects and actual errors.

**`post`**

```python
@abstractmethod
def post(
    self,
    path: str,
    action: RouteAction | None = None,
) -> FluentRoute:
```

`path: str` and optional `action: RouteAction | None` register a POST route, returning `FluentRoute`. An omitted/`None` action must be assigned with `.action(controller, handler)` before export. The abstract body performs no operation; see `Router.post` for implementation effects and actual errors.

**`query`**

```python
@abstractmethod
def query(
    self,
    path: str,
    action: RouteAction | None = None,
) -> FluentRoute:
```

`path: str` and optional `action: RouteAction | None` register a QUERY route, returning `FluentRoute`. An omitted/`None` action must be assigned with `.action(controller, handler)` before export. The abstract body performs no operation; see `Router.query` for implementation effects and actual errors.

**`get`**

```python
@abstractmethod
def get(
    self,
    path: str,
    action: RouteAction | None = None,
) -> FluentRoute:
```

`path: str` and optional `action: RouteAction | None` register a GET route, returning `FluentRoute`. An omitted/`None` action must be assigned with `.action(controller, handler)` before export. The abstract body performs no operation; see `Router.get` for implementation effects and actual errors.

**`put`**

```python
@abstractmethod
def put(
    self,
    path: str,
    action: RouteAction | None = None,
) -> FluentRoute:
```

`path: str` and optional `action: RouteAction | None` register a PUT route, returning `FluentRoute`. An omitted/`None` action must be assigned with `.action(controller, handler)` before export. The abstract body performs no operation; see `Router.put` for implementation effects and actual errors.

**`delete`**

```python
@abstractmethod
def delete(
    self,
    path: str,
    action: RouteAction | None = None,
) -> FluentRoute:
```

`path: str` and optional `action: RouteAction | None` register a DELETE route, returning `FluentRoute`. An omitted/`None` action must be assigned with `.action(controller, handler)` before export. The abstract body performs no operation; see `Router.delete` for implementation effects and actual errors.

**`patch`**

```python
@abstractmethod
def patch(
    self,
    path: str,
    action: RouteAction | None = None,
) -> FluentRoute:
```

`path: str` and optional `action: RouteAction | None` register a PATCH route, returning `FluentRoute`. An omitted/`None` action must be assigned with `.action(controller, handler)` before export. The abstract body performs no operation; see `Router.patch` for implementation effects and actual errors.

**`fallback`**

```python
@abstractmethod
def fallback(
    self,
    action: RouteAction,
) -> None:
```

Required `action: RouteAction` supplies a complete fallback; returns `None` without chaining. Documents `FallbackRouteAlreadyRegisteredException` for repeated registration and `TypeError` for `None` or an unsupported handler form. The abstract body performs no operation; see `Router.fallback` for implementation effects and actual errors.

**`group`**

```python
@abstractmethod
def group(
    self,
    *,
    prefix: str | None = None,
    middleware: MiddlewareInput | None = None,
    without_middleware: MiddlewareInput | None = None,
    routes: Sequence[FluentRoute | RouteGroup] | None = None,
) -> RouteGroup:
```

Keyword-only `prefix: str | None`, `middleware: MiddlewareInput | None`, `without_middleware: MiddlewareInput | None` and `routes: Sequence[FluentRoute | RouteGroup] | None` describe shared context and membership. Returns `RouteGroup`; documents `ValueError` for empty routes/invalid prefix/middleware and `TypeError` for invalid members. The abstract body performs no operation; see `Router.group` for implementation effects and actual errors.

**`export`**

```python
@abstractmethod
def export(self) -> dict:
```

No parameters; returns `dict` with all exported routes and the fallback. Documents `ValueError` for an unfinished route without an action or view. The abstract body performs no operation; see `Router.export` for implementation effects and actual errors.

<a id="api-058"></a>

### `IFluentRoute`

[contracts/fluent.py](../routes/contracts/fluent.py)

```python
class IFluentRoute(ABC):
```

Abstract base class (`ABC`). Each declaration below uses `@abstractmethod`; incomplete subclasses cannot be instantiated (`TypeError`). Method bodies contain only documentation and do not implement validation, I/O or state changes. `FluentRoute` provides the concrete behavior documented separately. Additional exceptions or effects for arbitrary third-party implementations:

> ⚠️ No especificado en el código fuente

**`id`**

```python
@property
@abstractmethod
def id(self) -> str:
```

No parameters; read-only property returning route identifier `str`. The abstract body performs no operation; see `FluentRoute.id` for implementation effects and actual errors.

**`action`**

```python
@abstractmethod
def action(self, controller: type, handler: str) -> Self:
```

`controller: type` and `handler: str` identify the class and method; returns `Self` for chaining. The abstract body performs no operation; see `FluentRoute.action` for implementation effects and actual errors.

**`name`**

```python
@abstractmethod
def name(self, name: str) -> Self:
```

`name: str` supplies the route name; returns `Self`. The abstract body performs no operation; see `FluentRoute.name` for implementation effects and actual errors.

**`middleware`**

```python
@abstractmethod
def middleware(
    self,
    *middleware: MiddlewareInput,
) -> Self:
```

`*middleware: MiddlewareInput` supplies classes or containers to add; returns `Self`. The abstract body performs no operation; see `FluentRoute.middleware` for implementation effects and actual errors.

**`withOutMiddleware`**

```python
@abstractmethod
def withOutMiddleware(
    self,
    *middleware: MiddlewareInput,
) -> Self:
```

`*middleware: MiddlewareInput` supplies classes or containers to exclude; returns `Self`. The abstract body performs no operation; see `FluentRoute.withOutMiddleware` for implementation effects and actual errors.

**`prefix`**

```python
@abstractmethod
def prefix(self, prefix: str) -> Self:
```

`prefix: str` supplies the path prefix; returns `Self`. The abstract body performs no operation; see `FluentRoute.prefix` for implementation effects and actual errors.

**`export`**

```python
@abstractmethod
def export(self) -> dict:
```

No parameters; returns `dict` describing a complete fluent route. Documents `ValueError` if neither an action nor a view is assigned. The abstract body performs no operation; see `FluentRoute.export` for implementation effects and actual errors.

<a id="api-059"></a>

### `IRouteLoader`

[contracts/loader.py](../routes/contracts/loader.py)

```python
class IRouteLoader(ABC):
```

Abstract base class (`ABC`). Each declaration below uses `@abstractmethod`; incomplete subclasses cannot be instantiated (`TypeError`). Method bodies contain only documentation and do not implement validation, I/O or state changes. `RouteLoader` provides the concrete behavior documented separately. Additional exceptions or effects for arbitrary third-party implementations:

> ⚠️ No especificado en el código fuente

**`load`**

```python
@abstractmethod
def load(self) -> dict[str, dict]:
```

No parameters; returns compiled `dict[str, dict]` with method-specific `static` and `dynamic` buckets. The abstract body performs no operation; see `RouteLoader.load` for implementation effects and actual errors.

**`fallback`**

```python
@property
@abstractmethod
def fallback(self) -> tuple | None:
```

Read-only property with no parameters; its documented access triggers loading. Returns `(Class, method_name)` for controller fallbacks, `(None, callable)` for function fallbacks, or `None` when none is registered, whether compiled on demand or restored from cache. The abstract body performs no operation; see `RouteLoader.fallback` for implementation effects and actual errors.

<a id="api-060"></a>

### `IRouteCompiler`

[contracts/route_compiler.py](../routes/contracts/route_compiler.py)

```python
class IRouteCompiler(ABC):
```

Abstract base class (`ABC`). Each declaration below uses `@abstractmethod`; incomplete subclasses cannot be instantiated (`TypeError`). Method bodies contain only documentation and do not implement validation, I/O or state changes. `RouteCompiler` provides the concrete behavior documented separately. Additional exceptions or effects for arbitrary third-party implementations:

> ⚠️ No especificado en el código fuente

**`compile`**

```python
@abstractmethod
def compile(
    self,
    routes: list[dict],
    fallback: tuple | None,
    app_middleware: list[type] | None = None,
) -> tuple[dict[str, dict], tuple | None]:
```

`routes: list[dict]` is raw route data; `fallback: tuple | None` is the fallback; optional `app_middleware: list[type] | None` precedes route middleware. Returns `(compiled_routes, fallback): tuple[dict[str, dict], tuple | None]`; documents `ValueError` for dynamic collisions and `TypeError` for invalid invokable classes. The abstract body performs no operation; see `RouteCompiler.compile` for implementation effects and actual errors.

**`compilePath`**

```python
@staticmethod
@abstractmethod
def compilePath(
    path: str,
) -> tuple[bool, re.Pattern | None, dict[str, Callable]]:
```

Static abstract method; `path: str` is the template. Returns `(is_static, regex, converters): tuple[bool, re.Pattern | None, dict[str, Callable]]`. The abstract body performs no operation; see `RouteCompiler.compilePath` for implementation effects and actual errors.

<a id="api-061"></a>

### `IRouteCache`

[contracts/route_cache.py](../routes/contracts/route_cache.py)

```python
class IRouteCache(ABC):
```

Abstract base class (`ABC`). Each declaration below uses `@abstractmethod`; incomplete subclasses cannot be instantiated (`TypeError`). Method bodies contain only documentation and do not implement validation, I/O or state changes. `RouteCache` provides the concrete behavior documented separately. Additional exceptions or effects for arbitrary third-party implementations:

> ⚠️ No especificado en el código fuente

**`toCache`**

```python
@abstractmethod
def toCache(
    self,
    routes: dict[str, dict],
    fallback: tuple | None,
) -> dict:
```

`routes: dict[str, dict]` is compiled data and `fallback: tuple | None` its fallback. Returns a serialized cache `dict`. The abstract body performs no operation; see `RouteCache.toCache` for implementation effects and actual errors.

**`fromCache`**

```python
@abstractmethod
def fromCache(
    self,
    cached: dict,
) -> tuple[dict[str, dict], tuple | None]:
```

`cached: dict` is serialized data; returns reconstructed `(routes, fallback): tuple[dict[str, dict], tuple | None]`. The abstract body performs no operation; see `RouteCache.fromCache` for implementation effects and actual errors.

<a id="api-062"></a>

### `IRouteResolver`

[contracts/route_resolver.py](../routes/contracts/route_resolver.py)

```python
class IRouteResolver(ABC):
```

Abstract base class (`ABC`). Each declaration below uses `@abstractmethod`; incomplete subclasses cannot be instantiated (`TypeError`). Method bodies contain only documentation and do not implement validation, I/O or state changes. `RouteResolver` provides the concrete behavior documented separately. Additional exceptions or effects for arbitrary third-party implementations:

> ⚠️ No especificado en el código fuente

**`resolve`**

```python
@abstractmethod
def resolve(
    self,
    method: str,
    path: str,
) -> ResolvedRoute:
```

`method: str` is the HTTP method; `path: str` is the raw request path. Returns `ResolvedRoute`; documents `RouteNotFound` and `MethodNotAllowed` for missing/method-mismatched paths. The abstract body performs no operation; see `RouteResolver.resolve` for implementation effects and actual errors.

**`options`**

```python
@abstractmethod
def options(self, path: str) -> list[str]:
```

`path: str` is the raw request path; returns sorted allowed methods as `list[str]`. The abstract body performs no operation; see `RouteResolver.options` for implementation effects and actual errors.

**`fallback`**

```python
@abstractmethod
def fallback(self) -> tuple | None:
```

No parameters; returns the registered `tuple | None` fallback. For `IRouteLoader` this is a property whose documented access triggers loading; for `IRouteResolver` it is a method. The abstract body performs no operation; see `RouteResolver.fallback` for implementation effects and actual errors.

**`allRoutes`**

```python
@abstractmethod
def allRoutes(self) -> list:
```

No parameters; signature returns `list` (the docstring specifies `list[CompiledRoute]`), with all deduplicated compiled routes. The abstract body performs no operation; see `RouteResolver.allRoutes` for implementation effects and actual errors.

**`invalidateCache`**

```python
@abstractmethod
def invalidateCache(self) -> None:
```

No parameters; returns `None` and declares clearing the hot-path cache. The abstract body performs no operation; see `RouteResolver.invalidateCache` for implementation effects and actual errors.

<a id="api-063"></a>

### PayloadTooLargeException

Source: [body.py](../payload/body.py).

```python
class PayloadTooLargeException(Exception):
```

Exception subclass raised by `BodyStream` when the accumulated nonempty transport chunks exceed its configured limit. It adds no constructor, fields or methods; construction and exception arguments come from `Exception`.

<a id="api-064"></a>

### BodyStream

Source: [body.py](../payload/body.py).

```python
class BodyStream(IBodyStream):
```

Owns one ASGI receive callable or one RSGI async iterable. `interface is Interface.RSGI` selects RSGI; every other value follows the ASGI path. `None` is represented internally by `sys.maxsize`, so it is a finite sentinel. There is no validation of a negative limit. The consumed flag is set before the first transport await. ASGI message types are not inspected: only `body` and `more_body` are read.

```python
__slots__ = (
        "__body",
        "__consumed",
        "__is_rsgi",
        "__max_size",
        "__receive",
    )
```

#### BodyStream.__init__

```python
def __init__(
    self,
    interface: Interface,
    receive_or_protocol: object,
    max_body_size: int | None = None,
) -> None:
```

Parameters:

- `interface` (`Interface`): Transport interface selector.
- `receive_or_protocol` (`object`): ASGI receive callable or RSGI async protocol.
- `max_body_size` (`int | None`): Maximum accumulated body bytes; `None` selects the sentinel limit.

Stores the transport and limit, initializes an empty cache and an unconsumed state; returns `None`. Does not read the transport.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `None`.

#### BodyStream.isBuffered

```python
@property
def isBuffered(self) -> bool:
```

Property: returns whether a complete bytes buffer is cached; does not change state.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `bool`.

#### BodyStream.isConsumed

```python
@property
def isConsumed(self) -> bool:
```

Property: returns whether consumption has started, including an interrupted or failed read; it does not mean every byte was received.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `bool`.

#### BodyStream.stream

```python
async def stream(self) -> AsyncGenerator[bytes]:  # NOSONAR # noqa: C901
```

Async generator yielding nonempty raw chunks, checking the accumulated byte count before yielding each chunk. If already buffered, yields the complete cached buffer once (including `b""`). Otherwise marks the transport consumed; streaming does not populate the cache. A partly consumed or failed stream cannot be restarted.

Exceptions: `RuntimeError("Request stream already consumed")` after uncached consumption; `PayloadTooLargeException("Request body too large")` when the accumulated size is greater than the limit. Transport errors and cancellation propagate.

Declared return/yield type: `AsyncGenerator[bytes]`.

#### BodyStream.read

```python
async def read(self) -> bytes:
```

Collects chunks and joins them into one `bytes` value, caches it, and returns it. Later calls return that same cached object. Keeps both the chunk list and joined result during buffering.

Exceptions: Propagates the errors of `stream()`; a failed read leaves no complete cache and the consumed flag remains set.

Declared return/yield type: `bytes`.

<a id="api-065"></a>

### Headers

Source: [estructures/headers.py](../payload/estructures/headers.py).

```python
class Headers(metaclass=Final):
```

Case-insensitive lookup with ordered original-case pairs. The exact `list` supplied to the constructor is adopted without copying; other iterables are materialized. Mutating an adopted list after construction can desynchronize it from the lowercase lookup index. The `Final` metaclass rejects subclassing with `TypeError`.

```python
__slots__ = ("_index", "_items")
```

#### Headers.__init__

```python
def __init__(self, raw: Iterable[tuple[str, str]]) -> None:
```

Parameters:

- `raw` (`Iterable[tuple[str, str]]`): Ordered string header pairs.

Stores/materializes `raw`, builds the lowercase index and returns `None`. Duplicate header values preserve insertion order.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `None`.

#### Headers.get

```python
def get(self, key: str, default: str | None = None) -> str | None:
```

Parameters:

- `key` (`str`): Name to retrieve or test; case rules are described on the class.
- `default` (`str | None`): Fallback for an absent name.

Returns the last value for case-insensitive `key`, or `default`.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `str | None`.

#### Headers.count

```python
def count(self, key: str) -> int:
```

Parameters:

- `key` (`str`): Name to retrieve or test; case rules are described on the class.

Returns how many entries match case-insensitive `key`, or zero.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `int`.

#### Headers.getAll

```python
def getAll(
    self, key: str | None = None,
) -> dict[str, list[str]] | list[str]:
```

Parameters:

- `key` (`str | None`): Name to retrieve or test; case rules are described on the class.

For `key=None`, returns a new dictionary of lowercase names to copied value lists. Otherwise returns a copied list for that case-insensitive key, or `[]`.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `dict[str, list[str]] | list[str]`.

#### Headers.__contains__

```python
def __contains__(self, key: str) -> bool:
```

Parameters:

- `key` (`str`): Name to retrieve or test; case rules are described on the class.

Returns whether case-insensitive `key` is present.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `bool`.

#### Headers.__getitem__

```python
def __getitem__(self, key: str) -> str:
```

Parameters:

- `key` (`str`): Name to retrieve or test; case rules are described on the class.

Returns the last value for case-insensitive `key`.

Exceptions: `KeyError(key)` when absent.

Declared return/yield type: `str`.

#### Headers.__iter__

```python
def __iter__(self) -> Iterator[tuple[str, str]]:
```

Returns an iterator of all original `(name, value)` pairs, including duplicates.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `Iterator[tuple[str, str]]`.

#### Headers.items

```python
def items(self) -> list[tuple[str, str]]:
```

Returns a shallow copy of all original pairs in insertion order.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `list[tuple[str, str]]`.

#### Headers.byteItems

```python
def byteItems(self) -> Iterator[tuple[bytes, bytes]]:
```

Generator yielding every original name and value encoded as UTF-8, preserving original casing and duplicates.

Exceptions: `UnicodeEncodeError` for strings that cannot be encoded as strict UTF-8.

Declared return/yield type: `Iterator[tuple[bytes, bytes]]`.

#### Headers.keys

```python
def keys(self) -> set[str]:
```

Returns a set of unique names in their original casing: differently cased spellings remain distinct in this result.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `set[str]`.

#### Headers.values

```python
def values(self) -> list[str]:
```

Returns a new list of all values in insertion order, including duplicates.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `list[str]`.

#### Headers.__len__

```python
def __len__(self) -> int:
```

Returns the total count of pairs, including duplicate names.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `int`.

#### Headers.__repr__

```python
def __repr__(self) -> str:
```

Returns `Headers(...)` with the original pairs.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `str`.

<a id="api-066"></a>

### Cookies

Source: [estructures/cookies.py](../payload/estructures/cookies.py).

```python
class Cookies(metaclass=Final):
```

Case-sensitive cookie mapping. Parsing splits on semicolons, ignores segments without `=`, splits each pair at the first `=`, trims whitespace, strips matching outer double quotes and percent-decodes values using `urllib.parse.unquote`. Plus signs remain plus signs. Repeated cookie names keep their last value. `Final` rejects subclassing with `TypeError`.

```python
__slots__ = ("_data",)
```

#### Cookies.__init__

```python
def __init__(self, cookie_header: str | None) -> None:
```

Parameters:

- `cookie_header` (`str | None`): Raw Cookie header, or `None`.

Parses `cookie_header` into the internal mapping; false/empty input creates an empty mapping. Returns `None`.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `None`.

#### Cookies.get

```python
def get(self, key: str, default: str | None = None) -> str | None:
```

Parameters:

- `key` (`str`): Name to retrieve or test; case rules are described on the class.
- `default` (`str | None`): Fallback for an absent name.

Returns the value for case-sensitive `key`, or `default`.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `str | None`.

#### Cookies.getAll

```python
def getAll(self) -> dict[str, str]:
```

Returns a shallow dictionary copy of all cookies.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `dict[str, str]`.

#### Cookies.__getitem__

```python
def __getitem__(self, key: str) -> str:
```

Parameters:

- `key` (`str`): Name to retrieve or test; case rules are described on the class.

Returns the value of case-sensitive `key`.

Exceptions: `KeyError` when absent.

Declared return/yield type: `str`.

#### Cookies.__contains__

```python
def __contains__(self, key: str) -> bool:
```

Parameters:

- `key` (`str`): Name to retrieve or test; case rules are described on the class.

Returns whether case-sensitive `key` exists.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `bool`.

#### Cookies.items

```python
def items(self) -> ItemsView[str, str]:
```

Returns the live `dict_items` view of cookie name/value pairs, annotated as `ItemsView[str, str]` from `collections.abc`.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `ItemsView[str, str]`.

#### Cookies.keys

```python
def keys(self) -> KeysView[str]:
```

Returns the live `dict_keys` view of cookie names, annotated as `KeysView[str]` from `collections.abc`.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `KeysView[str]`.

#### Cookies.values

```python
def values(self) -> ValuesView[str]:
```

Returns the live `dict_values` view of cookie values, annotated as `ValuesView[str]` from `collections.abc`.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `ValuesView[str]`.

#### Cookies.__iter__

```python
def __iter__(self) -> Iterator[tuple[str, str]]:
```

Returns an iterator of `(name, value)` pairs, not an iterator of names alone.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `Iterator[tuple[str, str]]`.

#### Cookies.__len__

```python
def __len__(self) -> int:
```

Returns the number of distinct cookie names.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `int`.

#### Cookies.__repr__

```python
def __repr__(self) -> str:
```

Returns `Cookies(...)` with the internal mapping representation.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `str`.

<a id="api-067"></a>

### QueryParams

Source: [estructures/query_params.py](../payload/estructures/query_params.py).

```python
class QueryParams(metaclass=Final):
```

Case-sensitive query multimap built with `parse_qsl(..., keep_blank_values=True, strict_parsing=False)`. Keeps ordered duplicate pairs and blank values; URL decoding follows the standard library, including `+` as space. `Final` rejects subclassing with `TypeError`.

```python
__slots__ = ("_index", "_items")
```

#### QueryParams.__init__

```python
def __init__(self, query_string: str) -> None:
```

Parameters:

- `query_string` (`str`): URL query string to decode.

Parses `query_string`, builds a separate last/multiple-value index and returns `None`.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `None`.

#### QueryParams.get

```python
def get(self, key: str, default: str | None = None) -> str | None:
```

Parameters:

- `key` (`str`): Name to retrieve or test; case rules are described on the class.
- `default` (`str | None`): Fallback for an absent name.

Returns the last value for case-sensitive `key`, or `default`.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `str | None`.

#### QueryParams.getAll

```python
def getAll(self, key: str) -> list[str]:
```

Parameters:

- `key` (`str`): Name to retrieve or test; case rules are described on the class.

Returns a new ordered list of values for `key`, or `[]`.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `list[str]`.

#### QueryParams.getList

```python
def getList(self, key: str) -> list[str]:
```

Parameters:

- `key` (`str`): Name to retrieve or test; case rules are described on the class.

Alias delegating to `getAll(key)`; returns the same kind of copied list.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `list[str]`.

#### QueryParams.multiItems

```python
def multiItems(self) -> list[tuple[str, str]]:
```

Returns a shallow copy of all ordered pairs, including duplicates.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `list[tuple[str, str]]`.

#### QueryParams.__contains__

```python
def __contains__(self, key: str) -> bool:
```

Parameters:

- `key` (`str`): Name to retrieve or test; case rules are described on the class.

Returns whether case-sensitive `key` is in the index.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `bool`.

#### QueryParams.__getitem__

```python
def __getitem__(self, key: str) -> str:
```

Parameters:

- `key` (`str`): Name to retrieve or test; case rules are described on the class.

Returns the last value for `key`.

Exceptions: `KeyError(key)` when absent.

Declared return/yield type: `str`.

#### QueryParams.items

```python
def items(self) -> list[tuple[str, str]]:
```

Returns a shallow copy of all pairs, equivalent to `multiItems()`.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `list[tuple[str, str]]`.

#### QueryParams.keys

```python
def keys(self) -> set[str]:
```

Returns a new set of unique parameter names.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `set[str]`.

#### QueryParams.values

```python
def values(self) -> list[str]:
```

Returns a new list of all values in pair order, including duplicates.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `list[str]`.

#### QueryParams.__iter__

```python
def __iter__(self) -> Iterator[tuple[str, str]]:
```

Returns an iterator of all `(key, value)` pairs, including duplicates.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `Iterator[tuple[str, str]]`.

#### QueryParams.__len__

```python
def __len__(self) -> int:
```

Returns the total number of pairs, including repeated names.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `int`.

#### QueryParams.__repr__

```python
def __repr__(self) -> str:
```

Returns `QueryParams(...)` with its ordered pairs.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `str`.

<a id="api-068"></a>

### FormData

Source: [form_data.py](../payload/form_data.py).

```python
class FormData(IFormData):
```

Ordered multipart pairs with a separate index of unique names. Constructor copies the outer list, while uploaded files remain shared objects. Text fields are recognized with `isinstance(value, str)`; every other value is treated as a file. Access uses the last value for repeated names. It has a synchronous context manager.

```python
__slots__ = ("_index", "_items")
```

#### FormData.__init__

```python
def __init__(
    self,
    items: list[tuple[str, str | UploadedFile]],
) -> None:
```

Parameters:

- `items` (`list[tuple[str, str | UploadedFile]]`): Ordered multipart `(name, value)` pairs.

Copies `items`, builds the name index, and returns `None`; repeated names preserve insertion order.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `None`.

#### FormData.fields

```python
@property
def fields(self) -> dict[str, list[str]]:
```

Property: returns a new dictionary and new lists grouping only string values by field name. Does not mutate stored pairs.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `dict[str, list[str]]`.

#### FormData.files

```python
@property
def files(self) -> dict[str, list[UploadedFile]]:
```

Property: returns a new dictionary and new lists grouping non-string values; the `UploadedFile` objects themselves are shared.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `dict[str, list[UploadedFile]]`.

#### FormData.get

```python
def get(
    self,
    key: str,
    default: object | None = None,
) -> object | None:
```

Parameters:

- `key` (`str`): Name to retrieve or test; case rules are described on the class.
- `default` (`object | None`): Fallback for an absent name.

Returns the last value for `key`, or `default` when absent. Read-only; the returned file object is shared.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `object | None`.

#### FormData.getAll

```python
def getAll(self, key: str) -> list[str | UploadedFile]:
```

Parameters:

- `key` (`str`): Name to retrieve or test; case rules are described on the class.

Returns a new list with every value for `key` in insertion order, or `[]`; file objects are shared.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `list[str | UploadedFile]`.

#### FormData.allItems

```python
@property
def allItems(self) -> list[tuple[str, str | UploadedFile]]:
```

Property: returns the actual internal list, without copying. The docstring says callers must not mutate it: mutating it can leave the separate lookup index inconsistent.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `list[tuple[str, str | UploadedFile]]`.

#### FormData.multiItems

```python
def multiItems(self) -> list[tuple[str, str | UploadedFile]]:
```

Returns a shallow copy of all ordered pairs.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `list[tuple[str, str | UploadedFile]]`.

#### FormData.__getitem__

```python
def __getitem__(self, key: str) -> object:
```

Parameters:

- `key` (`str`): Name to retrieve or test; case rules are described on the class.

Delegates to `get(key)` and returns the last value. A missing key returns `None`, without raising `KeyError`.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `object`.

#### FormData.__contains__

```python
def __contains__(self, key: str) -> bool:
```

Parameters:

- `key` (`str`): Name to retrieve or test; case rules are described on the class.

Returns whether the name `key` exists in the index.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `bool`.

#### FormData.__iter__

```python
def __iter__(self) -> Iterator[str]:
```

Returns an iterator over unique names in first-seen order.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `Iterator[str]`.

#### FormData.__len__

```python
def __len__(self) -> int:
```

Returns the number of unique names, not the number of stored pairs.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `int`.

#### FormData.__repr__

```python
def __repr__(self) -> str:
```

Returns `FormData(...)` containing the representation of all stored pairs.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `str`.

#### FormData.close

```python
def close(self) -> None:
```

Calls `close()` on every non-string value and returns `None`; does not remove pairs or deduplicate repeated file handles.

Exceptions: A delegated close failure propagates and interrupts cleanup of later items.

Declared return/yield type: `None`.

#### FormData.__enter__

```python
def __enter__(self) -> Self:
```

Returns this instance (`Self`).

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `Self`.

#### FormData.__exit__

```python
def __exit__(
    self,
    exc_type: type[BaseException] | None,
    exc_val: BaseException | None,
    exc_tb: TracebackType | None,
) -> None:
```

Parameters:

- `exc_type` (`type[BaseException] | None`): Context-body exception class, or `None`.
- `exc_val` (`BaseException | None`): Context-body exception instance, or `None`.
- `exc_tb` (`TracebackType | None`): Context-body traceback, or `None`.

Ignores the exception arguments, calls `close()` and returns `None`; exceptions from the context body are not suppressed.

Exceptions: Propagates cleanup errors from `close()`.

Declared return/yield type: `None`.

<a id="api-069"></a>

### MediaTypeRegistry

Source: [media_types.py](../payload/media_types.py).

```python
class MediaTypeRegistry(IMediaTypeRegistry):
```

Mutable mapping of lowercased media types to synchronous parsers. It lowercases keys but does not strip parameters, whitespace or vendor suffixes. It does not execute parsers or validate callability. `extend()` creates an independent mapping, while callable objects are shared.

```python
__slots__ = ("_parsers",)
```

#### MediaTypeRegistry.__init__

```python
def __init__(self, parsers: dict[str, BodyParser] | None = None) -> None:
```

Parameters:

- `parsers` (`dict[str, BodyParser] | None`): Media-type to synchronous parser mapping.

Copies `parsers` with lowercase keys, or creates an empty mapping for `None`/an empty mapping; returns `None`.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `None`.

#### MediaTypeRegistry.register

```python
def register(self, media_type: str, parser: BodyParser) -> None:
```

Parameters:

- `media_type` (`str`): Media-type lookup/registration key.
- `parser` (`BodyParser`): Synchronous bytes-to-object callable.

Adds or overwrites `media_type.lower()` with `parser` in this registry; returns `None`.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `None`.

#### MediaTypeRegistry.get

```python
def get(self, media_type: str) -> BodyParser | None:
```

Parameters:

- `media_type` (`str`): Media-type lookup/registration key.

Returns the registered parser for `media_type.lower()`, or `None`; does not invoke it.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `BodyParser | None`.

#### MediaTypeRegistry.extend

```python
def extend(self, parsers: dict[str, BodyParser]) -> MediaTypeRegistry:
```

Parameters:

- `parsers` (`dict[str, BodyParser]`): Media-type to synchronous parser mapping.

Returns a new `MediaTypeRegistry`, with normalized entries from `parsers` taking precedence; leaves the original registry unchanged.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `MediaTypeRegistry`.

<a id="api-070"></a>

### BodyParser

Sources: [media_types.py](../payload/media_types.py), [contracts/media_types.py](../payload/contracts/media_types.py).

```python
BodyParser = Callable[[bytes], object]
```

Identical alias defined in both modules: a synchronous callable receiving one `bytes` value and returning `object`; it supplies no runtime validation.

<a id="api-071"></a>

### DEFAULT_MEDIA_TYPES

Source: [media_types.py](../payload/media_types.py).

```python
DEFAULT_MEDIA_TYPES: MediaTypeRegistry = MediaTypeRegistry(
    {
        "application/json": parse_json,
        "application/x-www-form-urlencoded": parse_urlencoded,
        "application/msgpack": parse_msgpack,
        "application/xml": parse_xml,
        "text/xml": parse_xml,
        "text/html": parse_text,
        "text/plain": parse_text,
        "application/javascript": parse_text,
        "text/javascript": parse_text,
        "application/octet-stream": parse_binary,
    },
)
```

Module-level mutable singleton. Calling `register()` on this object changes shared defaults. It contains no multipart parser, suffix matching or `parse_urlencoded_multi` entry.

<a id="api-072"></a>

### parse_content_type

Source: [parsers.py](../payload/parsers.py).

```python
def parse_content_type(header: str) -> tuple[str, dict[str, str]]:
```

Parameters:

- `header` (`str`): Raw Content-Type string.

Returns `(media_type, params)` from `header`: strips/lowercases the media type and parameter names, strips whitespace and surrounding double-quote characters from parameter values, and lets the last duplicate win. Parameter separators are semicolons outside double-quoted values, so `boundary="a;b"` remains one parameter. Escaped characters inside quotes cannot close the quoted value; their backslashes are retained by this parser. Segments without `=` are ignored. Does not change the input.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `tuple[str, dict[str, str]]`.

**Internal `_split_header_parameters`**

```python
def _split_header_parameters(
    header: str, *, quote_chars: str = '"',
) -> list[str]:
```

`header: str` is header/parameter text; keyword-only `quote_chars: str = '"'` selects allowed quote delimiters. Returns a new `list[str]` of original segments with separating semicolons removed and whitespace, quotes and escapes preserved. A quote opens only at the first non-whitespace character after the first `=` in a segment; apostrophes inside unquoted values, including RFC 5987 charset/language separators, do not open quotes. Within a quoted value, a backslash protects the following character from closing it. An unclosed quoted value consumes the remainder of the header. The helper neither unquotes nor unescapes, mutates no input and performs no I/O; it contains no explicit `raise`. `parse_content_type` uses double quotes; `MultipartPart` enables both single and double quotes and applies its own value decoding.

<a id="api-073"></a>

### parse_json

Source: [parsers.py](../payload/parsers.py).

```python
def parse_json(raw: bytes) -> object:
```

Parameters:

- `raw` (`bytes`): Raw payload bytes.

Returns the Python object decoded from `raw` by `msgspec.json.decode`; has no module-state mutation.

Exceptions: `msgspec.DecodeError` for invalid JSON, propagated from the decoder.

Declared return/yield type: `object`.

<a id="api-074"></a>

### parse_msgpack

Source: [parsers.py](../payload/parsers.py).

```python
def parse_msgpack(raw: bytes) -> object:
```

Parameters:

- `raw` (`bytes`): Raw payload bytes.

Returns the Python object decoded from `raw` by `msgspec.msgpack.decode`; has no module-state mutation.

Exceptions: `msgspec.DecodeError` for invalid MessagePack, propagated from the decoder.

Declared return/yield type: `object`.

<a id="api-075"></a>

### parse_urlencoded

Source: [parsers.py](../payload/parsers.py).

```python
def parse_urlencoded(raw: bytes) -> dict[str, str]:
```

Parameters:

- `raw` (`bytes`): Raw payload bytes.

Strictly decodes `raw` as UTF-8, then calls `parse_qsl(..., keep_blank_values=True)` and constructs a dictionary. Blank values are retained; repeated names keep the last value. URL parsing uses the standard-library defaults, including `+` as a space.

Exceptions: `UnicodeDecodeError` when the initial UTF-8 decode fails.

Declared return/yield type: `dict[str, str]`.

<a id="api-076"></a>

### parse_urlencoded_multi

Source: [parsers.py](../payload/parsers.py).

```python
def parse_urlencoded_multi(raw: bytes) -> dict[str, str | list[str]]:
```

Parameters:

- `raw` (`bytes`): Raw payload bytes.

Returns decoded form fields, keeping single occurrences as `str` and repeated names as ordered `list[str]`. Preserves blanks and shares the UTF-8 and query parsing behavior of `parse_urlencoded`.

Exceptions: `UnicodeDecodeError` when the initial UTF-8 decode fails.

Declared return/yield type: `dict[str, str | list[str]]`.

<a id="api-077"></a>

### parse_xml

Source: [parsers.py](../payload/parsers.py).

```python
def parse_xml(raw: bytes) -> XMLElement:
```

Parameters:

- `raw` (`bytes`): Raw payload bytes.

Returns an `xml.etree.ElementTree.Element` by calling `defusedxml.ElementTree.fromstring(raw)` with no options. The installed dependency source sets `forbid_dtd=False`, `forbid_entities=True` and `forbid_external=True`. Internal and external entity declarations are rejected; DTDs without entity declarations are allowed, and external resources are not resolved. No filesystem or network fetching is implemented by this wrapper.

Exceptions: `xml.etree.ElementTree.ParseError` for malformed XML; `defusedxml.common.EntitiesForbidden` for internal or external entity declarations. `EntitiesForbidden` is a subclass of `defusedxml.common.DefusedXmlException` and is not a `ParseError`. These exceptions propagate unchanged.

Declared return/yield type: `XMLElement`.

<a id="api-078"></a>

### parse_text

Source: [parsers.py](../payload/parsers.py).

```python
def parse_text(raw: bytes) -> str:
```

Parameters:

- `raw` (`bytes`): Raw payload bytes.

Returns the strict UTF-8 decoding of `raw`; no state mutation.

Exceptions: `UnicodeDecodeError` for invalid UTF-8.

Declared return/yield type: `str`.

<a id="api-079"></a>

### parse_binary

Source: [parsers.py](../payload/parsers.py).

```python
def parse_binary(raw: bytes) -> bytes:
```

Parameters:

- `raw` (`bytes`): Raw payload bytes.

Returns `raw` unchanged, preserving object identity; no state mutation.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `bytes`.

<a id="api-080"></a>

### UploadedFile

Source: [uploaded_file.py](../payload/uploaded_file.py).

```python
class UploadedFile(IUploadedFile):
```

Synchronous wrapper around `tempfile.SpooledTemporaryFile`; starts in memory and can roll over to disk. Public `filename` is sanitized and `content_type: str | None` preserves client metadata without inspecting content. The extension is computed once, so changing `filename` later does not recompute it. There is no context-manager protocol on this class; `FormData` provides cleanup.

```python
__slots__ = (
        "_extension",
        "_file",
        "_memory_threshold",
        "_rolled",
        "_size",
        "content_type",
        "filename",
    )
```

#### UploadedFile.__init__

```python
def __init__(
    self,
    filename: str,
    content_type: str | None,
    memory_threshold: int = 1024 * 1024,
) -> None:
```

Parameters:

- `filename` (`str`): Client-supplied filename to sanitize.
- `content_type` (`str | None`): Client-declared MIME type or `None`.
- `memory_threshold` (`int`): Per-file spool size threshold in bytes.

Normalizes path separators, retains the last path component, strips control/forbidden characters and leading dots, and falls back to `"upload"`. Creates the spool, initializes byte count/rollover state and caches a lowercase suffix; returns `None`. The sanitizer does not validate every OS-reserved filename (for example, device names). `memory_threshold=0` disables automatic size-based rollover in the spool.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `None`.

#### UploadedFile.requiresDiskWrite

```python
def requiresDiskWrite(self, size: int = 0) -> bool:
```

Parameters:

- `size` (`int`): Prospective write byte count.

Returns `_rolled` or whether a nonzero threshold would be exceeded by the current byte counter plus `size`; read-only. It uses the tracked counter, not the underlying file position.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `bool`.

#### UploadedFile.write

```python
def write(self, chunk: bytes | bytearray | memoryview) -> None:
```

Parameters:

- `chunk` (`bytes | bytearray | memoryview`): Byte sequence to write.

Seeks to EOF with `seek(0, SEEK_END)` and appends `chunk`, preserving existing content after partial `chunks()` reads both in memory and on disk. Updates predicted rollover state before writing and increments the byte counter by `len(chunk)` after a successful write; returns `None`. The shared file cursor finishes at EOF, including when a `chunks()` iterator is suspended.

Exceptions: Delegated seek/write errors, including `ValueError` after closure. Rollover tracking is updated after seeking and before writing; the byte counter increases only after the write succeeds.

Declared return/yield type: `None`.

#### UploadedFile.size

```python
@property
def size(self) -> int:
```

Property returning the tracked byte count; writes increase it and `replace()` resets it to the replacement length.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `int`.

#### UploadedFile.extension

```python
@property
def extension(self) -> str:
```

Property returning the cached lowercase last suffix with its dot, or `""` when no dot occurs after the first filename character.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `str`.

#### UploadedFile.read

```python
def read(self) -> bytes:
```

Seeks to position zero, reads all content into `bytes`, and leaves the position after the read.

Exceptions: Delegated file I/O errors, including `ValueError` after closure.

Declared return/yield type: `bytes`.

#### UploadedFile.chunks

```python
def chunks(self, size: int = _CHUNK_SIZE) -> Iterator[bytes]:
```

Parameters:

- `size` (`int`): Maximum bytes requested per read.

Generator that rewinds when iteration begins, then yields successive reads of `size` bytes. Default `_CHUNK_SIZE` is `64 * 1024`. It does not validate positive sizes: zero yields nothing and a negative size delegates a full read to the backing file. Iteration changes the shared file position.

Exceptions: Delegated read/seek errors, including `ValueError` after closure.

Declared return/yield type: `Iterator[bytes]`.

#### UploadedFile.replace

```python
def replace(self, data: bytes) -> None:
```

Parameters:

- `data` (`bytes`): Replacement bytes.

Seeks to zero, truncates, writes `data` and sets `size` to `len(data)`; returns `None`. A disk-backed file stays disk-backed. Replacement is not atomic: an error can occur after truncation.

Exceptions: Delegated file I/O errors, including `ValueError` after closure.

Declared return/yield type: `None`.

#### UploadedFile.save

```python
def save(self, path: str | Path) -> None:
```

Parameters:

- `path` (`str | Path`): Filesystem destination.

Builds `Path(path)`, rewinds the spool, then opens the destination in `wb` mode (creating or truncating it) and copies in 64 KiB chunks; returns `None`. It does not create parent directories, sanitize `path`, close the upload, or guarantee an atomic destination write.

Exceptions: Filesystem errors such as `FileNotFoundError`, `PermissionError` and other `OSError`; read/seek errors after closure.

Declared return/yield type: `None`.

#### UploadedFile.close

```python
def close(self) -> None:
```

Closes the spool and releases its backing temporary file; returns `None`.

Exceptions: Delegated cleanup/I/O errors are not caught.

Declared return/yield type: `None`.

#### UploadedFile.__del__

```python
def __del__(self) -> None:
```

Calls `close()` during finalization and suppresses `Exception`; returns `None`.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `None`.

<a id="api-081"></a>

### MultipartPart

Source: [part.py](../payload/part.py).

```python
class MultipartPart(IMultipartPart):
```

Represents one multipart part. Public attributes are `headers` (the original dictionary), `name: str | None`, `filename: str | None`, `content_type: str | None`, `is_file: bool` and `data: UploadedFile | bytearray`. A declared filename, including an empty string, selects a file. `filename` retains the parsed value, while `data.filename` is sanitized by `UploadedFile`.

```python
__slots__ = (
        "_write",
        "content_type",
        "data",
        "filename",
        "headers",
        "is_file",
        "name",
    )
```

#### MultipartPart.__init__

```python
def __init__(
    self,
    headers: dict[str, str],
    memory_threshold: int,
) -> None:
```

Parameters:

- `headers` (`dict[str, str]`): MIME headers with lowercase keys.
- `memory_threshold` (`int`): Per-file spool size threshold in bytes.

Stores `headers`, parses `content-disposition` and creates either an `UploadedFile` using `memory_threshold`, or a `bytearray`; returns `None`. Header keys must already be lowercase. The private `_parseContentDisposition` uses `_split_header_parameters` to split only at semicolons outside single- or double-quoted values, preserving values such as `filename="a;b.txt"`. It strips matching quotes, unescapes quotes and prefers successfully decoded RFC 5987 `name*`/`filename*` values over plain attributes. Escaped quotes do not close a quoted segment, and apostrophes within unquoted values or RFC 5987 syntax do not open one. Errors decoding extended attributes are suppressed.

Exceptions: No explicit `raise` in this operation; failures of called operations are not intercepted unless described above.

Declared return/yield type: `None`.

#### MultipartPart.write

```python
def write(self, chunk: bytes | bytearray | memoryview) -> None:
```

Parameters:

- `chunk` (`bytes | bytearray | memoryview`): Byte sequence to write.

Passes `chunk` to the writer selected at construction: `UploadedFile.write` or `bytearray.extend`; returns `None` and accumulates part data.

Exceptions: Propagates file write failures for file parts.

Declared return/yield type: `None`.

#### MultipartPart.finalize

```python
def finalize(self) -> UploadedFile | str:  # NOSONAR
```

Returns a decoded string for fields or the same `UploadedFile` for files. Handles case-insensitive `base64` and `quoted-printable` content-transfer encoding. Fields use the first `charset=` substring found in `content-type`, otherwise UTF-8, with strict decoding. Files with these encodings are read completely, decoded and replaced in place. Repeated finalization of an encoded file decodes its already replaced content again; no completed flag exists.

Exceptions: `UnicodeDecodeError` for invalid field text; `LookupError` for an unknown charset; base64 decoding errors (`binascii.Error`) for invalid padding/encoding; delegated file I/O failures.

Declared return/yield type: `UploadedFile | str`.

<a id="api-082"></a>

### complete_in_thread

Source: [stream_parser.py](../payload/stream_parser.py).

```python
async def complete_in_thread[T](function: Callable[..., T], *args: object) -> T:
```

Parameters:

- `function` (`Callable[..., T]`): Blocking callable to run in a worker.
- `args` (`object`): Positional arguments forwarded to `function`.

Runs `function(*args)` with `asyncio.to_thread`, creates a task and awaits it through `shield`; returns its result `T`. On cancellation it awaits the task and re-raises cancellation when the worker finishes successfully. This keeps a worker using the multipart memoryview alive until completion before parser cleanup under a single cancellation.

Exceptions: Worker exceptions propagate; a worker failure while awaiting cancellation can replace `CancelledError`. A further cancellation during the unshielded `await task` is suppressed there; the function does not implement a loop ensuring worker completion under repeated cancellation.

Declared return/yield type: `T`.

<a id="api-083"></a>

### MultipartStreamParser

Source: [stream_parser.py](../payload/stream_parser.py).

```python
class MultipartStreamParser(IMultipartStreamParser):
```

Stateful async multipart parser over a supplied byte stream. Constructor attributes expose `stream`, prefixed `boundary`, mutable `buffer`, limits and counters (`files_count`, `fields_count`, `current_part_size`). Boundary search recognizes CRLF delimiters, optional spaces/tabs and a closing delimiter, including a final close at EOF; incomplete input is rejected. It may finish without exhausting the supplied stream once the closing delimiter is recognized. It does not reset state for another parse.

```python
__slots__ = (
        "_atStart",
        "_currentPart",
        "_eof",
        "_headerSearch",
        "_paddingEnd",
        "_paddingStart",
        "boundary",
        "buffer",
        "current_part_size",
        "fields_count",
        "files_count",
        "max_fields",
        "max_files",
        "max_header_size",
        "max_part_size",
        "memory_threshold",
        "stream",
    )
```

#### MultipartStreamParser.__init__

```python
def __init__(  # noqa: PLR0913
    self,
    stream: AsyncIterable[bytes],
    boundary: bytes,
    *,
    max_files: int = 1000,
    max_fields: int = 1000,
    max_part_size: int = 1024 * 1024 * 10,
    memory_threshold: int = 1024 * 1024,
    max_header_size: int = 64 * 1024,
) -> None:
```

Parameters:

- `stream` (`AsyncIterable[bytes]`): Async iterable of multipart bytes.
- `boundary` (`bytes`): Raw boundary token, without the leading `--`.
- `max_files` (`int`): Maximum accepted file-part count.
- `max_fields` (`int`): Maximum accepted text-field count.
- `max_part_size` (`int`): Maximum raw bytes in one part.
- `memory_threshold` (`int`): Per-file spool size threshold in bytes.
- `max_header_size` (`int`): Header-block limit and delimiter trailing-line limit, in bytes.

Stores `stream`, sets `boundary = b"--" + boundary`, allocates the working bytearray and initializes counters; returns `None`. All limits are stored as supplied, with no positivity checks. `max_part_size` counts incoming bytes before transfer-encoding decoding. `memory_threshold` applies to files only.

Exceptions: `ValueError("Missing multipart boundary")` for a false/empty boundary.

Declared return/yield type: `None`.

#### MultipartStreamParser.parse

```python
async def parse(self) -> FormData:
```

Consumes the async stream and returns `FormData` retaining ordered fields and files. Part headers are decoded as Latin-1; keys are lowercased, duplicate header names overwrite earlier ones, and lines without a colon are ignored. Requires a `name` attribute (an empty name is accepted). Private `_writePart` enforces the raw part-size limit; disk writes and disk-backed encoded-file finalization run through `complete_in_thread`. On `BaseException`, it closes the current uploaded file and collected file values before re-raising; successful callers own `FormData` cleanup.

Exceptions: `ValueError`: missing name, too many files/fields, part size above maximum, header block above maximum, delimiter trailing line above `max_header_size`, missing current part, or incomplete body. Propagates transport errors, cancellation, decoding and I/O failures. Cleanup errors can interrupt cleanup and replace the original failure.

Declared return/yield type: `FormData`.

<a id="api-084"></a>

### IBodyStream

Source: [contracts/body_stream.py](../payload/contracts/body_stream.py).

```python
class IBodyStream(ABC):
```

`ABC` contract for raw-body buffering and replay; implemented by `BodyStream`. Every listed member is abstract, and this class has `__slots__ = ()`. Instantiating it with unresolved abstract methods raises `TypeError`. It defines no constructor.

#### IBodyStream.isBuffered

```python
@property
@abstractmethod
def isBuffered(self) -> bool:
```

Abstract contract; parameter and return intent follows the corresponding `BodyStream.isBuffered` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `bool`.

#### IBodyStream.isConsumed

```python
@property
@abstractmethod
def isConsumed(self) -> bool:
```

Abstract contract; parameter and return intent follows the corresponding `BodyStream.isConsumed` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `bool`.

#### IBodyStream.stream

```python
@abstractmethod
async def stream(self) -> AsyncGenerator[bytes]:  # NOSONAR
```

Abstract contract; parameter and return intent follows the corresponding `BodyStream.stream` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Its docstring declares `RuntimeError` for unbuffered reconsumption and `PayloadTooLargeException` for a size-limit violation; this abstract body raises neither.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `AsyncGenerator[bytes]`.

#### IBodyStream.read

```python
@abstractmethod
async def read(self) -> bytes:
```

Abstract contract; parameter and return intent follows the corresponding `BodyStream.read` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `bytes`.

<a id="api-085"></a>

### IFormData

Source: [contracts/form_data.py](../payload/contracts/form_data.py).

```python
class IFormData(ABC):
```

`ABC` contract for ordered multipart fields/files and cleanup; implemented by `FormData`. Every listed member is abstract, and this class has `__slots__ = ()`. Instantiating it with unresolved abstract methods raises `TypeError`. It defines no constructor.

#### IFormData.fields

```python
@property
@abstractmethod
def fields(self) -> dict[str, list[str]]:
```

Abstract contract; parameter and return intent follows the corresponding `FormData.fields` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `dict[str, list[str]]`.

#### IFormData.files

```python
@property
@abstractmethod
def files(self) -> dict[str, list[UploadedFile]]:
```

Abstract contract; parameter and return intent follows the corresponding `FormData.files` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `dict[str, list[UploadedFile]]`.

#### IFormData.allItems

```python
@property
@abstractmethod
def allItems(self) -> list[tuple[str, str | UploadedFile]]:
```

Abstract contract; parameter and return intent follows the corresponding `FormData.allItems` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `list[tuple[str, str | UploadedFile]]`.

#### IFormData.get

```python
@abstractmethod
def get(
    self,
    key: str,
    default: object | None = None,
) -> object | None:
```

Parameters:

- `key` (`str`): Name to retrieve or test; case rules are described on the class.
- `default` (`object | None`): Fallback for an absent name.

Abstract contract; parameter and return intent follows the corresponding `FormData.get` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `object | None`.

#### IFormData.getAll

```python
@abstractmethod
def getAll(self, key: str) -> list[str | UploadedFile]:
```

Parameters:

- `key` (`str`): Name to retrieve or test; case rules are described on the class.

Abstract contract; parameter and return intent follows the corresponding `FormData.getAll` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `list[str | UploadedFile]`.

#### IFormData.multiItems

```python
@abstractmethod
def multiItems(self) -> list[tuple[str, str | UploadedFile]]:
```

Abstract contract; parameter and return intent follows the corresponding `FormData.multiItems` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `list[tuple[str, str | UploadedFile]]`.

#### IFormData.close

```python
@abstractmethod
def close(self) -> None:
```

Abstract contract; parameter and return intent follows the corresponding `FormData.close` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `None`.

#### IFormData.__getitem__

```python
@abstractmethod
def __getitem__(self, key: str) -> object:
```

Parameters:

- `key` (`str`): Name to retrieve or test; case rules are described on the class.

Abstract contract; parameter and return intent follows the corresponding `FormData.__getitem__` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `object`.

#### IFormData.__contains__

```python
@abstractmethod
def __contains__(self, key: str) -> bool:
```

Parameters:

- `key` (`str`): Name to retrieve or test; case rules are described on the class.

Abstract contract; parameter and return intent follows the corresponding `FormData.__contains__` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `bool`.

#### IFormData.__iter__

```python
@abstractmethod
def __iter__(self) -> Iterator[str]:
```

Abstract contract; parameter and return intent follows the corresponding `FormData.__iter__` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `Iterator[str]`.

#### IFormData.__len__

```python
@abstractmethod
def __len__(self) -> int:
```

Abstract contract; parameter and return intent follows the corresponding `FormData.__len__` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `int`.

#### IFormData.__repr__

```python
@abstractmethod
def __repr__(self) -> str:
```

Abstract contract; parameter and return intent follows the corresponding `FormData.__repr__` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `str`.

#### IFormData.__enter__

```python
@abstractmethod
def __enter__(self) -> Self:
```

Abstract contract; parameter and return intent follows the corresponding `FormData.__enter__` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `Self`.

#### IFormData.__exit__

```python
@abstractmethod
def __exit__(
    self,
    exc_type: type[BaseException] | None,
    exc_val: BaseException | None,
    exc_tb: TracebackType | None,
) -> None:
```

Parameters:

- `exc_type` (`type[BaseException] | None`): Context-body exception class, or `None`.
- `exc_val` (`BaseException | None`): Context-body exception instance, or `None`.
- `exc_tb` (`TracebackType | None`): Context-body traceback, or `None`.

Abstract contract; parameter and return intent follows the corresponding `FormData.__exit__` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `None`.

<a id="api-086"></a>

### IMediaTypeRegistry

Source: [contracts/media_types.py](../payload/contracts/media_types.py).

```python
class IMediaTypeRegistry(ABC):
```

`ABC` contract for media-type parser registration and extension; implemented by `MediaTypeRegistry`. Every listed member is abstract, and this class has `__slots__ = ()`. Instantiating it with unresolved abstract methods raises `TypeError`. It defines no constructor.

#### IMediaTypeRegistry.register

```python
@abstractmethod
def register(self, media_type: str, parser: BodyParser) -> None:
```

Parameters:

- `media_type` (`str`): Media-type lookup/registration key.
- `parser` (`BodyParser`): Synchronous bytes-to-object callable.

Abstract contract; parameter and return intent follows the corresponding `MediaTypeRegistry.register` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `None`.

#### IMediaTypeRegistry.get

```python
@abstractmethod
def get(self, media_type: str) -> BodyParser | None:
```

Parameters:

- `media_type` (`str`): Media-type lookup/registration key.

Abstract contract; parameter and return intent follows the corresponding `MediaTypeRegistry.get` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `BodyParser | None`.

#### IMediaTypeRegistry.extend

```python
@abstractmethod
def extend(self, parsers: dict[str, BodyParser]) -> IMediaTypeRegistry:
```

Parameters:

- `parsers` (`dict[str, BodyParser]`): Media-type to synchronous parser mapping.

Abstract contract; parameter and return intent follows the corresponding `MediaTypeRegistry.extend` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `IMediaTypeRegistry`.

<a id="api-087"></a>

### IUploadedFile

Source: [contracts/uploaded_file.py](../payload/contracts/uploaded_file.py).

```python
class IUploadedFile(ABC):
```

`ABC` contract for uploaded-file content and resource management; implemented by `UploadedFile`. Every listed member is abstract, and this class has `__slots__ = ()`. Instantiating it with unresolved abstract methods raises `TypeError`. It defines no constructor.

#### IUploadedFile.size

```python
@property
@abstractmethod
def size(self) -> int:
```

Abstract contract; parameter and return intent follows the corresponding `UploadedFile.size` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `int`.

#### IUploadedFile.extension

```python
@property
@abstractmethod
def extension(self) -> str:
```

Abstract contract; parameter and return intent follows the corresponding `UploadedFile.extension` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `str`.

#### IUploadedFile.write

```python
@abstractmethod
def write(self, chunk: bytes | bytearray | memoryview) -> None:
```

Parameters:

- `chunk` (`bytes | bytearray | memoryview`): Byte sequence to write.

Abstract contract; parameter and return intent follows the corresponding `UploadedFile.write` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `None`.

#### IUploadedFile.read

```python
@abstractmethod
def read(self) -> bytes:
```

Abstract contract; parameter and return intent follows the corresponding `UploadedFile.read` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `bytes`.

#### IUploadedFile.chunks

```python
@abstractmethod
def chunks(self, size: int = 65536) -> Iterator[bytes]:
```

Parameters:

- `size` (`int`): Maximum bytes requested per read.

Abstract contract; parameter and return intent follows the corresponding `UploadedFile.chunks` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `Iterator[bytes]`.

#### IUploadedFile.replace

```python
@abstractmethod
def replace(self, data: bytes) -> None:
```

Parameters:

- `data` (`bytes`): Replacement bytes.

Abstract contract; parameter and return intent follows the corresponding `UploadedFile.replace` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `None`.

#### IUploadedFile.save

```python
@abstractmethod
def save(self, path: str | Path) -> None:
```

Parameters:

- `path` (`str | Path`): Filesystem destination.

Abstract contract; parameter and return intent follows the corresponding `UploadedFile.save` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `None`.

#### IUploadedFile.close

```python
@abstractmethod
def close(self) -> None:
```

Abstract contract; parameter and return intent follows the corresponding `UploadedFile.close` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `None`.

<a id="api-088"></a>

### IMultipartPart

Source: [contracts/part.py](../payload/contracts/part.py).

```python
class IMultipartPart(ABC):
```

`ABC` contract for multipart byte accumulation and finalization; implemented by `MultipartPart`. Every listed member is abstract, and this class has `__slots__ = ()`. Instantiating it with unresolved abstract methods raises `TypeError`. It defines no constructor.

#### IMultipartPart.write

```python
@abstractmethod
def write(self, chunk: bytes | bytearray | memoryview) -> None:
```

Parameters:

- `chunk` (`bytes | bytearray | memoryview`): Byte sequence to write.

Abstract contract; parameter and return intent follows the corresponding `MultipartPart.write` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `None`.

#### IMultipartPart.finalize

```python
@abstractmethod
def finalize(self) -> UploadedFile | str:
```

Abstract contract; parameter and return intent follows the corresponding `MultipartPart.finalize` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `UploadedFile | str`.

<a id="api-089"></a>

### IMultipartStreamParser

Source: [contracts/stream_parser.py](../payload/contracts/stream_parser.py).

```python
class IMultipartStreamParser(ABC):
```

`ABC` contract for async multipart parsing; implemented by `MultipartStreamParser`. Every listed member is abstract, and this class has `__slots__ = ()`. Instantiating it with unresolved abstract methods raises `TypeError`. It defines no constructor.

#### IMultipartStreamParser.parse

```python
@abstractmethod
async def parse(self) -> FormData:
```

Abstract contract; parameter and return intent follows the corresponding `MultipartStreamParser.parse` operation above. The annotation is reproduced literally. This body contains only its docstring and supplies no concrete implementation.

Concrete side effects and additional exceptions:

> ⚠️ No especificado en el código fuente

Declared return/yield type: `FormData`.

<a id="api-090"></a>

### TransportAdapter

Source: [adapters/request/contracts/transport.py](../adapters/request/contracts/transport.py).

```python
class TransportAdapter(ABC):

    @abstractmethod
    def client(self) -> str | None:

    @abstractmethod
    def setClient(self, ip: str) -> None:

    @abstractmethod
    def scheme(self) -> str | None:

    @abstractmethod
    def setScheme(self, value: str) -> None:

    @abstractmethod
    def method(self) -> str | None:

    @abstractmethod
    def path(self) -> str | None:

    @abstractmethod
    def headers(self) -> Headers:

    @abstractmethod
    def setState(self, key: str, value: Any) -> None:

    @abstractmethod
    def wantsJson(self) -> bool:

    @abstractmethod
    def getScope(self) -> dict:
```

Abstract, slotted request-transport contract (`ABC`). All ten methods are `@abstractmethod`; instantiating the class or an incomplete subclass raises `TypeError`. The method bodies contain only docstrings: they do not read or mutate a transport themselves.

| Method | Parameters and declared result |
| --- | --- |
| `client` | No arguments; remote address as `str \| None`. |
| `setClient` | `ip: str`, replacement address; returns `None`. |
| `scheme` | No arguments; URL scheme as `str \| None`. |
| `setScheme` | `value: str`, replacement scheme; returns `None`. |
| `method` | No arguments; HTTP method as `str \| None`. |
| `path` | No arguments; request path as `str \| None`. |
| `headers` | No arguments; parsed request `Headers`. |
| `setState` | `key: str`, state name; `value: Any`, stored value; returns `None`. |
| `wantsJson` | No arguments; JSON preference as `bool`. |
| `getScope` | No arguments; scope representation with overrides as `dict`. |

Concrete side effects, error conditions, and storage rules beyond these abstract declarations:

> ⚠️ No especificado en el código fuente

<a id="api-091"></a>

### ASGITransportAdapter

Source: [adapters/request/asgi.py](../adapters/request/asgi.py).

```python
class ASGITransportAdapter(TransportAdapter):

    def __init__(self, scope: dict) -> None:

    def __getitem__(self, key: str) -> object | None:

    def __setitem__(self, key: str, value: object) -> None:

    def __contains__(self, key: str) -> bool:

    def __delitem__(self, key: str) -> None:

    def client(self) -> str | None:

    def setClient(self, ip: str) -> None:

    def scheme(self) -> str | None:

    def setScheme(self, value: str) -> None:

    def method(self) -> str | None:

    def path(self) -> str | None:

    def headers(self) -> Headers:

    def setState(self, key: str, value: Any) -> None:

    def wantsJson(self) -> bool:

    def getScope(self) -> dict:
```

Wraps a caller-supplied `scope: dict` by reference, builds `Headers` by decoding raw byte pairs with Latin-1, and initializes per-instance overrides and lazy caches. Missing `headers` defaults to an empty sequence. Implements `TransportAdapter` with five slots.

| Method | Parameters, result, and state changes |
| --- | --- |
| `__getitem__` | `key: str`, override name; returns its `object` value or `None`, without falling back to the original scope. |
| `__setitem__` | `key: str` and `value: object`; writes an override, returns `None`. |
| `__contains__` | `key: str`; returns `bool` for override membership only. |
| `__delitem__` | `key: str`; removes an override if present, returns `None`; missing keys do not raise `KeyError`. |
| `client` | No arguments; lazily returns/caches the client address (`str \| None`) and stores parsed `client` and integer `port` overrides when available. |
| `setClient` | `ip: str`; updates both the address cache and `client` override, returns `None`; does not update `port`. |
| `scheme` | No arguments; `str \| None` from a non-`None` override, otherwise the original scope. |
| `setScheme` | `value: str`; writes the scheme override, returns `None`. |
| `method` | No arguments; `str \| None` from a non-`None` override, otherwise the original scope. |
| `path` | No arguments; `str \| None` read directly from the original scope, ignoring overrides. |
| `headers` | No arguments; returns the cached `Headers` object created by the constructor. |
| `setState` | `key: str` and `value: Any`; writes an override, returns `None`. |
| `wantsJson` | No arguments; caches a `bool` indicating whether the last `Accept` value, lowercased, contains `application/json` or `+json`; missing/empty values return `False`. It does not parse quality weights. |
| `getScope` | No arguments; returns a `dict` representing original fields plus overrides, as detailed below. |

The constructor and all mutators return `None`. No I/O or explicit locking occurs. Generic override writes/deletions do not synchronize the dedicated client or JSON caches: use `setClient` for address changes. Header overrides do not rebuild `headers()`. Apart from scope/header parsing errors described below, these methods contain no explicit raises.

`client()` expects `scope["client"]` to be a `(host, port)` pair; false/missing values return `None`. A malformed pair can raise `IndexError`/`TypeError`, and `int(port)` can raise `ValueError`/`TypeError`. Header pairs lacking byte-compatible `.decode()` raise `AttributeError`; malformed pair unpacking can raise `ValueError`.

`getScope()` returns the **original dictionary itself** while there are no overrides; otherwise it creates a shallow merged dictionary. The adapter does not directly rewrite the input dictionary, but callers can mutate the original through that returned reference. Reading `client()` can itself create overrides and change subsequent `getScope()` behavior.

<a id="api-092"></a>

### RSGITransportAdapter

Source: [adapters/request/rsgi.py](../adapters/request/rsgi.py).

```python
class RSGITransportAdapter(TransportAdapter):

    def __init__(self, scope: Scope) -> None:

    def __getitem__(self, key: str) -> object | None:

    def __setitem__(self, key: str, value: object) -> None:

    def __contains__(self, key: str) -> bool:

    def __delitem__(self, key: str) -> None:

    def client(self) -> str | None:

    def setClient(self, ip: str) -> None:

    def scheme(self) -> str | None:

    def setScheme(self, value: str) -> None:

    def method(self) -> str | None:

    def path(self) -> str | None:

    def headers(self) -> Headers:

    def setState(self, key: str, value: Any) -> None:

    def wantsJson(self) -> bool:

    def getScope(self) -> dict:
```

Wraps a Granian `scope: Scope` by reference. The constructor iterates `scope.headers`, flattens each `get_all(key)` collection into lowercase name/value pairs, builds `Headers`, and initializes five slots for scope, headers, overrides, and lazy caches.

| Method | Parameters, result, and state changes |
| --- | --- |
| `__getitem__` | `key: str`, override name; returns its `object` value or `None`, without falling back to the original scope. |
| `__setitem__` | `key: str` and `value: object`; writes an override, returns `None`. |
| `__contains__` | `key: str`; returns `bool` for override membership only. |
| `__delitem__` | `key: str`; removes an override if present, returns `None`; missing keys do not raise `KeyError`. |
| `client` | No arguments; lazily returns/caches the client address (`str \| None`) and stores parsed `client` and integer `port` overrides when available. |
| `setClient` | `ip: str`; updates both the address cache and `client` override, returns `None`; does not update `port`. |
| `scheme` | No arguments; `str \| None` from a non-`None` override, otherwise the original scope. |
| `setScheme` | `value: str`; writes the scheme override, returns `None`. |
| `method` | No arguments; `str \| None` from a non-`None` override, otherwise the original scope. |
| `path` | No arguments; `str \| None` read directly from the original scope, ignoring overrides. |
| `headers` | No arguments; returns the cached `Headers` object created by the constructor. |
| `setState` | `key: str` and `value: Any`; writes an override, returns `None`. |
| `wantsJson` | No arguments; caches a `bool` indicating whether the last `Accept` value, lowercased, contains `application/json` or `+json`; missing/empty values return `False`. It does not parse quality weights. |
| `getScope` | No arguments; returns a `dict` representing original fields plus overrides, as detailed below. |

The constructor and all mutators return `None`. No I/O or explicit locking occurs. Generic override writes/deletions do not synchronize the dedicated client or JSON caches: use `setClient` for address changes. Header overrides do not rebuild `headers()`. Apart from scope/header parsing errors described below, these methods contain no explicit raises.

`client()` splits the raw `scope.client` string at its last colon, removes surrounding IPv6 brackets from the host and converts the final component to `int`; false values return `None`. For example, `[::1]:8000` produces client `::1` and port `8000`, allowing the address to be checked against trusted proxy networks. IPv4 parsing, lazy caching and `setClient` overrides retain the behavior described above. Missing separators or nonnumeric ports raise `ValueError`; missing scope attributes/header methods raise `AttributeError`.

`getScope()` always creates a new dictionary with exactly the base fields `proto`, `http_version`, `rsgi_version`, `server`, `client`, `scheme`, `method`, `path`, `query_string`, `authority`, and `headers`, then applies overrides. Before client resolution, `client` is the original host/port string; afterward it is the cached address and `port` is added.

<a id="api-093"></a>

### ResponseAdapter

Source: [adapters/response/contracts/response.py](../adapters/response/contracts/response.py).

```python
class ResponseAdapter(ABC):

    @abstractmethod
    async def send(
        self,
        adapter: TransportAdapter,
        response: Response,
        *args: object,
        **kwargs: object,
    ) -> None:
```

Slotted abstract `ABC` for response delivery. `send` receives `adapter: TransportAdapter` for request method/headers, `response: Response` to deliver, and protocol-specific `*args: object` / `**kwargs: object`. Its declared asynchronous result is `None`. Instantiating this class or a subclass that leaves `send` abstract raises `TypeError`.

The abstract body only contains its docstring. Protocol-specific I/O, exceptions, and response mutation:

> ⚠️ No especificado en el código fuente

<a id="api-094"></a>

### ASGIResponseAdapter

Source: [adapters/response/asgi.py](../adapters/response/asgi.py).

```python
class ASGIResponseAdapter(ResponseAdapter):

    async def send(
        self,
        adapter: TransportAdapter,
        response: Response,
        _receive: Callable[..., Awaitable[dict]],
        send: Callable[..., Awaitable[None]],
    ) -> None:
```

Stateless `ResponseAdapter` with `__slots__ = ()`, `RESPONSE_START = "http.response.start"`, and `RESPONSE_BODY = "http.response.body"`.

`send` parameters: `adapter: TransportAdapter` supplies method and range header; `response: Response` supplies status, headers, body/stream, and background tasks; `_receive: Callable[..., Awaitable[dict]]` is accepted but unused; `send: Callable[..., Awaitable[None]]` receives ASGI message dictionaries. Awaiting the method returns `None`.

It overwrites the response `server` header with `Orionis ASGI`. Exact `HEAD` sends start plus an empty final body, adding outgoing content length for a file or buffered body when missing. It does not iterate the stream or process ranges on HEAD. Other requests send buffered bytes, or start/stream chunks with `more_body=True` followed by an empty final body. An iterator's `aclose()` is awaited in `finally` when available.

For `FileResponse`, a valid single range changes the outgoing status to 206 and replaces outgoing `content-length`, `content-range`, and `accept-ranges`; it does not set the response object's status to 206. The private range iterator reads `[start, end)` in chunks of at most `64 * 1024`, offloads open/read/close to the running loop's executor, and closes the file in `finally`. Invalid/unsatisfiable ranges fall through to full delivery; no 416 is generated.

After successful delivery, it awaits `response.runBackground()`. Send, stream, iterator-close, file, or background exceptions propagate; a delivery/close failure skips background execution. Non-Latin-1 response headers raise `UnicodeEncodeError` during `getRawHeaders()`. File operations may raise `OSError` subclasses; cancellation propagates with the file-helper behavior below. This method performs network callback I/O and mutates response headers; HEAD-added/range headers belong to the outgoing header list.

<a id="api-095"></a>

### RSGIResponseAdapter

Source: [adapters/response/rsgi.py](../adapters/response/rsgi.py).

```python
class RSGIResponseAdapter(ResponseAdapter):

    async def send(
        self,
        adapter: TransportAdapter,
        response: Response,
        protocol: HTTPProtocol,
    ) -> None:
```

Stateless `ResponseAdapter` (`__slots__ = ()`). `send` receives `adapter: TransportAdapter` for method/range access, `response: Response` to transmit, and Granian `protocol: HTTPProtocol`; it returns `None` when awaited.

It overwrites `server` with `Orionis RSGI`, obtains string header pairs, and dispatches to `protocol.response_empty` for exact HEAD (adding outgoing file/buffered content length when absent), `response_file_range(206, ..., start, end)` for a valid file range, `response_file` for other file responses, `response_stream` plus awaited `transport.send_bytes` for streams, and `response_bytes`/`response_empty` for nonempty/empty buffered bodies. File handling precedes stream handling. Range end is exclusive; invalid ranges trigger full delivery. Range headers/status change the outgoing arguments, not the response object's status.

Streams are closed using awaited `aclose()` in `finally` when available. Each successful path then awaits `response.runBackground()`; protocol/stream/close/background exceptions propagate, and an earlier failure skips background tasks. Granian owns file delivery in this adapter; no Python executor file reads occur here. Mutates the response's server header and performs protocol I/O.

<a id="api-096"></a>

### open_file

Source: [adapters/response/files.py](../adapters/response/files.py).

```python
async def open_file(path: Path, start: int = 0) -> BinaryIO:
```

`path: Path` identifies the file opened with `path.open("rb")`; `start: int = 0` is the byte offset, passed to `seek` only when truthy. Returns the open `BinaryIO` positioned at that offset. The caller owns normal closure.

Opening/seeking runs in the current asyncio loop's default executor. `asyncio.shield` prevents the waiting task's cancellation from cancelling the open future; on `asyncio.CancelledError`, it awaits opening, closes the resulting file in the executor, then re-raises. An `OSError` during seek closes the file and propagates. Opening/seek/close exceptions can propagate, including `FileNotFoundError`/`PermissionError`; a failure during cancellation cleanup may replace the cancellation. Uses file I/O and a worker thread.

<a id="api-097"></a>

### complete_file_read

Source: [adapters/response/files.py](../adapters/response/files.py).

```python
async def complete_file_read(pending: Future[bytes]) -> bytes:
```

`pending: Future[bytes]` is an already scheduled worker-read future. Returns its `bytes` result, awaiting it through `asyncio.shield`. If the caller is cancelled, waits for `pending` before re-raising `asyncio.CancelledError`, keeping a reader from being closed while that read is outstanding. Exceptions from the future propagate and may replace cancellation during cleanup. Does not schedule a read or close a file itself.

<a id="api-098"></a>

### parse_range

Source: [adapters/response/ranges.py](../adapters/response/ranges.py).

```python
def parse_range(value: str | None, file_size: int) -> tuple[int, int] | None:
```

`value: str | None` is the Range header; `file_size: int` is the file's byte size. Returns `(start, end)` as `tuple[int, int]` with exclusive `end`, or `None` for missing, malformed, or unsatisfiable input. Accepts exact lowercase `bytes=start-end`, `bytes=start-`, and `bytes=-suffix`; numeric components must be ASCII decimal digits. Explicit end is clamped to file size; suffixes larger than the file cover the whole file. Zero-size files, zero suffixes, multiple ranges, spaces, and other units are rejected. Catches numeric `ValueError` and has no I/O or mutable state; no explicit exception escapes for the annotated input types.

<a id="api-099"></a>

### IBaseMiddleware

Source: [layer/contracts/middleware.py](../layer/contracts/middleware.py).

```python
class IBaseMiddleware(ABC):

    @abstractmethod
    async def handle(
        self,
        request: Request,
        call_next: NextCallable,
    ) -> Response:
```

Slotted abstract `ABC` defining onion-style application middleware. `handle` receives `request: Request` and `call_next: NextCallable`, a no-argument callable returning an awaitable `Response`; its declared asynchronous result is `Response`. The module defines `NextCallable = Callable[[], Awaitable["Response"]]`. Direct instantiation/incomplete implementations raise `TypeError`; the abstract method body is only a docstring.

Concrete exception handling, request mutation, and whether the next handler is called:

> ⚠️ No especificado en el código fuente

<a id="api-100"></a>

### MemoryRateLimitStore

Source: [layer/store/memory_rate_limit.py](../layer/store/memory_rate_limit.py).

```python
class MemoryRateLimitStore:

    def __init__(self) -> None:

    async def hit( # NOSONAR
        self,
        key: str,
        limit: int,
        window: int,
    ) -> bool:
```

Per-instance in-memory sliding window of **accepted** attempts. `__init__` takes no arguments, creates empty dictionary/deque storage and a zero tick counter, and returns `None`. `_GC_INTERVAL: int = 16` and `_GC_BATCH_SIZE: int = 64` control incremental cleanup.

`hit` parameters: `key: str`, entity identifier; `limit: int`, maximum accepted attempts; `window: int`, seconds in the sliding window. Returns `bool`: `False` for `limit <= 0` or an exhausted window, otherwise records the current `monotonic()` timestamp and returns `True`. It evicts accepted timestamps `<= now - window`; rejected attempts do not enter the timestamp deque. Every 16 attempts, including rejections, private `__gc` examines up to 64 keys and removes expired buckets. Its private slotted dataclass `_RateLimitBucket` stores `expires_at: float` and `timestamps: deque[float]` with a fresh deque factory.

There are no `await` points inside `hit`, so calls on one event loop do not interleave inside it. No cross-thread/process lock or shared persistence exists. Each key should use a consistent window; direct calls do not validate positive windows or input types. No explicit exceptions are raised; invalid arithmetic/key types can propagate ordinary `TypeError`. Memory grows with retained keys and accepted timestamps; cleanup happens only on later calls, not on a timer.

<a id="api-101"></a>

### RateLimitMiddleware

Source: [layer/shared/rate_limit.py](../layer/shared/rate_limit.py).

```python
class RateLimitMiddleware:

    def __init__(
        self,
        config: dict,
        default_responses: IDefaultResponses,
    ) -> None:

    def isEnabled(self) -> bool:

    async def handle(
        self,
        adapter: TransportAdapter,
    ) -> Response | None:
```

`__init__` accepts `config: dict` expanded into `HTTPRateLimit` and `default_responses: IDefaultResponses`, the error-response builder; returns `None`. Configuration keys are `rate_limit_enabled: bool`, `rate_limit_requests: int`, and `rate_limit_window_seconds: int`. Their entity defaults read `RATE_LIMIT_ENABLED` (fallback `False`), `RATE_LIMIT_REQUESTS` (`100`), and `RATE_LIMIT_WINDOW` (`60`) through `Env`. Invalid field types/unknown keys raise `TypeError`; nonpositive request/window values and failed environment integer conversions raise `ValueError`. Creates a private `MemoryRateLimitStore` only when enabled and precomputes `Retry-After` as the configured whole window.

`isEnabled()` takes no arguments and returns the cached `bool` flag. `handle(adapter: TransportAdapter)` returns `Response | None` when awaited: disabled limiting, absent/false client IP, and an accepted hit return `None`; a rejected hit returns `default_responses.error(status_code=429, content="Too Many Requests", expects_json=adapter.wantsJson(), headers={"Retry-After": ...})`. The quota key is the client IP alone. It mutates store state, propagates adapter/store/default-response errors, and has no explicit raises. `Retry-After` is not computed from the oldest accepted timestamp.

<a id="api-102"></a>

### CORSException

Source: [layer/shared/cors.py](../layer/shared/cors.py).

```python
class CORSException(Exception):
```

Direct `Exception` subclass with an ellipsis body, no custom constructor, fields, or methods. Raised by `CORSMiddleware.__init__` when `allow_credentials` is true and `allow_origins` contains `"*"`. Its arguments/return behavior are inherited from `Exception`; the module defines no additional exception API.

<a id="api-103"></a>

### CORSMiddleware

Source: [layer/shared/cors.py](../layer/shared/cors.py).

```python
class CORSMiddleware:

    def __init__(
        self,
        config: dict,
    ) -> None:

    def before(
        self,
        adapter: TransportAdapter,
    ) -> Response | None:

    def after(
        self,
        adapter: TransportAdapter,
        response: Response,
    ) -> Response:
```

`__init__(config: dict)` builds `Cors(**config)`, normalizes and pre-renders configuration, and returns `None`. Fields/defaults: `allow_origins: list[str] = []`, `allow_origin_regex: str | None = None`, `allow_methods: list[str] = []`, `allow_headers: list[str] = []`, `expose_headers: list[str] = []`, `allow_credentials: bool = False`, `max_age: int | None = 600`. The wildcard-method constant is `ALL_METHODS: Final[str] = "DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT"`. Explicit methods are uppercased; configured allow/expose header names are lowercased; origin trailing slashes are removed. Matching uses exact normalized origin or `re.Pattern.match`, not full matching.

Constructor exceptions: `CORSException` for credentials plus wildcard origin; `TypeError` for unknown fields or invalid configuration types; `ValueError` for methods rejected by `Cors`; `re.PatternError` for invalid regular expressions. The entity's explicit allowed-method set omits `HEAD`, although wildcard expansion contains HEAD. Invalid list elements passed through entity validation can also raise `AttributeError` during string normalization.

`before(adapter: TransportAdapter)` returns `Response | None`: a request with Origin, an OPTIONS method (case-normalized if needed), `Access-Control-Request-Method` present, and an allowed origin gets a new status-204 response. Others return `None`, including disallowed origins. It advertises configured methods/headers but does not check the requested method/header names against those lists. Wildcard allowed headers reflect a nonempty `Access-Control-Request-Headers` and add that header to `Vary`; otherwise the literal `*` is used. Adds configured credentials and max-age when applicable.

`after(adapter: TransportAdapter, response: Response)` returns the same `Response`, applying allowed origin, credentials, and exposed-header fields when Origin is present and permitted. It does not test whether the request is preflight. Specific/credentialed origins are reflected and merged into `Vary: origin`; unrestricted origins use `*`. Existing Vary values are retained without case-insensitive duplicate directives. Both methods mutate response headers, perform no I/O, and propagate adapter/response errors without explicit raises.

<a id="api-104"></a>

### SecurityMiddleware

Source: [layer/shared/security.py](../layer/shared/security.py).

```python
class SecurityMiddleware:

    def __init__(
        self,
        config: dict,
        default_responses: IDefaultResponses,
    ) -> None:

    def handle(
        self,
        adapter: TransportAdapter,
    ) -> Response | None:
```

`__init__` receives `config: dict` expanded into `HTTPSecurity` and `default_responses: IDefaultResponses` for rejection responses, and returns `None`. `allowed_hosts: list[str] | Literal["*"]` defaults to `[]`; unknown fields, non-list/non-`"*"` values, and nonstring entries raise `TypeError`. Host entries are stripped/lowercased; empty entries are ignored. `*.example.com` allows both `example.com` and suffix-matching subdomains. The literal string `"*"`, an empty list, or all-blank entries disable allowlist enforcement; a list containing `"*"` is treated as an exact host entry.

`handle(adapter: TransportAdapter)` returns `Response | None`. In order, it rejects CR/LF in any header name/value with 400 `Invalid header format.`, multiple Host headers with 400 `Multiple Host headers not allowed.`, then missing/disallowed Host under an active allowlist with 400 `Host header not allowed.`. Host comparison strips whitespace, lowercases, removes a final port, and handles bracketed IPv6 by extracting the bracket contents. Responses use `adapter.wantsJson()`; success returns `None`. The first two checks are always active. No request mutation or I/O occurs; adapter/default-response exceptions propagate, and no exception is raised explicitly in `handle`.

<a id="api-105"></a>

### ProxiesMiddleware

Source: [layer/shared/proxies.py](../layer/shared/proxies.py).

```python
class ProxiesMiddleware:

    def __init__(
        self,
        config: dict,
    ) -> None:

    def handle(self, adapter: TransportAdapter) -> TransportAdapter:
```

`__init__(config: dict)` builds `HTTPProxies`, compiles trusted networks, and returns `None`. `trusted_proxies: list[str]` defaults through `Env.get("TRUSTED_PROXIES", [])`. Unknown fields/non-list/nonstring entries raise `TypeError`; invalid IP/CIDR strings raise `ValueError` from `ip_network(..., strict=False)`. Exact token `private` expands only to IPv4 `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, and `192.168.0.0/16`. Empty networks disable processing. Header constants are `_IP_HEADER = "x-forwarded-for"` and `_PROTO_HEADER = "x-forwarded-proto"`.

`handle(adapter: TransportAdapter)` returns that same `TransportAdapter`. It only rewrites requests whose current client is a parsable IP in a trusted network. All X-Forwarded-For header values are split on commas; invalid/empty addresses are discarded. Scanning right to left selects the first untrusted IP; if all are trusted, selects the leftmost. With no valid chain, the existing client is retained. `proxies` contains every chain string unequal to the selected client, rather than only the trusted suffix; the direct peer is not automatically appended to a valid chain.

It calls `setClient`, optionally `setScheme` for the first complete X-Forwarded-Proto value when stripped/lowercased to `http` or `https`, then `setState("forwarded", {"client": real_ip, "proxies": proxies, "chain": chain})`. A comma-separated protocol list is not accepted. Invalid forwarded addresses are caught as `ValueError` and ignored. Adapter errors propagate; there are no explicit raises in `handle`, no I/O, and the scope overrides/cache are mutated.

<a id="api-106"></a>

### UnderMaintenanceMiddleware

Source: [layer/shared/maintenance.py](../layer/shared/maintenance.py).

```python
class UnderMaintenanceMiddleware:

    def __init__(
        self,
        *,
        under_maintenance: bool,
        default_responses: IDefaultResponses,
    ) -> None:

    def handle(
        self,
        adapter: TransportAdapter,
    ) -> Response | None:
```

`__init__` requires keyword-only `under_maintenance: bool`, cached maintenance flag, and `default_responses: IDefaultResponses`, response factory; returns `None` and performs no validation.

`handle(adapter: TransportAdapter)` uses the adapter's JSON preference and returns `Response | None`: false maintenance flag returns `None`; otherwise it calls the factory with status 503 and content `The application is currently under maintenance.`. The flag is fixed at construction and tested for truthiness. No direct I/O or request mutation occurs; there are no explicit raises, and adapter/factory exceptions propagate.

<a id="api-107"></a>

### StartSessionMiddleware

Source: [layer/web/start_session.py](../layer/web/start_session.py).

```python
class StartSessionMiddleware(BaseMiddleware):

    def __init__(self, manager: SessionManager, catch: ICatch) -> None:

    async def handle(
        self,
        request: Request,
        call_next: Callable[[], Awaitable[Response]],
    ) -> Response:
```

Extends `BaseMiddleware`; slots `_manager` and `_catch` hold injected collaborators. `__init__(manager: SessionManager, catch: ICatch)` stores the session lifecycle manager and exception-to-response handler, returning `None`.

`handle` receives `request: Request` and no-argument asynchronous `call_next: Callable[[], Awaitable[Response]]`; awaiting it returns the outgoing `Response`. It awaits `manager.start(request)`, writes `request.state.session`, invokes the next handler, applies nonempty `response.getFlashData()` through `orionis.session.flash.apply_flash`, records the URL under the rules below, and awaits `manager.save(response, session)`. The manager may add the session cookie and performs the configured persistence I/O.

Private `__response` catches `Exception` from `call_next` and awaits `catch.exception(exc, request)` while the session is still available. Subsequent `BaseException` failures inside the processing/save block, including cancellation and failures of the exception handler, trigger awaited `manager.abort(session)` and re-raise; an abort failure can replace the original error. `manager.start` and the assignment to request state occur before that protected block.

Private `__storeCurrentUrl` records `request.url` only for exact GET/HEAD when neither `isAjax()` nor `wantsJson()` is true and `200 <= status < 300`. Other methods, AJAX/JSON requests and responses outside the 2xx range preserve the previously stored URL. It mutates request/session/response state and propagates collaborator exceptions; no new exception type is defined here.

<a id="api-108"></a>

### CSRFTokenMismatchException

Source: [layer/web/exceptions.py](../layer/web/exceptions.py).

```python
class CSRFTokenMismatchException(Exception):
```

Direct `Exception` subclass with no custom constructor, fields, or methods. `CSRFTokenMiddleware` raises it for invalid/missing tokens on every method outside GET/HEAD/OPTIONS/TRACE, not only the four unsafe verbs listed in its docstring. `orionis.failure.base.handler` maps it to `(419, "CSRF token mismatch")`. Inherits the standard exception arguments and behavior; it does not create a response itself.

<a id="api-109"></a>

### CSRFTokenMiddleware

Source: [layer/web/csrf_token.py](../layer/web/csrf_token.py).

```python
class CSRFTokenMiddleware(BaseMiddleware):

    def __init__(self, config: dict) -> None:

    async def handle(
        self,
        request: Request,
        call_next: Callable[[], Awaitable[Response]],
    ) -> Response:
```

Extends `BaseMiddleware`. `__init__(config: dict)` expands fields into `HTTPCsrf`, caches configuration, and returns `None`. Defaults: `enabled=True`, `token_length=32` random bytes, `session_key="_csrf_token"`, `xsrf_cookie=False`, `cookie_name="XSRF-TOKEN"`, `cookie_secure=False`, `cookie_same_site="lax"`, `cookie_path="/"`, `cookie_domain=None`. Field types are respectively `bool`, `int`, `str`, `bool`, `str`, `bool`, `Literal["lax", "strict", "none"]`, `str`, and `str | None`. Unknown fields and invalid validated types raise `TypeError`; token length below 32, invalid/empty session key or cookie name, and unsupported SameSite values raise `ValueError`. The entity does not explicitly validate `cookie_secure`.

`handle` receives `request: Request` and `call_next: Callable[[], Awaitable[Response]]`, the next no-argument async handler; awaiting it returns its `Response`. Disabled middleware delegates immediately. Otherwise, private `__resolveToken` reuses a truthy session value or generates `secrets.token_urlsafe(token_length)` and stores it; without `request.state.session` it generates an ephemeral token without persistence. It publishes `request.state.csrf_token` even on safe methods. A fresh token is generated when the stored token is absent/false.

[Session.regenerate()](../../session/session.py) requests an ID rotation while preserving session data, including the stored CSRF token. The bundled [SessionGuard](../../auth/guards/session_guard.py) explicitly replaces that token during `login()` and updates `request.state.csrf_token`; `logout()` invalidates the session and clears its stored data. The middleware creates a token when a subsequent active session has none.

Exact safe methods are GET, HEAD, OPTIONS, TRACE. Others check `x-csrf-token` before `x-xsrf-token`, trimming header tokens. A whitespace-only first header returns `None` without trying the second; body extraction then runs. If no header token is found, content type must contain the case-sensitive substring `application/x-www-form-urlencoded` or `multipart/form-data`; it awaits `request.data()` and checks nonempty string `_csrf` then `csrf_token` without trimming form values. Exceptions from `request.data()` are caught as missing tokens; cancellation is not caught by that `except Exception`.

`secrets.compare_digest(token.encode(), submitted.encode())` verifies the value. Missing/mismatched tokens raise `CSRFTokenMismatchException` before `call_next`; errors from session access, wrong stored token types, or downstream handlers otherwise propagate. It does not validate against the request cookie.

After `call_next`, optional cookie output uses configured name/path/domain/SameSite, forces `http_only=False`, and computes `secure = cookie_secure or request.scheme == "https"`. An invalidated session deletes the cookie instead; otherwise a newly stored session token overrides the earlier one in the cookie. This changes request/session state and outgoing cookies and can read the request body; no lock or cross-request synchronization is implemented in this class.

## Usage examples

Each code block in this section is a complete Python 3.14+ program. Run it independently after installing Orionis and its declared dependencies (or from this checkout with those dependencies available). No running server or configured application is needed for these examples.

### Build a JSON response

Uses the public response factory, headers and cookie chaining without an application boot or server.

```python
from orionis.http import JSONResponse, response

result = response.json({"message": "Created", "id": 42}, status_code=201)
result.setHeader("x-request-id", "example-42")
result.withCookie("language", "es", http_only=True)

assert isinstance(result, JSONResponse)
assert result.getStatusCode() == 201
assert result.getHeader("X-Request-Id") == ["example-42"]
assert result.getHeader("set-cookie") is not None
print(result.getBody().decode("utf-8"))
```

### Read a request and handle parsing errors

Provides a complete ASGI input fixture with real adapters and an explicit body-size limit. Demonstrates cached body reuse, invalid JSON, unsupported MIME and an oversized request.

```python
import asyncio

from orionis.http import Request
from orionis.http.adapters.request.asgi import ASGITransportAdapter
from orionis.http.enums import Interface
from orionis.http.payload.body import BodyStream, PayloadTooLargeException
from orionis.http.request import UnsupportedMediaTypeException


def make_request(raw: bytes, content_type: str, limit: int = 1024) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "scheme": "https",
        "path": "/users",
        "query_string": b"",
        "headers": [
            (b"host", b"example.test"),
            (b"content-type", content_type.encode("ascii")),
        ],
    }
    events = iter([{"type": "http.request", "body": raw, "more_body": False}])

    async def receive() -> dict:
        return next(events)

    return Request(
        Interface.ASGI,
        ASGITransportAdapter(scope),
        BodyStream(Interface.ASGI, receive, max_body_size=limit),
    )


async def main() -> None:
    request = make_request(b'{"name":"Ada"}', "application/json")
    assert await request.data() == {"name": "Ada"}
    assert await request.body() == b'{"name":"Ada"}'
    for raw, mime, limit in [
        (b"{invalid", "application/json", 1024),
        (b"text", "text/plain", 1024),
        (b'{"name":"Ada"}', "application/json", 4),
    ]:
        try:
            await make_request(raw, mime, limit).json()
        except (ValueError, UnsupportedMediaTypeException, PayloadTooLargeException) as exc:
            print(type(exc).__name__, str(exc))


asyncio.run(main())
```

### Integrate background tasks with ASGI delivery

Integrates `orionis.background.task.BackgroundTask`. The local send callable records actual ASGI messages; the task finishes after the response is delivered.

```python
import asyncio

from orionis.background.task import BackgroundTask
from orionis.http import response
from orionis.http.adapters.request.asgi import ASGITransportAdapter
from orionis.http.adapters.response.asgi import ASGIResponseAdapter


async def main() -> None:
    completed = []
    messages = []

    async def record_delivery() -> None:
        completed.append("delivered")

    async def receive() -> dict:
        return {"type": "http.disconnect"}

    async def send(message: dict) -> None:
        messages.append(message)

    adapter = ASGITransportAdapter({"method": "GET", "headers": []})
    result = response.text("ok", background=BackgroundTask(record_delivery))
    await ASGIResponseAdapter().send(adapter, result, receive, send)
    assert messages[0]["status"] == 200
    assert messages[-1]["body"] == b"ok"
    assert completed == ["delivered"]
    print(completed)


asyncio.run(main())
```

### Compile and resolve routes

Creates a route without an initial action, completes it with `.action(UserController, "show")`, and compiles it with middleware. Resolves implicit HEAD, handles lookup errors and round-trips metadata through RouteCache. Resolution returns metadata; it does not execute the handler or middleware.

```python
from orionis.http.middleware import BaseMiddleware
from orionis.http.routes.exceptions.method_not_allowed import MethodNotAllowed
from orionis.http.routes.exceptions.route_not_found import RouteNotFound
from orionis.http.routes.fluent import FluentRoute
from orionis.http.routes.route_cache import RouteCache
from orionis.http.routes.route_compiler import RouteCompiler
from orionis.http.routes.route_resolver import RouteResolver


class AuditMiddleware(BaseMiddleware):
    async def handle(self, request, call_next):
        return await call_next()


class UserController:
    def show(self, user_id: int) -> dict:
        return {"user_id": user_id}


route = (
    FluentRoute("GET", "/users/{user_id:int}")
    .action(UserController, "show")
    .name("users.show")
    .middleware(AuditMiddleware)
)
compiled, fallback = RouteCompiler().compile([route.export()], (None, None))
resolver = RouteResolver(compiled, hot_cache_size=32, fallback=fallback)
result = resolver.resolve("HEAD", "/users/42/")
assert result.params["user_id"] == 42
assert result.route.method == "GET"
assert result.route.compiled_middlewares == (AuditMiddleware,)
assert resolver.options("/users/42") == ["GET", "HEAD", "OPTIONS"]

for method, path in (("POST", "/users/42"), ("GET", "/missing")):
    try:
        resolver.resolve(method, path)
    except MethodNotAllowed:
        print("Method not allowed:", method, path)
    except RouteNotFound:
        print("Route not found:", path)

cache = RouteCache()
cached = cache.toCache(compiled, fallback)
restored, restored_fallback = cache.fromCache(cached)
restored_resolver = RouteResolver(restored, fallback=restored_fallback)
assert restored_resolver.resolve("GET", "/users/7").params["user_id"] == 7
print(dict(result.params))
```

### Parse a multipart upload and close resources

Parses complete multipart bytes using the real payload implementation and closes owned form/upload resources.

```python
import asyncio

from orionis.http.enums.interfaces import Interface
from orionis.http.payload.body import BodyStream, PayloadTooLargeException
from orionis.http.payload.stream_parser import MultipartStreamParser
from orionis.http.payload.uploaded_file import UploadedFile


def make_body(data: bytes, limit: int | None = None) -> BodyStream:
    messages = iter([
        {"type": "http.request", "body": data[:17], "more_body": True},
        {"type": "http.request", "body": data[17:], "more_body": False},
    ])

    async def receive() -> dict[str, object]:
        return next(messages)

    return BodyStream(Interface.ASGI, receive, max_body_size=limit)


async def main() -> None:
    raw = (
        b'--demo\r\nContent-Disposition: form-data; name="tag"\r\n\r\n'
        b'alpha\r\n'
        b'--demo\r\nContent-Disposition: form-data; name="asset"; '
        b'filename="../notes.txt"\r\nContent-Type: text/plain\r\n\r\n'
        b'hello\r\n--demo--\r\n'
    )
    body = make_body(raw, limit=4096)
    assert await body.read() == raw
    parser = MultipartStreamParser(body.stream(), boundary=b"demo")
    with await parser.parse() as form:
        assert form.get("tag") == "alpha"
        upload = form.get("asset")
        assert isinstance(upload, UploadedFile)
        assert upload.filename == "notes.txt"
        assert upload.read() == b"hello"
        print(form.fields, upload.filename, upload.size)

    try:
        await make_body(b"oversized", limit=3).read()
    except PayloadTooLargeException as error:
        print(type(error).__name__, str(error))


if __name__ == "__main__":
    asyncio.run(main())
```
## Performance and concurrency considerations

The following are implementation limits/defaults, not benchmark claims:

| Component | Verified behavior |
|---|---|
| `BodyStream` | `read()` buffers the full body; `stream()` replays that buffer if already read. Direct streaming consumes the transport once. Default limit is represented by `sys.maxsize`; `KernelHTTP` supplies no explicit smaller limit. |
| `MultipartStreamParser` | Defaults: 1000 files, 1000 fields, 10 MiB per part, 1 MiB file memory threshold, 64 KiB part headers. These are not a total-request memory cap. |
| File output | `FileResponse` defaults to 64 KiB reads; ASGI range output also uses 64 KiB. Constructor `stat()` is synchronous; reads use executor helpers. RSGI file delivery delegates to Granian. |
| Routes | Static routes use mappings; dynamic matching is indexed by segment count. Successful dynamic resolutions use a FIFO cache of 512 entries by default; zero disables it. Hits do not refresh eviction order. |
| Rate limiting | In-memory deques store accepted timestamps; cleanup examines at most 64 keys every 16 attempts. There is no configured hard global key/memory cap or cross-process sharing. |
| Default pages | First HTML access reads bundled templates synchronously; instance caches retain bytes/templates/substitution plans. Error status labels use a module-level dict. |

`MemoryRateLimitStore.hit()` contains no suspension, and its source limits the atomicity claim to a single event loop. Requests, body readers and multipart parsers contain mutable consumption state; route and default-response caches have no synchronization locks. Kernel middleware instances are cached and reused, while continuation state is per request. Neither concurrent boot nor general cross-thread use is guaranteed.

General thread-safety, throughput, latency and global memory bounds:

> ⚠️ No especificado en el código fuente

Cancellation-aware file helpers shield worker operations and wait for completion before propagating cancellation. Multipart failures clean up active/completed uploads on `BaseException`; successful parses transfer ownership to the returned form. This does not establish a guarantee for arbitrary repeated cancellation or failures in cleanup collaborators. Synchronous iterable output still iterates on the event-loop thread. Background tasks are awaited after successful sending, not dispatched as detached work.

## Compatibility notes

The inspected [pyproject.toml](../../../pyproject.toml) declares Orionis `0.756.0` and **Python >=3.14**. Some files without `from __future__ import annotations` (for example `kernel.py` and web middleware) refer in annotations to names imported only under `TYPE_CHECKING`; Python 3.14 deferred annotations allow those definitions without eager runtime resolution. The source also uses `type` aliases/generic function parameters, `Self`, `StrEnum`, `mimetypes.guess_file_type` and the `Partitioned` cookie attribute. These older individual features do not lower the declared project minimum. Runtime annotation evaluation may still require the missing type namespace.

Direct third-party imports and the dependency constraints declared by this checkout:

| Package | Declared constraint | Use |
|---|---|---|
| `msgspec` | `>=0.21.1` | JSON/MessagePack encoding and decoding; supported `Struct` handler results. |
| `defusedxml` | `>=0.7.1,<1.0` | XML parser. |
| `granian[dotenv,pname,reload,uvloop,winloop]` | `>=2.8.3,<3.0` | RSGI transport types/protocol; direct HTTP imports are under `TYPE_CHECKING`. |

These packages are already project dependencies installed by `pip install orionis`; no separate HTTP installation requirement or extra is declared. Dependency versions above are declared ranges, not assertions about installed versions. Internal services have their own project dependencies and configuration; importing the root `orionis` package also loads application infrastructure.

Behavior that matters when integrating this revision:

- `json()` accepts `+json`, while `data()` accepts only its four exact MIME values; Accept helpers perform substring tests and do not honor quality weights.
- Router verbs and `FluentRoute` accept omitted/`None` actions for later `.action(...)` assignment; exporting an unfinished route raises `ValueError`. `fallback(action)` requires a handler immediately and returns no builder. HEAD resolution uses GET; OPTIONS discovery is separate.
- Invalid/unsupported file ranges lead to full output in the response adapters, not a generated 416 response.
- Session middleware stores a previous URL only for GET/HEAD responses with 2xx status and excludes AJAX and JSON requests.
- `RegisterController` requires an application user model, configured database/hash services and application views. `Router.auth()` loads those controllers lazily.
- Public names such as `estructures`, `httpVersion`, `formUrlEncoded`, `robotsTxt` and `noContent` retain their source spelling.
- `WebSocketStatus` enumerates close codes; the HTTP kernel provides no WebSocket dispatch API.
