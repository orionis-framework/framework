# orionis.http

> Peticiones, rutas, middleware, parseo de payload y respuestas HTTP para aplicaciones ASGI/RSGI.

## Tabla de contenidos

- [Descripción funcional](#descripción-funcional)
- [Referencia de API](#referencia-de-api)
- [Ejemplos de uso](#ejemplos-de-uso)
- [Consideraciones de rendimiento y concurrencia](#consideraciones-de-rendimiento-y-concurrencia)
- [Notas de compatibilidad](#notas-de-compatibilidad)

<details>
<summary>Índice de API</summary>

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

## Descripción funcional

`orionis.http` convierte entradas ASGI/RSGI en peticiones, resuelve rutas, ejecuta middleware y handlers y envía respuestas HTTP tipadas. Incluye parsers de cuerpos/formularios/archivos, compilación y caché de rutas y páginas/controladores predeterminados. Integra el contenedor de aplicación (`orionis.foundation.contracts.application`), autenticación, sesiones, validación de schemas, vistas y tareas de fondo.

La raíz del paquete exporta los siguientes nombres; las demás API de esta referencia se importan desde sus módulos de definición:

```python
from orionis.http import (
    BaseMiddleware, FileResponse, HTMLResponse, HttpResponse, JSONResponse,
    NextCallable, PlainTextResponse, RedirectResponse, Request, Response,
    ResponseFactory, StreamingResponse, response,
)
```

`orionis.http.base` exporta `BaseController`; `orionis.http.enums` exporta `Interface`, `HTTPStatus` y `WebSocketStatus`. Los inicializadores de `routes` y `payload` están vacíos.

### Ciclo de una petición

1. `KernelHTTP.boot()` carga rutas y prepara handlers, middleware, adaptadores de respuesta y servicios de aplicación.
2. `handleASGI()` o `handleRSGI()` abre un scope de aplicación y aplica middleware de transporte.
3. El resolver selecciona metadatos de ruta; el kernel crea `BodyStream` y `Request` y registra la petición en el scope.
4. Se ejecutan middleware web/API y de ruta antes del handler; el contenedor resuelve sus argumentos.
5. El kernel gestiona las excepciones contempladas, aplica cabeceras CORS de salida y envía mediante el adaptador; espera las tareas de fondo tras una entrega correcta.

### Decisiones de diseño

- **Adaptadores y contratos ABC:** ASGI/RSGI comparten API de petición/respuesta, mientras los métodos de transporte conservan sus propias firmas.
- **Factoría:** `response` es una instancia de `ResponseFactory` creada al importar; sus llamadas crean respuestas y permiten encadenar cookies/flash.
- **Constructores encadenables:** `FluentRoute` y `RouteGroup` modifican rutas registradas de inmediato; los miembros del grupo se guardan en una tupla.
- **Singleton de contenedor:** `RouterProvider` enlaza `IRouter` con `Router` como singleton y fija la fachada `Route` durante el arranque.
- **Dataclasses congeladas:** `CompiledRoute` y `ResolvedRoute` impiden reasignar campos; sus contenedores anidados tienen la mutabilidad descrita en cada entrada de API.
- **Slots y cachés diferidas:** clases de petición, transporte y payload usan `__slots__` y cachean valores seleccionados; esto no vuelve inmutables los mappings devueltos.
- **Streaming y almacenamiento temporal:** el procesamiento de cuerpos/archivos puede consumir datos incrementalmente y trasladar archivos a almacenamiento temporal; la propiedad de los recursos forma parte de la API.
- **Continuación por petición:** `_MiddlewarePipeline` mantiene el estado del recorrido fuera de las instancias compartidas de middleware y rechaza repetir la continuación en una capa.

### Inventario de fuentes

A continuación se enumeran los 104 archivos Python, incluidos los inicializadores de paquetes. Las definiciones con guion bajo inicial son internas; la referencia incluye métodos públicos propios y dunders seleccionados de ciclo de vida/mapping. Los métodos heredados se documentan en su clase de definición. El inventario incluye también recursos de respuesta no escritos en Python.

<details>
<summary>Desplegar inventario completo de archivos</summary>

| Archivo | Definiciones / exports del paquete |
|---|---|
| [`__init__.py`](../__init__.py) | `ResponseFactory`, `response`, `BaseMiddleware`, `NextCallable`, `Request`, `FileResponse`, `HTMLResponse`, `JSONResponse`, `PlainTextResponse`, `RedirectResponse`, `Response`, `StreamingResponse`, `HttpResponse` |
| [`adapters/__init__.py`](../adapters/__init__.py) | Sin definiciones locales de clases/funciones. |
| [`adapters/request/__init__.py`](../adapters/request/__init__.py) | Sin definiciones locales de clases/funciones. |
| [`adapters/request/asgi.py`](../adapters/request/asgi.py) | `ASGITransportAdapter` |
| [`adapters/request/contracts/__init__.py`](../adapters/request/contracts/__init__.py) | Sin definiciones locales de clases/funciones. |
| [`adapters/request/contracts/transport.py`](../adapters/request/contracts/transport.py) | `TransportAdapter` |
| [`adapters/request/rsgi.py`](../adapters/request/rsgi.py) | `RSGITransportAdapter` |
| [`adapters/response/__init__.py`](../adapters/response/__init__.py) | Sin definiciones locales de clases/funciones. |
| [`adapters/response/asgi.py`](../adapters/response/asgi.py) | `ASGIResponseAdapter` |
| [`adapters/response/contracts/__init__.py`](../adapters/response/contracts/__init__.py) | Sin definiciones locales de clases/funciones. |
| [`adapters/response/contracts/response.py`](../adapters/response/contracts/response.py) | `ResponseAdapter` |
| [`adapters/response/files.py`](../adapters/response/files.py) | `open_file`, `complete_file_read` |
| [`adapters/response/ranges.py`](../adapters/response/ranges.py) | `parse_range` |
| [`adapters/response/rsgi.py`](../adapters/response/rsgi.py) | `RSGIResponseAdapter` |
| [`base/__init__.py`](../base/__init__.py) | `BaseController` |
| [`base/controller.py`](../base/controller.py) | `BaseController` |
| [`contracts/__init__.py`](../contracts/__init__.py) | Sin definiciones locales de clases/funciones. |
| [`contracts/kernel.py`](../contracts/kernel.py) | `IKernelHTTP` |
| [`contracts/request.py`](../contracts/request.py) | `IRequest` |
| [`contracts/response.py`](../contracts/response.py) | `IResponse` |
| [`default/__init__.py`](../default/__init__.py) | Sin definiciones locales de clases/funciones. |
| [`default/contracts/__init__.py`](../default/contracts/__init__.py) | Sin definiciones locales de clases/funciones. |
| [`default/contracts/responses.py`](../default/contracts/responses.py) | `IDefaultResponses` |
| [`default/controllers/__init__.py`](../default/controllers/__init__.py) | Sin definiciones locales de clases/funciones. |
| [`default/controllers/login_controller.py`](../default/controllers/login_controller.py) | `LoginController` |
| [`default/controllers/register_controller.py`](../default/controllers/register_controller.py) | `RegisterController` |
| [`default/responses.py`](../default/responses.py) | `_validate_status_code`, `_compile_placeholders`, `DefaultResponses` |
| [`default/schemas/__init__.py`](../default/schemas/__init__.py) | Sin definiciones locales de clases/funciones. |
| [`default/schemas/login.py`](../default/schemas/login.py) | `LoginSchema` |
| [`default/schemas/register.py`](../default/schemas/register.py) | `RegisterSchema` |
| [`enums/__init__.py`](../enums/__init__.py) | `Interface`, `HTTPStatus`, `WebSocketStatus` |
| [`enums/interfaces.py`](../enums/interfaces.py) | `Interface` |
| [`enums/status.py`](../enums/status.py) | `HTTPStatus`, `WebSocketStatus` |
| [`factory.py`](../factory.py) | `ResponseFactory` |
| [`kernel.py`](../kernel.py) | `_MiddlewarePipeline`, `KernelHTTP` |
| [`layer/__init__.py`](../layer/__init__.py) | Sin definiciones locales de clases/funciones. |
| [`layer/api/__init__.py`](../layer/api/__init__.py) | Sin definiciones locales de clases/funciones. |
| [`layer/contracts/__init__.py`](../layer/contracts/__init__.py) | Sin definiciones locales de clases/funciones. |
| [`layer/contracts/middleware.py`](../layer/contracts/middleware.py) | `IBaseMiddleware` |
| [`layer/shared/__init__.py`](../layer/shared/__init__.py) | Sin definiciones locales de clases/funciones. |
| [`layer/shared/cors.py`](../layer/shared/cors.py) | `CORSException`, `CORSMiddleware` |
| [`layer/shared/maintenance.py`](../layer/shared/maintenance.py) | `UnderMaintenanceMiddleware` |
| [`layer/shared/proxies.py`](../layer/shared/proxies.py) | `ProxiesMiddleware` |
| [`layer/shared/rate_limit.py`](../layer/shared/rate_limit.py) | `RateLimitMiddleware` |
| [`layer/shared/security.py`](../layer/shared/security.py) | `SecurityMiddleware` |
| [`layer/store/__init__.py`](../layer/store/__init__.py) | Sin definiciones locales de clases/funciones. |
| [`layer/store/memory_rate_limit.py`](../layer/store/memory_rate_limit.py) | `_RateLimitBucket`, `MemoryRateLimitStore` |
| [`layer/web/__init__.py`](../layer/web/__init__.py) | Sin definiciones locales de clases/funciones. |
| [`layer/web/csrf_token.py`](../layer/web/csrf_token.py) | `CSRFTokenMiddleware` |
| [`layer/web/exceptions.py`](../layer/web/exceptions.py) | `CSRFTokenMismatchException` |
| [`layer/web/start_session.py`](../layer/web/start_session.py) | `StartSessionMiddleware` |
| [`middleware.py`](../middleware.py) | `BaseMiddleware` |
| [`payload/__init__.py`](../payload/__init__.py) | Sin definiciones locales de clases/funciones. |
| [`payload/body.py`](../payload/body.py) | `PayloadTooLargeException`, `BodyStream` |
| [`payload/contracts/__init__.py`](../payload/contracts/__init__.py) | Sin definiciones locales de clases/funciones. |
| [`payload/contracts/body_stream.py`](../payload/contracts/body_stream.py) | `IBodyStream` |
| [`payload/contracts/form_data.py`](../payload/contracts/form_data.py) | `IFormData` |
| [`payload/contracts/media_types.py`](../payload/contracts/media_types.py) | `IMediaTypeRegistry` |
| [`payload/contracts/part.py`](../payload/contracts/part.py) | `IMultipartPart` |
| [`payload/contracts/stream_parser.py`](../payload/contracts/stream_parser.py) | `IMultipartStreamParser` |
| [`payload/contracts/uploaded_file.py`](../payload/contracts/uploaded_file.py) | `IUploadedFile` |
| [`payload/estructures/__init__.py`](../payload/estructures/__init__.py) | Sin definiciones locales de clases/funciones. |
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
| [`routes/__init__.py`](../routes/__init__.py) | Sin definiciones locales de clases/funciones. |
| [`routes/contracts/__init__.py`](../routes/contracts/__init__.py) | Sin definiciones locales de clases/funciones. |
| [`routes/contracts/fluent.py`](../routes/contracts/fluent.py) | `IFluentRoute` |
| [`routes/contracts/loader.py`](../routes/contracts/loader.py) | `IRouteLoader` |
| [`routes/contracts/route_cache.py`](../routes/contracts/route_cache.py) | `IRouteCache` |
| [`routes/contracts/route_compiler.py`](../routes/contracts/route_compiler.py) | `IRouteCompiler` |
| [`routes/contracts/route_resolver.py`](../routes/contracts/route_resolver.py) | `IRouteResolver` |
| [`routes/contracts/router.py`](../routes/contracts/router.py) | `IRouter` |
| [`routes/entities/__init__.py`](../routes/entities/__init__.py) | Sin definiciones locales de clases/funciones. |
| [`routes/entities/compiled_route.py`](../routes/entities/compiled_route.py) | `CompiledRoute` |
| [`routes/entities/resolved_route.py`](../routes/entities/resolved_route.py) | `ResolvedRoute` |
| [`routes/enums/__init__.py`](../routes/enums/__init__.py) | Sin definiciones locales de clases/funciones. |
| [`routes/enums/route_types.py`](../routes/enums/route_types.py) | `RouteType` |
| [`routes/exceptions/__init__.py`](../routes/exceptions/__init__.py) | Sin definiciones locales de clases/funciones. |
| [`routes/exceptions/fallback_route_already_registered.py`](../routes/exceptions/fallback_route_already_registered.py) | `FallbackRouteAlreadyRegisteredException` |
| [`routes/exceptions/method_not_allowed.py`](../routes/exceptions/method_not_allowed.py) | `MethodNotAllowed` |
| [`routes/exceptions/route_not_found.py`](../routes/exceptions/route_not_found.py) | `RouteNotFound` |
| [`routes/fluent.py`](../routes/fluent.py) | `FluentRoute` |
| [`routes/functions.py`](../routes/functions.py) | `normalize_path`, `normalize_request_path`, `strip_regex_anchors`, `flatten_middleware`, `_middleware_key`, `is_valid_handler`, `parse_action` |
| [`routes/group.py`](../routes/group.py) | `RouteGroup` |
| [`routes/loader.py`](../routes/loader.py) | `RouteLoader` |
| [`routes/params_types.py`](../routes/params_types.py) | Sin definiciones locales de clases/funciones. |
| [`routes/provider.py`](../routes/provider.py) | `RouterProvider` |
| [`routes/route_cache.py`](../routes/route_cache.py) | `RouteCache` |
| [`routes/route_compiler.py`](../routes/route_compiler.py) | `_validate_literal`, `_action_name`, `_register_name`, `RouteCompiler` |
| [`routes/route_id.py`](../routes/route_id.py) | `RouteID` |
| [`routes/route_resolver.py`](../routes/route_resolver.py) | `_DepthBucket`, `_PrefixIndex`, `_select_bucket`, `_path_allowed_for_method`, `_build_extractors`, `_build_matching_bucket`, `_build_depth_bucket`, `_build_overlapping_index`, `_extract_result`, `RouteResolver`, `DepthTable` |
| [`routes/router.py`](../routes/router.py) | `Router` |
| [`routes/types.py`](../routes/types.py) | `RouteAction`, `MiddlewareInput` |
| [`types.py`](../types.py) | `HttpResponse` |
| [`validation.py`](../validation.py) | `_url_origin`, `_is_local_reference`, `validation_response`, `previous_url` |
| [`default/assets/favicon.ico`](../default/assets/favicon.ico) | Recurso/plantilla de respuesta incluido. |
| [`default/assets/robots.txt`](../default/assets/robots.txt) | Recurso/plantilla de respuesta incluido. |
| [`default/pages/down.html`](../default/pages/down.html) | Recurso/plantilla de respuesta incluido. |
| [`default/pages/error.html`](../default/pages/error.html) | Recurso/plantilla de respuesta incluido. |
| [`default/pages/exception.html`](../default/pages/exception.html) | Recurso/plantilla de respuesta incluido. |
| [`default/pages/up.html`](../default/pages/up.html) | Recurso/plantilla de respuesta incluido. |

</details>

### Dependencias internas

Aquí se enumeran imports directos externos a `orionis.http`, incluidos los de `TYPE_CHECKING` y los diferidos. `default/controllers/register_controller.py` también importa directamente `app.models.user.User`, propio de la aplicación.

<details>
<summary>Nombres exactos de módulos Orionis</summary>

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

## Referencia de API

Los bloques de firmas son declaraciones copiadas del código, no ejemplos autónomos de ejecución. Conservan anotaciones, valores predeterminados, decoradores, mayúsculas e incluso discrepancias del código. `self`/`cls` representan la instancia/clase enlazada y no son argumentos adicionales del llamador; el retorno `None` del constructor describe `__init__`, no el objeto creado al invocar la clase. Las propiedades se leen como atributos. Los generadores async producen elementos; las corrutinas se esperan con await. Cada entrada describe comportamiento observable, parámetros, resultados, errores relevantes y efectos de estado/I/O. Los contratos abstractos remiten el significado de parámetros a sus implementaciones sin afirmar que un docstring imponga comportamiento.

Pueden propagarse excepciones de callables suministrados, servicios de aplicación, operaciones de archivo e implementaciones de transporte cuando no se capturan localmente; esta referencia no inventa un conjunto cerrado de excepciones de esos colaboradores. Las garantías no especificadas se marcan con la advertencia literal requerida en ambos idiomas.
<a id="api-001"></a>

### UnsupportedMediaTypeException

[`orionis.http.request.UnsupportedMediaTypeException`](../request.py)

```python
class UnsupportedMediaTypeException(Exception):
```

Subclase de Exception que lanzan las comprobaciones MIME de Request; sin constructor ni métodos propios.

<a id="api-002"></a>

### Request

[`orionis.http.request.Request`](../request.py)

```python
class Request(IRequest):
```

Petición independiente del transporte que implementa IRequest. Cachea propiedades y datos decodificados por instancia; los resultados mutables no son copias defensivas. La clase y su contrato declaran __slots__, pero los diccionarios cacheados y el estado siguen siendo mutables. La propiedad del flujo/lectura sigue al IBodyStream inyectado.

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

Conserva el scope del adaptador y el lector del cuerpo, inicializa cachés diferidas y copia parámetros de ruta. Devuelve None. Una interfaz inválida lanza ValueError al convertir a Interface; propaga fallos del adaptador.

| Parámetro | Tipo | Significado |
|---|---|---|
| `interface` | `Interface` | Interfaz de transporte. |
| `adapter` | `TransportAdapter` | Adaptador que proporciona el scope y las cabeceras. |
| `body_stream` | `IBodyStream` | Lector del cuerpo proporcionado por quien llama. |
| `registry` | `MediaTypeRegistry \| None` | Registro de parsers MIME; None selecciona DEFAULT_MEDIA_TYPES. |
| `params` | `Mapping[str, Any] \| None` | Parámetros de ruta, copiados a un dict interno si no están vacíos. |

Tipo de retorno declarado: `None`.

```python
@property
def method(self) -> str:
```

Devuelve scope["method"] cacheado; si falta method lanza KeyError.

Tipo de retorno declarado: `str`.

```python
@property
def scheme(self) -> str:
```

Devuelve y cachea el scheme del scope; por defecto "http".

Tipo de retorno declarado: `str`.

```python
@property
def path(self) -> str:
```

Devuelve y cachea path del scope; por defecto "/".

Tipo de retorno declarado: `str`.

```python
@property
def httpVersion(self) -> str:
```

Devuelve y cachea http_version; por defecto "1.1".

Tipo de retorno declarado: `str`.

```python
@property
def interface(self) -> Interface:
```

Devuelve el enum Interface normalizado.

Tipo de retorno declarado: `Interface`.

```python
@property
def url(self) -> str:
```

Construye la URL de forma diferida con scheme, Host (o server), path y query. ASGI sin Host/server devuelve ruta relativa; RSGI accede directamente a claves obligatorias y puede lanzar KeyError.

Tipo de retorno declarado: `str`.

```python
@property
def baseUrl(self) -> str:
```

Construye el origen de forma diferida; ASGI añade root_path y usa localhost si faltan Host/server. RSGI usa Host o server sin root_path; claves RSGI obligatorias ausentes lanzan KeyError.

Tipo de retorno declarado: `str`.

```python
@property
def headers(self) -> Headers:
```

Devuelve el objeto Headers del adaptador, cacheado de forma diferida y sin copiar.

Tipo de retorno declarado: `Headers`.

```python
@property
def queryParams(self) -> QueryParams:
```

Parsea query_string de forma diferida con QueryParams; los bytes ASGI usan Latin-1. RSGI espera una cadena en scope["query_string"].

Tipo de retorno declarado: `QueryParams`.

```python
@property
def cookies(self) -> Cookies:
```

Parsea la cabecera Cookie de forma diferida en Cookies.

Tipo de retorno declarado: `Cookies`.

```python
@property
def ip(self) -> str | None:
```

Devuelve client[0] como str si client es lista/tupla, str(client) en otro caso, o None; cachea resultados distintos de None.

Tipo de retorno declarado: `str | None`.

```python
@property
def port(self) -> int | None:
```

Devuelve scope.get("port") y cachea resultados distintos de None; no extrae el puerto de una tupla client ASGI sin normalizar.

Tipo de retorno declarado: `int | None`.

```python
@property
def forwarded(self) -> dict[str, Any]:
```

Cachea y devuelve el mapping forwarded del scope, o un dict vacío.

Tipo de retorno declarado: `dict[str, Any]`.

```python
@property
def userAgent(self) -> str | None:
```

Devuelve la cabecera user-agent o None.

Tipo de retorno declarado: `str | None`.

```python
@property
def authorization(self) -> str | None:
```

Devuelve la cabecera authorization o None.

Tipo de retorno declarado: `str | None`.

```python
@property
def bearerToken(self) -> str | None:
```

Devuelve el token sin espacios exteriores solo si existe una cabecera Authorization con prefijo "bearer " sin distinguir mayúsculas; en otro caso None.

Tipo de retorno declarado: `str | None`.

```python
@property
def apiKey(self) -> str | None:
```

Devuelve x-api-key o None.

Tipo de retorno declarado: `str | None`.

```python
@property
def accept(self) -> str | None:
```

Devuelve Accept o None.

Tipo de retorno declarado: `str | None`.

```python
@property
def state(self) -> SimpleNamespace:
```

Crea un SimpleNamespace en el primer acceso y devuelve el objeto mutable.

Tipo de retorno declarado: `SimpleNamespace`.

```python
@property
def scope(self) -> dict[str, Any]:
```

Devuelve el dict scope subyacente por referencia.

Tipo de retorno declarado: `dict[str, Any]`.

```python
async def stream(self) -> AsyncGenerator[bytes]:
```

Produce bloques del flujo del cuerpo; consume el flujo subyacente y propaga sus errores de estado, límite de tamaño y transporte.

Tipo de retorno declarado: `AsyncGenerator[bytes]`.

```python
async def body(self) -> bytes:
```

Espera body_stream.read() y devuelve bytes; propaga errores de BodyStream/transporte.

Tipo de retorno declarado: `bytes`.

```python
async def raw(self) -> bytes:
```

Equivale funcionalmente a body(): lee mediante el mismo lector del cuerpo.

Tipo de retorno declarado: `bytes`.

```python
async def text(self) -> str:
```

Lee todos los bytes y decodifica UTF-8 estricto; propaga UnicodeDecodeError y errores del lector.

Tipo de retorno declarado: `str`.

```python
async def json(self) -> object:
```

Cachea y devuelve el valor JSON decodificado como object: dict, list, str, int, float, bool o None. Acepta application/json y tipos terminados en +json. Lanza UnsupportedMediaTypeException para otros tipos y ValueError para JSON vacío o inválido; propaga errores del lector.

Tipo de retorno declarado: `object`.

```python
async def xml(self) -> XMLElement:
```

Lee el cuerpo y delega en `parse_xml` sin comprobar Content-Type. Propaga `xml.etree.ElementTree.ParseError` para XML mal formado, `defusedxml.common.EntitiesForbidden` para declaraciones de entidades internas o externas y errores del lector del cuerpo. `EntitiesForbidden` pertenece a la familia `DefusedXmlException`. Se permiten DTD sin declaraciones de entidades; no se resuelven recursos externos.

Tipo de retorno declarado: `XMLElement`.

```python
async def msgpack(self) -> object:
```

Lee y delega en parse_msgpack sin validar MIME ni exigir mapping. Devuelve el valor MessagePack decodificado como object, incluidos mapas, arrays, escalares, datos binarios, valores de extensión o None. MessagePack inválido lanza msgspec.DecodeError; propaga errores del lector.

Tipo de retorno declarado: `object`.

```python
async def formUrlEncoded(self) -> dict[str, Any]:
```

Cachea un dict URL-encoded con parse_urlencoded (último valor repetido). Content-Type incorrecto lanza UnsupportedMediaTypeException; propaga errores de decodificación/lectura.

Tipo de retorno declarado: `dict[str, Any]`.

```python
async def form(self) -> FormData:
```

Procesa multipart/form-data en flujo con MultipartStreamParser y cachea FormData. MIME incorrecto lanza UnsupportedMediaTypeException; boundary ausente lanza ValueError. Propaga límites del parser, errores de temporales y transporte; los archivos devueltos requieren cierre.

Tipo de retorno declarado: `FormData`.

```python
async def payload(self) -> object:
```

Devuelve bytes para MIME ausente/no registrado, FormData para multipart o el resultado del parser síncrono del registro. Consume el cuerpo; propaga excepciones del parser y lector.

Tipo de retorno declarado: `object`.

```python
async def data(self) -> dict[str, Any]:
```

Cachea un dict para application/json, application/x-www-form-urlencoded, multipart/form-data o application/msgpack exactos. Los valores JSON/MessagePack decodificados deben ser mappings (TypeError en otro caso); cuerpos vacíos o fallos de decodificación JSON/MessagePack lanzan ValueError. Los valores repetidos de formulario forman listas; multipart puede incluir UploadedFile. Otros MIME, incluido +json, lanzan UnsupportedMediaTypeException. El parseo multipart puede lanzar ValueError; propaga otros errores del cuerpo/parser.

Tipo de retorno declarado: `dict[str, Any]`.

```python
def wantsJson(self) -> bool:
```

Comprueba si Accept en minúsculas contiene application/json o +json; no negocia factores de calidad.

Tipo de retorno declarado: `bool`.

```python
def wantsHtml(self) -> bool:
```

Busca text/html o */* en Accept en minúsculas.

Tipo de retorno declarado: `bool`.

```python
def wantsXml(self) -> bool:
```

Busca application/xml o text/xml en Accept en minúsculas.

Tipo de retorno declarado: `bool`.

```python
def accepts(self, mime: str) -> bool:
```

Devuelve si mime.lower() es subcadena de Accept en minúsculas; no implementa negociación de comodines.

| Parámetro | Tipo | Significado |
|---|---|---|
| `mime` | `str` | Cadena MIME que se busca en Accept convertido a minúsculas. |

Tipo de retorno declarado: `bool`.

```python
def isAjax(self) -> bool:
```

Comprueba igualdad exacta de X-Requested-With con "XMLHttpRequest".

Tipo de retorno declarado: `bool`.

```python
def routeParam(self, key: str) -> object:
```

Devuelve el parámetro de ruta indicado o None.

| Parámetro | Tipo | Significado |
|---|---|---|
| `key` | `str` | Clave de cabecera, cookie, flash o consulta, según el método. |

Tipo de retorno declarado: `object`.

```python
def routeParams(self) -> dict[str, Any]:
```

Devuelve el dict mutable interno de parámetros; crea uno vacío si hace falta.

Tipo de retorno declarado: `dict[str, Any]`.

```python
def csrfToken(self) -> str | None:
```

Devuelve state.csrf_token si existe, o None. También se expone como propiedad csrf_token.

Tipo de retorno declarado: `str | None`.

El siguiente alias también es público:

```python
csrf_token = property(csrfToken)
```

<a id="api-003"></a>

### Response

[`orionis.http.responses.Response`](../responses.py)

```python
class Response(IResponse):
```

Respuesta mutable que implementa IResponse. Los parámetros comunes se describen en cada firma. Las consultas de cabeceras no distinguen mayúsculas. Set-Cookie puede repetirse. No hay I/O de red hasta que un adaptador envía la respuesta.

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

Guarda estado, cabeceras y tarea; renderiza contenido normal de inmediato y conserva iterables async como flujos. TypeError: estado no entero, headers evaluados como verdaderos que no sean mapping o background inválido; ValueError: estado fuera de 100–599. Propaga errores de renderizado. La clase base no crea cabeceras Content-Type ni Content-Length.

| Parámetro | Tipo | Significado |
|---|---|---|
| `content` | `Any` | Cuerpo o valor que se renderiza; la interpretación depende de la clase de respuesta. |
| `status_code` | `HTTPStatus \| int` | Código HTTP; la respuesta base valida enteros entre 100 y 599. |
| `headers` | `Mapping[str, str] \| None` | Cabeceras iniciales de respuesta, con nombres almacenados en minúsculas. |
| `media_type` | `str \| None` | Tipo MIME de la respuesta. |
| `background` | `BackgroundTask \| None` | BackgroundTask que se espera al llamar runBackground(). |

Tipo de retorno declarado: `None`.

```python
def render(self, content: Any) -> bytes:
```

Devuelve b"" para None, conserva bytes, copia bytearray/memoryview, codifica str con self.charset (utf-8 por defecto) y en otro caso codifica str(content) con ese charset. Propaga errores de conversión/codificación; no reemplaza el cuerpo almacenado.

| Parámetro | Tipo | Significado |
|---|---|---|
| `content` | `Any` | Cuerpo o valor que se renderiza; la interpretación depende de la clase de respuesta. |

Tipo de retorno declarado: `bytes`.

```python
def addHeader(self, key: str, value: str) -> None:
```

Añade value bajo key.lower(); modifica cabeceras y conserva valores duplicados. Devuelve None.

| Parámetro | Tipo | Significado |
|---|---|---|
| `key` | `str` | Clave de cabecera, cookie, flash o consulta, según el método. |
| `value` | `str` | Valor asociado a key. |

Tipo de retorno declarado: `None`.

```python
def setHeader(self, key: str, value: str) -> None:
```

Reemplaza todos los valores de key.lower() por uno. Devuelve None.

| Parámetro | Tipo | Significado |
|---|---|---|
| `key` | `str` | Clave de cabecera, cookie, flash o consulta, según el método. |
| `value` | `str` | Valor asociado a key. |

Tipo de retorno declarado: `None`.

```python
def getHeader(self, key: str) -> list[str] | None:
```

Devuelve la lista interna de valores o None; quien llama puede modificar esa lista.

| Parámetro | Tipo | Significado |
|---|---|---|
| `key` | `str` | Clave de cabecera, cookie, flash o consulta, según el método. |

Tipo de retorno declarado: `list[str] | None`.

```python
def hasHeader(self, key: str) -> bool:
```

Indica si key.lower() está almacenado.

| Parámetro | Tipo | Significado |
|---|---|---|
| `key` | `str` | Clave de cabecera, cookie, flash o consulta, según el método. |

Tipo de retorno declarado: `bool`.

```python
def removeHeader(self, key: str) -> None:
```

Elimina key.lower() si existe; ignora claves ausentes. Devuelve None.

| Parámetro | Tipo | Significado |
|---|---|---|
| `key` | `str` | Clave de cabecera, cookie, flash o consulta, según el método. |

Tipo de retorno declarado: `None`.

```python
def getRawHeaders(self) -> list[tuple[bytes, bytes]]:
```

Devuelve una lista nueva de pares de bytes Latin-1; UnicodeEncodeError para nombres/valores no codificables.

Tipo de retorno declarado: `list[tuple[bytes, bytes]]`.

```python
def getStringHeaders(self) -> list[tuple[str, str]]:
```

Devuelve una lista nueva de pares de cabecera en texto, conservando duplicados.

Tipo de retorno declarado: `list[tuple[str, str]]`.

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

Añade Set-Cookie mediante SimpleCookie y codifica el valor con porcentajes. Considera UTC los datetime sin zona. ValueError por same_site inválido o "none" sin secure=True; propaga errores de nombre, codificación y tipo de cookie. Devuelve None.

| Parámetro | Tipo | Significado |
|---|---|---|
| `key` | `str` | Clave de cabecera, cookie, flash o consulta, según el método. |
| `value` | `str` | Valor asociado a key. |
| `max_age` | `int \| None` | Duración de la cookie en segundos; None omite Max-Age. |
| `expires` | `datetime \| str \| int \| None` | Caducidad de la cookie; datetime se normaliza a UTC y los demás valores se convierten a texto. |
| `path` | `str \| None` | Ruta de archivo para respuestas de archivo; ruta URL para métodos de cookies. |
| `domain` | `str \| None` | Dominio de la cookie; None omite el atributo. |
| `secure` | `bool` | Activa el atributo Secure de la cookie. |
| `http_only` | `bool` | Activa el atributo HttpOnly de la cookie. |
| `same_site` | `Literal["lax", "strict", "none"] \| None` | Política SameSite; None la omite, mientras que la cadena "none" requiere secure=True. |
| `partitioned` | `bool` | Activa el atributo Partitioned de la cookie. |

Tipo de retorno declarado: `None`.

```python
def deleteCookie(
    self,
    key: str,
    *,
    path: str = "/",
    domain: str | None = None,
) -> None:
```

Añade cookie caducada (Max-Age=0, 1970-01-01 UTC) para key/path/domain; devuelve None y propaga errores de setCookie.

| Parámetro | Tipo | Significado |
|---|---|---|
| `key` | `str` | Clave de cabecera, cookie, flash o consulta, según el método. |
| `path` | `str` | Ruta de archivo para respuestas de archivo; ruta URL para métodos de cookies. |
| `domain` | `str \| None` | Dominio de la cookie; None omite el atributo. |

Tipo de retorno declarado: `None`.

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

Llama setCookie y devuelve esta misma respuesta; mismos errores y mutación.

| Parámetro | Tipo | Significado |
|---|---|---|
| `key` | `str` | Clave de cabecera, cookie, flash o consulta, según el método. |
| `value` | `str` | Valor asociado a key. |
| `max_age` | `int \| None` | Duración de la cookie en segundos; None omite Max-Age. |
| `expires` | `datetime \| str \| int \| None` | Caducidad de la cookie; datetime se normaliza a UTC y los demás valores se convierten a texto. |
| `path` | `str \| None` | Ruta de archivo para respuestas de archivo; ruta URL para métodos de cookies. |
| `domain` | `str \| None` | Dominio de la cookie; None omite el atributo. |
| `secure` | `bool` | Activa el atributo Secure de la cookie. |
| `http_only` | `bool` | Activa el atributo HttpOnly de la cookie. |
| `same_site` | `Literal["lax", "strict", "none"] \| None` | Política SameSite; None la omite, mientras que la cadena "none" requiere secure=True. |
| `partitioned` | `bool` | Activa el atributo Partitioned de la cookie. |

Tipo de retorno declarado: `Self`.

```python
def withCookies(
    self,
    cookies: Mapping[str, str | Mapping[str, Any]],
) -> Self:
```

Llama setCookie por cada entrada y devuelve self. Propaga errores; las cookies anteriores permanecen si falla una entrada posterior.

| Parámetro | Tipo | Significado |
|---|---|---|
| `cookies` | `Mapping[str, str \| Mapping[str, Any]]` | Nombres de cookies asociados a cadenas o mappings de opciones para setCookie(). |

Tipo de retorno declarado: `Self`.

```python
def withoutCookie(
    self,
    key: str,
    *,
    path: str = "/",
    domain: str | None = None,
) -> Self:
```

Llama deleteCookie y devuelve self; mismos errores y mutación.

| Parámetro | Tipo | Significado |
|---|---|---|
| `key` | `str` | Clave de cabecera, cookie, flash o consulta, según el método. |
| `path` | `str` | Ruta de archivo para respuestas de archivo; ruta URL para métodos de cookies. |
| `domain` | `str \| None` | Dominio de la cookie; None omite el atributo. |

Tipo de retorno declarado: `Self`.

```python
def withFlash(self, key: str, value: Any = None) -> Self:
```

Encola key/value en el dict flash de la respuesta y devuelve self. StartSessionMiddleware realiza la persistencia posterior en sesión.

| Parámetro | Tipo | Significado |
|---|---|---|
| `key` | `str` | Clave de cabecera, cookie, flash o consulta, según el método. |
| `value` | `Any` | Valor asociado a key. |

Tipo de retorno declarado: `Self`.

```python
def withInput(self, values: Mapping[str, Any]) -> Self:
```

Fusiona entrada anterior filtrada en flash y devuelve self. Excluye las claves superiores _csrf, csrf_token, current_password, new_password, password y password_confirmation; no filtra valores anidados de forma recursiva.

| Parámetro | Tipo | Significado |
|---|---|---|
| `values` | `Mapping[str, Any]` | Mapping de datos enviados que se encola como entrada anterior. |

Tipo de retorno declarado: `Self`.

```python
def withErrors(self, errors: Mapping[str, Any] | Exception) -> Self:
```

Normaliza errores de campos a listas de mensajes, fusiona el bag de errores flash y devuelve self. TypeError si una excepción que no es mapping no proporciona errors como mapping ni datos failure.

| Parámetro | Tipo | Significado |
|---|---|---|
| `errors` | `Mapping[str, Any] \| Exception` | Mapping de campos y mensajes o excepción aceptada por normalize_errors(). |

Tipo de retorno declarado: `Self`.

```python
def getFlashData(self) -> dict[str, Any] | None:
```

Devuelve el dict flash interno o None sin copiar.

Tipo de retorno declarado: `dict[str, Any] | None`.

```python
def getBody(self) -> bytes | None:
```

Devuelve bytes almacenados o None para contenido en flujo.

Tipo de retorno declarado: `bytes | None`.

```python
def getStream(self) -> AsyncIterable[bytes] | None:
```

Devuelve el iterable async almacenado o None.

Tipo de retorno declarado: `AsyncIterable[bytes] | None`.

```python
def hasStream(self) -> bool:
```

Indica si hay un flujo almacenado.

Tipo de retorno declarado: `bool`.

```python
async def runBackground(self) -> None:
```

Espera la tarea background si existe; devuelve None y propaga sus fallos. Llamadas repetidas vuelven a ejecutarla.

Tipo de retorno declarado: `None`.

```python
def getStatusCode(self) -> int:
```

Devuelve status_code.

Tipo de retorno declarado: `int`.

```python
def getMediaType(self) -> str | None:
```

Devuelve media_type.

Tipo de retorno declarado: `str | None`.

<a id="api-004"></a>

### HTMLResponse

[`orionis.http.responses.HTMLResponse`](../responses.py)

```python
class HTMLResponse(Response):
```

Hereda Response; establece media_type='text/html' y Content-Type con UTF-8 si no se proporcionó. Hereda los demás métodos y excepciones.

```python
def __init__(
    self,
    content: str | bytes = "",
    status_code: HTTPStatus | int = 200,
    headers: Mapping[str, str] | None = None,
    background: BackgroundTask | None = None,
) -> None:
```

Renderiza content de inmediato y devuelve None; hereda validación y errores de renderizado de Response.

| Parámetro | Tipo | Significado |
|---|---|---|
| `content` | `str \| bytes` | Cuerpo o valor que se renderiza; la interpretación depende de la clase de respuesta. |
| `status_code` | `HTTPStatus \| int` | Código HTTP; la respuesta base valida enteros entre 100 y 599. |
| `headers` | `Mapping[str, str] \| None` | Cabeceras iniciales de respuesta, con nombres almacenados en minúsculas. |
| `background` | `BackgroundTask \| None` | BackgroundTask que se espera al llamar runBackground(). |

Tipo de retorno declarado: `None`.

<a id="api-005"></a>

### PlainTextResponse

[`orionis.http.responses.PlainTextResponse`](../responses.py)

```python
class PlainTextResponse(Response):
```

Hereda Response; establece media_type='text/plain' y Content-Type con UTF-8 si no se proporcionó. Hereda los demás métodos y excepciones.

```python
def __init__(
    self,
    content: str | bytes = "",
    status_code: HTTPStatus | int = 200,
    headers: Mapping[str, str] | None = None,
    background: BackgroundTask | None = None,
) -> None:
```

Renderiza content de inmediato y devuelve None; hereda validación y errores de renderizado de Response.

| Parámetro | Tipo | Significado |
|---|---|---|
| `content` | `str \| bytes` | Cuerpo o valor que se renderiza; la interpretación depende de la clase de respuesta. |
| `status_code` | `HTTPStatus \| int` | Código HTTP; la respuesta base valida enteros entre 100 y 599. |
| `headers` | `Mapping[str, str] \| None` | Cabeceras iniciales de respuesta, con nombres almacenados en minúsculas. |
| `background` | `BackgroundTask \| None` | BackgroundTask que se espera al llamar runBackground(). |

Tipo de retorno declarado: `None`.

<a id="api-006"></a>

### JSONResponse

[`orionis.http.responses.JSONResponse`](../responses.py)

```python
class JSONResponse(Response):
```

Response con application/json; la salida predeterminada usa msgspec.json.encode. Las opciones de formato pueden cambiar a json.dumps. El hook privado convierte datetime/date/time a texto ISO, Decimal/UUID a cadenas, Enum a su valor y conjuntos a listas cuando el codificador delega en él.

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

Guarda opciones JSON antes de que Response renderice content; añade Content-Type si falta. Hereda validación de Response y errores de codificación JSON.

| Parámetro | Tipo | Significado |
|---|---|---|
| `content` | `Any` | Cuerpo o valor que se renderiza; la interpretación depende de la clase de respuesta. |
| `status_code` | `HTTPStatus \| int` | Código HTTP; la respuesta base valida enteros entre 100 y 599. |
| `headers` | `Mapping[str, str] \| None` | Cabeceras iniciales de respuesta, con nombres almacenados en minúsculas. |
| `background` | `BackgroundTask \| None` | BackgroundTask que se espera al llamar runBackground(). |
| `indent` | `int \| None` | Sangría JSON; None permite salida compacta. |
| `ensure_ascii` | `bool` | Escapa caracteres no ASCII mediante el codificador JSON estándar si es true. |
| `separators` | `tuple[str, str] \| None` | Par de separadores JSON de elementos/claves; se pasa a json.dumps en esa ruta. |
| `default` | `Any \| None` | Hook de codificación; None selecciona JSONResponse._defaultEncoder. |

Tipo de retorno declarado: `None`.

```python
def render(self, content: Any) -> bytes:
```

Devuelve bytes JSON. Usa msgspec solo con indent=None, ensure_ascii=False y separators=None; en otro caso json.dumps. Los objetos no admitidos lanzan TypeError mediante el hook predeterminado y se propagan errores del codificador/hook. No modifica el cuerpo almacenado.

| Parámetro | Tipo | Significado |
|---|---|---|
| `content` | `Any` | Cuerpo o valor que se renderiza; la interpretación depende de la clase de respuesta. |

Tipo de retorno declarado: `bytes`.

<a id="api-007"></a>

### RedirectResponse

[`orionis.http.responses.RedirectResponse`](../responses.py)

```python
class RedirectResponse(Response):
```

Response con cuerpo de texto y cabecera Location; hereda todos los métodos de respuesta.

```python
def __init__(
    self,
    url: str,
    status_code: HTTPStatus | int = 302,
    headers: Mapping[str, str] | None = None,
    background: BackgroundTask | None = None,
) -> None:
```

Requiere url str (TypeError en otro caso) y estado 300–399 (ValueError fuera del rango). Establece Location en url y cuerpo "Redirecting to {url}"; también propaga errores de Response. No comprueba el origen de destino.

| Parámetro | Tipo | Significado |
|---|---|---|
| `url` | `str` | Cadena con el destino de redirección. |
| `status_code` | `HTTPStatus \| int` | Código HTTP; la respuesta base valida enteros entre 100 y 599. |
| `headers` | `Mapping[str, str] \| None` | Cabeceras iniciales de respuesta, con nombres almacenados en minúsculas. |
| `background` | `BackgroundTask \| None` | BackgroundTask que se espera al llamar runBackground(). |

Tipo de retorno declarado: `None`.

<a id="api-008"></a>

### StreamingResponse

[`orionis.http.responses.StreamingResponse`](../responses.py)

```python
class StreamingResponse(Response):
```

Response que conserva un flujo async; getBody() es None. Los iterables síncronos se envuelven en un generador async, pero la iteración sigue siendo síncrona.

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

Acepta AsyncIterable o Iterable; en otro caso TypeError. La envoltura síncrona acepta bytes y convierte bytearray/memoryview; otros bloques lanzan TypeError durante la iteración. Conserva bloques async para los adaptadores. Añade Content-Type a partir de media_type si falta. Hereda errores de Response; los errores de iteración ocurren al consumir.

| Parámetro | Tipo | Significado |
|---|---|---|
| `content` | `AsyncIterable[bytes] \| Iterable[bytes]` | Cuerpo o valor que se renderiza; la interpretación depende de la clase de respuesta. |
| `status_code` | `HTTPStatus \| int` | Código HTTP; la respuesta base valida enteros entre 100 y 599. |
| `headers` | `Mapping[str, str] \| None` | Cabeceras iniciales de respuesta, con nombres almacenados en minúsculas. |
| `media_type` | `str \| None` | Tipo MIME de la respuesta. |
| `background` | `BackgroundTask \| None` | BackgroundTask que se espera al llamar runBackground(). |

Tipo de retorno declarado: `None`.

<a id="api-009"></a>

### FileResponse

[`orionis.http.responses.FileResponse`](../responses.py)

```python
class FileResponse(StreamingResponse):
```

StreamingResponse para un archivo regular. El constructor realiza stat síncrono; el iterador abre, lee y cierra mediante helpers con executor, con lectura predeterminada de 64 KiB. No captura una instantánea del contenido.

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

Consulta stat de path, comprueba archivo regular, deduce MIME y establece Content-Length; filename activa disposición attachment. FileNotFoundError/OSError por stat, ValueError por ruta no regular o chunk_size no positivo, TypeError por chunk_size no entero; propaga errores heredados. La lectura posterior puede fallar por separado.

| Parámetro | Tipo | Significado |
|---|---|---|
| `path` | `str \| Path` | Ruta de archivo para respuestas de archivo; ruta URL para métodos de cookies. |
| `status_code` | `int` | Código HTTP; la respuesta base valida enteros entre 100 y 599. |
| `headers` | `Mapping[str, str] \| None` | Cabeceras iniciales de respuesta, con nombres almacenados en minúsculas. |
| `media_type` | `str \| None` | Tipo MIME de la respuesta. |
| `filename` | `str \| None` | Nombre del adjunto; download() usa el nombre del archivo si se omite. |
| `chunk_size` | `int` | Tamaño entero positivo de bloque de lectura en bytes. |
| `background` | `BackgroundTask \| None` | BackgroundTask que se espera al llamar runBackground(). |

Tipo de retorno declarado: `None`.

```python
def getPath(self) -> Path:
```

Devuelve el Path almacenado sin resolverlo.

Tipo de retorno declarado: `Path`.

```python
def getFileSize(self) -> int:
```

Devuelve el tamaño registrado por stat en el constructor; no lo actualiza.

Tipo de retorno declarado: `int`.

<a id="api-010"></a>

### ResponseFactory

[`orionis.http.factory.ResponseFactory`](../factory.py)

```python
class ResponseFactory:
```

Factoría sin estado con __slots__=(). El módulo crea response: ResponseFactory = ResponseFactory() al importarse; permite construir más factorías. Es una instancia compartida de conveniencia, no un Singleton impuesto.

```python
def view(self, template: str, **context: Any) -> PendingView:
```

Devuelve View.make(template, **context), un PendingView que se espera para renderizar. Usa la fachada de vistas enlazada y propaga fallos de resolución/renderizado cuando se ejecuta la operación delegada.

| Parámetro | Tipo | Significado |
|---|---|---|
| `template` | `str` | Identificador de plantilla que se pasa a View.make. |
| `context` | `Any` | Argumentos por nombre del contexto de plantilla. |

Tipo de retorno declarado: `PendingView`.

```python
def html(
    self,
    content: str | bytes = "",
    status_code: HTTPStatus | int = 200,
    headers: Mapping[str, str] | None = None,
    background: BackgroundTask | None = None,
) -> HTMLResponse:
```

Construye y devuelve HTMLResponse con estos argumentos; los parámetros, efectos y excepciones son los de su constructor.

| Parámetro | Tipo | Significado |
|---|---|---|
| `content` | `str \| bytes` | Cuerpo o valor que se renderiza; la interpretación depende de la clase de respuesta. |
| `status_code` | `HTTPStatus \| int` | Código HTTP; la respuesta base valida enteros entre 100 y 599. |
| `headers` | `Mapping[str, str] \| None` | Cabeceras iniciales de respuesta, con nombres almacenados en minúsculas. |
| `background` | `BackgroundTask \| None` | BackgroundTask que se espera al llamar runBackground(). |

Tipo de retorno declarado: `HTMLResponse`.

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

Construye y devuelve JSONResponse con estos argumentos; los parámetros, efectos y excepciones son los de su constructor.

| Parámetro | Tipo | Significado |
|---|---|---|
| `content` | `Any` | Cuerpo o valor que se renderiza; la interpretación depende de la clase de respuesta. |
| `status_code` | `HTTPStatus \| int` | Código HTTP; la respuesta base valida enteros entre 100 y 599. |
| `headers` | `Mapping[str, str] \| None` | Cabeceras iniciales de respuesta, con nombres almacenados en minúsculas. |
| `background` | `BackgroundTask \| None` | BackgroundTask que se espera al llamar runBackground(). |
| `indent` | `int \| None` | Sangría JSON; None permite salida compacta. |
| `ensure_ascii` | `bool` | Escapa caracteres no ASCII mediante el codificador JSON estándar si es true. |
| `separators` | `tuple[str, str] \| None` | Par de separadores JSON de elementos/claves; se pasa a json.dumps en esa ruta. |
| `default` | `Any \| None` | Hook de codificación; None selecciona JSONResponse._defaultEncoder. |

Tipo de retorno declarado: `JSONResponse`.

```python
def text(
    self,
    content: str | bytes = "",
    status_code: HTTPStatus | int = 200,
    headers: Mapping[str, str] | None = None,
    background: BackgroundTask | None = None,
) -> PlainTextResponse:
```

Construye y devuelve PlainTextResponse con estos argumentos; los parámetros, efectos y excepciones son los de su constructor.

| Parámetro | Tipo | Significado |
|---|---|---|
| `content` | `str \| bytes` | Cuerpo o valor que se renderiza; la interpretación depende de la clase de respuesta. |
| `status_code` | `HTTPStatus \| int` | Código HTTP; la respuesta base valida enteros entre 100 y 599. |
| `headers` | `Mapping[str, str] \| None` | Cabeceras iniciales de respuesta, con nombres almacenados en minúsculas. |
| `background` | `BackgroundTask \| None` | BackgroundTask que se espera al llamar runBackground(). |

Tipo de retorno declarado: `PlainTextResponse`.

```python
def redirect(
    self,
    url: str,
    status_code: HTTPStatus | int = 302,
    headers: Mapping[str, str] | None = None,
    background: BackgroundTask | None = None,
) -> RedirectResponse:
```

Construye y devuelve RedirectResponse con estos argumentos; los parámetros, efectos y excepciones son los de su constructor.

| Parámetro | Tipo | Significado |
|---|---|---|
| `url` | `str` | Cadena con el destino de redirección. |
| `status_code` | `HTTPStatus \| int` | Código HTTP; la respuesta base valida enteros entre 100 y 599. |
| `headers` | `Mapping[str, str] \| None` | Cabeceras iniciales de respuesta, con nombres almacenados en minúsculas. |
| `background` | `BackgroundTask \| None` | BackgroundTask que se espera al llamar runBackground(). |

Tipo de retorno declarado: `RedirectResponse`.

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

Construye y devuelve StreamingResponse con estos argumentos; los parámetros, efectos y excepciones son los de su constructor.

| Parámetro | Tipo | Significado |
|---|---|---|
| `content` | `AsyncIterable[bytes] \| Iterable[bytes]` | Cuerpo o valor que se renderiza; la interpretación depende de la clase de respuesta. |
| `status_code` | `HTTPStatus \| int` | Código HTTP; la respuesta base valida enteros entre 100 y 599. |
| `headers` | `Mapping[str, str] \| None` | Cabeceras iniciales de respuesta, con nombres almacenados en minúsculas. |
| `media_type` | `str \| None` | Tipo MIME de la respuesta. |
| `background` | `BackgroundTask \| None` | BackgroundTask que se espera al llamar runBackground(). |

Tipo de retorno declarado: `StreamingResponse`.

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

Construye y devuelve FileResponse con estos argumentos; los parámetros, efectos y excepciones son los de su constructor.

| Parámetro | Tipo | Significado |
|---|---|---|
| `path` | `str \| Path` | Ruta de archivo para respuestas de archivo; ruta URL para métodos de cookies. |
| `status_code` | `HTTPStatus \| int` | Código HTTP; la respuesta base valida enteros entre 100 y 599. |
| `headers` | `Mapping[str, str] \| None` | Cabeceras iniciales de respuesta, con nombres almacenados en minúsculas. |
| `media_type` | `str \| None` | Tipo MIME de la respuesta. |
| `filename` | `str \| None` | Nombre del adjunto; download() usa el nombre del archivo si se omite. |
| `chunk_size` | `int` | Tamaño entero positivo de bloque de lectura en bytes. |
| `background` | `BackgroundTask \| None` | BackgroundTask que se espera al llamar runBackground(). |

Tipo de retorno declarado: `FileResponse`.

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

Construye FileResponse con estado predeterminado 200, fuerza Content-Disposition attachment con filename o nombre de path y la devuelve. Mismas excepciones de archivo/respuesta y consulta stat al sistema de archivos.

| Parámetro | Tipo | Significado |
|---|---|---|
| `path` | `str \| Path` | Ruta de archivo para respuestas de archivo; ruta URL para métodos de cookies. |
| `filename` | `str \| None` | Nombre del adjunto; download() usa el nombre del archivo si se omite. |
| `headers` | `Mapping[str, str] \| None` | Cabeceras iniciales de respuesta, con nombres almacenados en minúsculas. |
| `media_type` | `str \| None` | Tipo MIME de la respuesta. |
| `background` | `BackgroundTask \| None` | BackgroundTask que se espera al llamar runBackground(). |

Tipo de retorno declarado: `FileResponse`.

```python
def noContent(
    self,
    status_code: HTTPStatus | int = 204,
    headers: Mapping[str, str] | None = None,
    background: BackgroundTask | None = None,
) -> Response:
```

Devuelve Response con cuerpo vacío y estado predeterminado 204; acepta otro estado válido. Mismas excepciones del constructor Response.

| Parámetro | Tipo | Significado |
|---|---|---|
| `status_code` | `HTTPStatus \| int` | Código HTTP; la respuesta base valida enteros entre 100 y 599. |
| `headers` | `Mapping[str, str] \| None` | Cabeceras iniciales de respuesta, con nombres almacenados en minúsculas. |
| `background` | `BackgroundTask \| None` | BackgroundTask que se espera al llamar runBackground(). |

Tipo de retorno declarado: `Response`.

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

Construye y devuelve Response con estos argumentos; los parámetros, efectos y excepciones son los de su constructor.

| Parámetro | Tipo | Significado |
|---|---|---|
| `content` | `Any` | Cuerpo o valor que se renderiza; la interpretación depende de la clase de respuesta. |
| `status_code` | `HTTPStatus \| int` | Código HTTP; la respuesta base valida enteros entre 100 y 599. |
| `headers` | `Mapping[str, str] \| None` | Cabeceras iniciales de respuesta, con nombres almacenados en minúsculas. |
| `media_type` | `str \| None` | Tipo MIME de la respuesta. |
| `background` | `BackgroundTask \| None` | BackgroundTask que se espera al llamar runBackground(). |

Tipo de retorno declarado: `Response`.

<a id="api-011"></a>

### BaseMiddleware

[`orionis.http.middleware.BaseMiddleware`](../middleware.py)

```python
class BaseMiddleware(IBaseMiddleware):
```

Implementa IBaseMiddleware y declara __slots__=(). Las subclases proporcionan handle; la implementación base siempre lanza NotImplementedError.

```python
async def handle(
    self,
    request: Request,
    call_next: NextCallable,
) -> Response:
```

Recibe request y la continuación siguiente; declara retorno Response, pero esta implementación siempre lanza NotImplementedError con el nombre de la clase concreta.

| Parámetro | Tipo | Significado |
|---|---|---|
| `request` | `Request` | Request actual. |
| `call_next` | `NextCallable` | Continuación esperable de la siguiente capa de middleware. |

Tipo de retorno declarado: `Response`.

<a id="api-012"></a>

### BaseController

[`orionis.http.base.controller.BaseController`](../base/controller.py)

```python
class BaseController:
```

Clase marcadora vacía para herencia de controladores; sin constructor, campos ni métodos propios y sin comportamiento de despacho propio.

<a id="api-013"></a>

### KernelHTTP

[`orionis.http.kernel.KernelHTTP`](../kernel.py)

```python
class KernelHTTP(IKernelHTTP):
```

Coordinador de despacho HTTP que implementa IKernelHTTP. Orden global: proxies, mantenimiento si está activo, seguridad, preflight CORS y rate limit. Responde OPTIONS desde el resolver antes de construir Request. Orden web: StartSessionMiddleware, CSRFTokenMiddleware, ResolveSessionIdentityMiddleware; API: ResolveTokenIdentityMiddleware; después middleware de ruta y handler. El posprocesamiento CORS ocurre antes del envío.

```python
def __init__(
    self,
    app: IApplication,
    catch: ICatch,
) -> None:
```

Conserva servicios de aplicación/excepciones, desactiva el indicador de arranque y crea caché de instancias middleware. Devuelve None; no arranca el kernel.

| Parámetro | Tipo | Significado |
|---|---|---|
| `app` | `IApplication` | Servicio de aplicación que proporciona configuración, resolución de dependencias y scopes. |
| `catch` | `ICatch` | Gestor de excepciones de la aplicación. |

Tipo de retorno declarado: `None`.

```python
async def boot(self) -> None:
```

Carga/compila rutas, precarga imports de handlers y middleware de ruta, construye respuestas predeterminadas, capas de seguridad/sesión/auth, emisores y registro debug. Devuelve None; llamadas posteriores secuenciales no hacen nada. Propaga fallos de import, rutas, configuración y DI. No hay lock contra arranques concurrentes.

Tipo de retorno declarado: `None`.

```python
async def handleRSGI(
    self,
    scope: Scope,
    protocol: HTTPProtocol,
) -> object | None:
```

Crea adaptador RSGI, entra en application.beginScope(), procesa y envía. Anotado object | None; el emisor actual devuelve None. Requiere boot previo; campos sin inicializar pueden lanzar AttributeError. Delega excepciones de procesamiento a ICatch (o validación/fallback); pueden escapar fallos de scope, envío, background y gestor de errores.

| Parámetro | Tipo | Significado |
|---|---|---|
| `scope` | `Scope` | Dict ASGI o Scope RSGI de Granian entrante, según la firma. |
| `protocol` | `HTTPProtocol` | Protocolo HTTP RSGI de Granian para leer el cuerpo y enviar la respuesta. |

Tipo de retorno declarado: `object | None`.

```python
async def handleASGI(
    self,
    scope: dict,
    receive: object,
    send: object,
) -> None:
```

Crea adaptador ASGI, entra en application.beginScope(), procesa y envía mediante receive/send; devuelve None. Mismo requisito de arranque y límites de captura de excepciones que handleRSGI.

| Parámetro | Tipo | Significado |
|---|---|---|
| `scope` | `dict` | Dict ASGI o Scope RSGI de Granian entrante, según la firma. |
| `receive` | `object` | Callable receive de ASGI, anotado object; BodyStream lo invoca para leer el cuerpo, mientras ASGIResponseAdapter lo recibe sin usarlo. |
| `send` | `object` | Callable send de ASGI usado para emitir mensajes de respuesta. |

Tipo de retorno declarado: `None`.

La clase privada _MiddlewarePipeline conserva estado de continuación por petición y lanza RuntimeError si una capa llama next dos veces. El despacho usa application.invoke/build/call; solo acepta resultados Response, dict y msgspec.Struct (los últimos dos se convierten en JSONResponse). Otros resultados lanzan TypeError. El fallback debe devolver Response. Los errores de validación web usan validation_response; los de API producen JSON 422. Request se inserta en el scope de aplicación para inyección.

<a id="api-014"></a>

### DefaultResponses

[`orionis.http.default.responses.DefaultResponses`](../default/responses.py)

```python
class DefaultResponses(IDefaultResponses):
```

Implementa IDefaultResponses con páginas/recursos incluidos y almacenamiento público de aplicación. Mantiene cachés de instancia y caché de etiquetas HTTP de módulo; construye respuestas nuevas. Lee plantillas de forma síncrona en fallos de caché.

```python
def __init__(
    self,
    app: IApplication,
    directory: Directory,
) -> None:
```

Lee app.name/app.locale e inicializa caché de instancia; devuelve None. Propaga fallos de configuración/servicios.

| Parámetro | Tipo | Significado |
|---|---|---|
| `app` | `IApplication` | Servicio de aplicación que proporciona configuración, resolución de dependencias y scopes. |
| `directory` | `Directory` | Servicio de directorios de la aplicación; storagePublic() localiza recursos públicos. |

Tipo de retorno declarado: `None`.

```python
def __getitem__(self, key: str) -> object | None:
```

Devuelve objeto cacheado para key o None sin lanzar KeyError.

| Parámetro | Tipo | Significado |
|---|---|---|
| `key` | `str` | Clave de cabecera, cookie, flash o consulta, según el método. |

Tipo de retorno declarado: `object | None`.

```python
def __setitem__(self, key: str, value: object) -> None:
```

Almacena value bajo key; devuelve None.

| Parámetro | Tipo | Significado |
|---|---|---|
| `key` | `str` | Clave de cabecera, cookie, flash o consulta, según el método. |
| `value` | `object` | Valor asociado a key. |

Tipo de retorno declarado: `None`.

```python
def __contains__(self, key: str) -> bool:
```

Indica si key está cacheada.

| Parámetro | Tipo | Significado |
|---|---|---|
| `key` | `str` | Clave de cabecera, cookie, flash o consulta, según el método. |

Tipo de retorno declarado: `bool`.

```python
def __delitem__(self, key: str) -> None:
```

Elimina key si está cacheada; devuelve None e ignora claves ausentes.

| Parámetro | Tipo | Significado |
|---|---|---|
| `key` | `str` | Clave de cabecera, cookie, flash o consulta, según el método. |

Tipo de retorno declarado: `None`.

```python
def favicon(self) -> FileResponse | Response:
```

Devuelve FileResponse nueva y cachea ruta/tipo. Busca favicon.ico, .png, .svg en storagePublic(), luego assets/favicon.ico incluido; en otro caso HTML 404. Establece public max-age=31536000, immutable. Propaga errores de archivo/respuesta, incluido un archivo cacheado eliminado después.

Tipo de retorno declarado: `FileResponse | Response`.

```python
def robotsTxt(self) -> FileResponse | Response:
```

Usa storagePublic()/robots.txt, luego el archivo incluido o HTML 404; cachea ruta y devuelve FileResponse nueva con public max-age=3600. Propaga errores de archivo/respuesta.

Tipo de retorno declarado: `FileResponse | Response`.

```python
def sitemapXml(self) -> FileResponse | Response:
```

Usa storagePublic()/sitemap.xml con public max-age=600; cachea ruta y devuelve FileResponse, o HTML 404 si falta. No hay sitemap alternativo incluido; propaga errores de archivo/respuesta.

Tipo de retorno declarado: `FileResponse | Response`.

```python
def health(self, request: Request) -> HTMLResponse | JSONResponse:
```

Lee app.maintenance en cada llamada: false produce 200 con plantilla up, true 503 con down. Los valores JSON de message son "Online Application" y "Application in Maintenance", respectivamente. Usa wantsJson() para JSON; en otro caso lee/cachea HTML con sustitución de nombre/locale. Devuelve respuesta nueva con no-cache/no-store. Pueden propagarse claves de mantenimiento inválidas y fallos de archivo/codificación.

| Parámetro | Tipo | Significado |
|---|---|---|
| `request` | `Request` | Request actual. |

Tipo de retorno declarado: `HTMLResponse | JSONResponse`.

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

Valida status_code mediante el auxiliar privado _validate_status_code antes de renderizar cualquier formato o leer una plantilla: valores no enteros lanzan TypeError y valores fuera de 100–599 lanzan ValueError. JSON conserva content dict o envuelve texto como {"message": content}. HTML lee/cachea un plan de sustituciones y usa la etiqueta de HTTPStatus si existe, o "HTTP {code}" para un entero válido ausente del enum. Su descripción es el texto recibido, str(content["message"]) si existe esa clave, o json.dumps(content); html.escape la convierte en texto HTML antes de sustituirla. El registro en consola de la plantilla lee título y descripción mediante textContent del DOM en lugar de interpolarlos en literales JavaScript. Añade no-cache si falta. Propaga errores de archivo, serialización y respuesta.

| Parámetro | Tipo | Significado |
|---|---|---|
| `status_code` | `int \| HTTPStatus` | Entero entre 100 y 599, validado antes de renderizar; los códigos HTML ausentes del enum usan la etiqueta HTTP {code}. |
| `content` | `str \| dict` | Texto de error o diccionario; JSON conserva los valores y la descripción HTML es texto escapado. |
| `expects_json` | `bool` | Selecciona JSON si es true; en caso contrario HTML. |
| `headers` | `dict[str, str] \| None` | Cabeceras iniciales de respuesta, con nombres almacenados en minúsculas. |

Tipo de retorno declarado: `HTMLResponse | JSONResponse`.

```python
def exception(
    self,
    request_path: str,
    request_method: str,
    exception: BaseException,
    status_code: int | HTTPStatus = HTTPStatus.INTERNAL_SERVER_ERROR,
) -> HTMLResponse:
```

Lee/cachea plantilla de excepción, obtiene zona DateTime, configuración y metadatos de ejecución, parsea la excepción y sustituye datos de petición/traceback. Devuelve HTMLResponse con no-cache. No restringe por sí mismo la página según app.debug; propaga errores de archivo, fachada, parser y serialización.

| Parámetro | Tipo | Significado |
|---|---|---|
| `request_path` | `str` | Ruta de la petición insertada en la página de excepción. |
| `request_method` | `str` | Método de la petición insertado en la página de excepción. |
| `exception` | `BaseException` | Excepción que inspecciona ExceptionParser. |
| `status_code` | `int \| HTTPStatus` | Código HTTP; la respuesta base valida enteros entre 100 y 599. |

Tipo de retorno declarado: `HTMLResponse`.

<a id="api-015"></a>

### LoginController

[`orionis.http.default.controllers.login_controller.LoginController`](../default/controllers/login_controller.py)

```python
class LoginController(BaseController):
```

BaseController predeterminado para login/logout; depende de vistas configuradas e IAuthManager. La casilla remember recuerda el email en usrname; no pasa una opción remember a auth.attempt.

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

Establece redirect_to desde auth.session.home o /home; devuelve None. Propaga errores de configuración.

| Parámetro | Tipo | Significado |
|---|---|---|
| `application` | `IApplication` | Configuración de la aplicación para seleccionar la redirección de login. |

Tipo de retorno declarado: `None`.

```python
async def index(
    self,
) -> HttpResponse:
```

Espera auth.login mediante response.view y devuelve la respuesta renderizada; propaga errores de vista/servicios.

Tipo de retorno declarado: `HttpResponse`.

```python
async def login(
    self,
    request: Request,
    payload: LoginSchema,
    auth: IAuthManager,
) -> HttpResponse:
```

Lee request.data() y llama auth.attempt con email/password de payload. Un fallo devuelve redirección /login con entrada anterior filtrada y errores de email. Éxito redirige a redirect_to y guarda email en usrname durante 259200 segundos solo si remember crudo == "on"; en otro caso cookie vacía con Max-Age=0. Propaga errores de auth, cuerpo, cookies y respuesta; la autenticación modifica estado externo auth/sesión.

| Parámetro | Tipo | Significado |
|---|---|---|
| `request` | `Request` | Request actual. |
| `payload` | `LoginSchema` | LoginSchema validado con email y password. |
| `auth` | `IAuthManager` | Gestor de autenticación usado para attempt() o logout(). |

Tipo de retorno declarado: `HttpResponse`.

```python
async def logout(
    self,
    auth: IAuthManager,
) -> HttpResponse:
```

Espera auth.logout() y devuelve redirección a /. Propaga fallos de auth/respuesta y modifica estado auth/sesión.

| Parámetro | Tipo | Significado |
|---|---|---|
| `auth` | `IAuthManager` | Gestor de autenticación usado para attempt() o logout(). |

Tipo de retorno declarado: `HttpResponse`.

<a id="api-016"></a>

### RegisterController

[`orionis.http.default.controllers.register_controller.RegisterController`](../default/controllers/register_controller.py)

```python
class RegisterController(BaseController):
```

BaseController acoplado a la aplicación: importa directamente app.models.user.User y usa fachadas DB/Hash y vista auth.register.

```python
    REGISTER_VIEW_NAME: str = "auth.register"
    REGISTER_REDIRECT_PATH: str = "/login"
```

```python
async def index(
    self,
) -> HttpResponse:
```

Espera auth.register y devuelve su respuesta; propaga errores de vista/servicios.

Tipo de retorno declarado: `HttpResponse`.

```python
async def register(
    self,
    request: RegisterSchema,
) -> HttpResponse:
```

Inicia transacción, hashea password, recorta name, recorta/convierte email a minúsculas, guarda User y hace commit; devuelve redirección /login con flash de éxito. Las excepciones dentro del try causan rollback y renderizado auth.register con errores/entrada anterior. beginTransaction ocurre fuera del try; pueden propagarse fallos de rollback/renderizado. Escribe en base de datos y hashea contraseña.

| Parámetro | Tipo | Significado |
|---|---|---|
| `request` | `RegisterSchema` | RegisterSchema validado, pese al nombre request del parámetro. |

Tipo de retorno declarado: `HttpResponse`.

<a id="api-017"></a>

### IRequest

[contracts/request.py](../contracts/request.py)

Contrato ABC abstracto de Request. Los parámetros y retornos tienen el significado del método correspondiente documentado arriba; estas declaraciones no implementan I/O ni políticas de estado. Los miembros abstractos sin implementar impiden instanciar (TypeError). Los cuerpos base solo contienen docstrings y no imponen el comportamiento concreto documentado.

```python
class IRequest(ABC):
```

```python
@property
@abstractmethod
def url(self) -> str:
```

`url`: significado de parámetros/retorno: `Request.url`. Excepciones y efectos concretos dependen de la implementación.

```python
@property
@abstractmethod
def baseUrl(self) -> str:
```

`baseUrl`: significado de parámetros/retorno: `Request.baseUrl`. Excepciones y efectos concretos dependen de la implementación.

```python
@property
@abstractmethod
def headers(self) -> Headers:
```

`headers`: significado de parámetros/retorno: `Request.headers`. Excepciones y efectos concretos dependen de la implementación.

```python
@property
@abstractmethod
def queryParams(self) -> QueryParams:
```

`queryParams`: significado de parámetros/retorno: `Request.queryParams`. Excepciones y efectos concretos dependen de la implementación.

```python
@property
@abstractmethod
def cookies(self) -> Cookies:
```

`cookies`: significado de parámetros/retorno: `Request.cookies`. Excepciones y efectos concretos dependen de la implementación.

```python
@property
@abstractmethod
def ip(self) -> str | None:
```

`ip`: significado de parámetros/retorno: `Request.ip`. Excepciones y efectos concretos dependen de la implementación.

```python
@property
@abstractmethod
def port(self) -> int | None:
```

`port`: significado de parámetros/retorno: `Request.port`. Excepciones y efectos concretos dependen de la implementación.

```python
@property
@abstractmethod
def forwarded(self) -> dict[str, Any]:
```

`forwarded`: significado de parámetros/retorno: `Request.forwarded`. Excepciones y efectos concretos dependen de la implementación.

```python
@property
@abstractmethod
def method(self) -> str:
```

`method`: significado de parámetros/retorno: `Request.method`. Excepciones y efectos concretos dependen de la implementación.

```python
@property
@abstractmethod
def scheme(self) -> str:
```

`scheme`: significado de parámetros/retorno: `Request.scheme`. Excepciones y efectos concretos dependen de la implementación.

```python
@property
@abstractmethod
def path(self) -> str:
```

`path`: significado de parámetros/retorno: `Request.path`. Excepciones y efectos concretos dependen de la implementación.

```python
@property
@abstractmethod
def interface(self) -> Interface:
```

`interface`: significado de parámetros/retorno: `Request.interface`. Excepciones y efectos concretos dependen de la implementación.

```python
@property
@abstractmethod
def httpVersion(self) -> str:
```

`httpVersion`: significado de parámetros/retorno: `Request.httpVersion`. Excepciones y efectos concretos dependen de la implementación.

```python
@property
@abstractmethod
def userAgent(self) -> str | None:
```

`userAgent`: significado de parámetros/retorno: `Request.userAgent`. Excepciones y efectos concretos dependen de la implementación.

```python
@property
@abstractmethod
def apiKey(self) -> str | None:
```

`apiKey`: significado de parámetros/retorno: `Request.apiKey`. Excepciones y efectos concretos dependen de la implementación.

```python
@property
@abstractmethod
def bearerToken(self) -> str | None:
```

`bearerToken`: significado de parámetros/retorno: `Request.bearerToken`. Excepciones y efectos concretos dependen de la implementación.

```python
@property
@abstractmethod
def authorization(self) -> str | None:
```

`authorization`: significado de parámetros/retorno: `Request.authorization`. Excepciones y efectos concretos dependen de la implementación.

```python
@property
@abstractmethod
def accept(self) -> str | None:
```

`accept`: significado de parámetros/retorno: `Request.accept`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
def wantsJson(self) -> bool:
```

`wantsJson`: significado de parámetros/retorno: `Request.wantsJson`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
def accepts(self, mime: str) -> bool:
```

`accepts`: significado de parámetros/retorno: `Request.accepts`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
def isAjax(self) -> bool:
```

`isAjax`: significado de parámetros/retorno: `Request.isAjax`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
def wantsHtml(self) -> bool:
```

`wantsHtml`: significado de parámetros/retorno: `Request.wantsHtml`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
def wantsXml(self) -> bool:
```

`wantsXml`: significado de parámetros/retorno: `Request.wantsXml`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
async def stream(self) -> AsyncGenerator[bytes]:
```

`stream`: significado de parámetros/retorno: `Request.stream`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
async def body(self) -> bytes:
```

`body`: significado de parámetros/retorno: `Request.body`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
async def json(self) -> object:
```

`json`: significado de parámetros/retorno: `Request.json`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
async def payload(self) -> Any:
```

`payload`: significado de parámetros/retorno: `Request.payload`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
async def formUrlEncoded(self) -> dict[str, Any]:
```

`formUrlEncoded`: significado de parámetros/retorno: `Request.formUrlEncoded`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
async def raw(self) -> bytes:
```

`raw`: significado de parámetros/retorno: `Request.raw`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
async def text(self) -> str:
```

`text`: significado de parámetros/retorno: `Request.text`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
async def xml(self) -> ET.Element:
```

`xml`: significado de parámetros/retorno: `Request.xml`. El contrato documenta `xml.etree.ElementTree.ParseError` para XML mal formado y `defusedxml.common.EntitiesForbidden`, subclase de `DefusedXmlException`, para declaraciones de entidades internas o externas. Se permiten DTD sin declaraciones de entidades; no se resuelven recursos externos. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
async def msgpack(self) -> object:
```

`msgpack`: declara object para cualquier valor MessagePack decodificado, igual que `Request.msgpack`; el docstring declara msgspec.DecodeError para entradas inválidas. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
async def form(self) -> FormData:
```

`form`: significado de parámetros/retorno: `Request.form`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
async def data(self) -> dict[str, Any]:
```

`data`: significado de parámetros/retorno: `Request.data`. El contrato documenta TypeError para un valor JSON/MessagePack decodificado que no sea mapping, y ValueError para un cuerpo JSON o MessagePack vacío/no decodificable o un fallo de parseo multipart. Excepciones y efectos concretos dependen de la implementación.

```python
@property
@abstractmethod
def state(self) -> SimpleNamespace:
```

`state`: significado de parámetros/retorno: `Request.state`. Excepciones y efectos concretos dependen de la implementación.

```python
@property
@abstractmethod
def scope(self) -> dict[str, Any]:
```

`scope`: significado de parámetros/retorno: `Request.scope`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
def routeParam(self, key: str) -> object:
```

`routeParam`: significado de parámetros/retorno: `Request.routeParam`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
def routeParams(self) -> dict[str, Any]:
```

`routeParams`: significado de parámetros/retorno: `Request.routeParams`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
def csrfToken(self) -> str | None:
```

`csrfToken`: significado de parámetros/retorno: `Request.csrfToken`. Excepciones y efectos concretos dependen de la implementación.

El contrato anota xml() como ET.Element (ET se importa solo bajo TYPE_CHECKING); Request usa XMLElement. payload() declara Any aquí y object en Request. Se conservan esas anotaciones sin normalizarlas.

<a id="api-018"></a>

### IResponse

[contracts/response.py](../contracts/response.py)

Contrato ABC abstracto de Response. Los parámetros y retornos tienen el significado del método correspondiente documentado arriba; estas declaraciones no implementan I/O ni políticas de estado. Los miembros abstractos sin implementar impiden instanciar (TypeError). Los cuerpos base solo contienen docstrings y no imponen el comportamiento concreto documentado.

```python
class IResponse(ABC):
```

```python
@abstractmethod
def render(self, content: Any) -> bytes:
```

`render`: significado de parámetros/retorno: `Response.render`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
def addHeader(self, key: str, value: str) -> None:
```

`addHeader`: significado de parámetros/retorno: `Response.addHeader`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
def setHeader(self, key: str, value: str) -> None:
```

`setHeader`: significado de parámetros/retorno: `Response.setHeader`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
def getHeader(self, key: str) -> list[str] | None:
```

`getHeader`: significado de parámetros/retorno: `Response.getHeader`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
def hasHeader(self, key: str) -> bool:
```

`hasHeader`: significado de parámetros/retorno: `Response.hasHeader`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
def removeHeader(self, key: str) -> None:
```

`removeHeader`: significado de parámetros/retorno: `Response.removeHeader`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
def getRawHeaders(self) -> list[tuple[bytes, bytes]]:
```

`getRawHeaders`: significado de parámetros/retorno: `Response.getRawHeaders`. Excepciones y efectos concretos dependen de la implementación.

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

`setCookie`: significado de parámetros/retorno: `Response.setCookie`. Excepciones y efectos concretos dependen de la implementación.

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

`deleteCookie`: significado de parámetros/retorno: `Response.deleteCookie`. Excepciones y efectos concretos dependen de la implementación.

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

`withCookie`: significado de parámetros/retorno: `Response.withCookie`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
def withCookies(
    self,
    cookies: Mapping[str, str | Mapping[str, Any]],
) -> Self:
```

`withCookies`: significado de parámetros/retorno: `Response.withCookies`. Excepciones y efectos concretos dependen de la implementación.

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

`withoutCookie`: significado de parámetros/retorno: `Response.withoutCookie`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
def withFlash(self, key: str, value: Any = None) -> Self:
```

`withFlash`: significado de parámetros/retorno: `Response.withFlash`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
def withInput(self, values: Mapping[str, Any]) -> Self:
```

`withInput`: significado de parámetros/retorno: `Response.withInput`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
def withErrors(self, errors: Mapping[str, Any] | Exception) -> Self:
```

`withErrors`: significado de parámetros/retorno: `Response.withErrors`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
def getFlashData(self) -> dict[str, Any] | None:
```

`getFlashData`: significado de parámetros/retorno: `Response.getFlashData`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
def getBody(self) -> bytes | None:
```

`getBody`: significado de parámetros/retorno: `Response.getBody`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
def getStream(self) -> AsyncIterable[bytes] | None:
```

`getStream`: significado de parámetros/retorno: `Response.getStream`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
def hasStream(self) -> bool:
```

`hasStream`: significado de parámetros/retorno: `Response.hasStream`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
async def runBackground(self) -> None:
```

`runBackground`: significado de parámetros/retorno: `Response.runBackground`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
def getStatusCode(self) -> int:
```

`getStatusCode`: significado de parámetros/retorno: `Response.getStatusCode`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
def getMediaType(self) -> str | None:
```

`getMediaType`: significado de parámetros/retorno: `Response.getMediaType`. Excepciones y efectos concretos dependen de la implementación.

<a id="api-019"></a>

### IKernelHTTP

[contracts/kernel.py](../contracts/kernel.py)

Contrato ABC abstracto de KernelHTTP. Los parámetros y retornos tienen el significado del método correspondiente documentado arriba; estas declaraciones no implementan I/O ni políticas de estado. Los miembros abstractos sin implementar impiden instanciar (TypeError). Los cuerpos base solo contienen docstrings y no imponen el comportamiento concreto documentado.

```python
class IKernelHTTP(ABC):
```

```python
@abstractmethod
async def boot(self) -> None:
```

`boot`: significado de parámetros/retorno: `KernelHTTP.boot`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
async def handleRSGI(
    self,
    scope: Scope,
    protocol: HTTPProtocol,
) -> object | None:
```

`handleRSGI`: significado de parámetros/retorno: `KernelHTTP.handleRSGI`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
async def handleASGI(
    self,
    scope: dict,
    receive: object,
    send: object,
) -> None:
```

`handleASGI`: significado de parámetros/retorno: `KernelHTTP.handleASGI`. Excepciones y efectos concretos dependen de la implementación.

<a id="api-020"></a>

### IDefaultResponses

[default/contracts/responses.py](../default/contracts/responses.py)

Contrato ABC abstracto de DefaultResponses. Los parámetros y retornos tienen el significado del método correspondiente documentado arriba; estas declaraciones no implementan I/O ni políticas de estado. Los miembros abstractos sin implementar impiden instanciar (TypeError). Los cuerpos base solo contienen docstrings y no imponen el comportamiento concreto documentado.

```python
class IDefaultResponses(ABC):
```

```python
@abstractmethod
def favicon(self) -> FileResponse | Response:
```

`favicon`: significado de parámetros/retorno: `DefaultResponses.favicon`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
def robotsTxt(self) -> FileResponse | Response:
```

`robotsTxt`: significado de parámetros/retorno: `DefaultResponses.robotsTxt`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
def sitemapXml(self) -> FileResponse | Response:
```

`sitemapXml`: significado de parámetros/retorno: `DefaultResponses.sitemapXml`. Excepciones y efectos concretos dependen de la implementación.

```python
@abstractmethod
def health(self, request: Request) -> HTMLResponse | JSONResponse:
```

`health`: significado de parámetros/retorno: `DefaultResponses.health`. Excepciones y efectos concretos dependen de la implementación.

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

`error`: significado de parámetros/retorno: `DefaultResponses.error`. El contrato documenta códigos enteros entre 100 y 599, descripciones HTML escapadas, TypeError para estados no enteros y ValueError para estados fuera de rango. El cuerpo abstracto no valida ni renderiza; excepciones y efectos concretos dependen de la implementación.

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

`exception`: significado de parámetros/retorno: `DefaultResponses.exception`. Excepciones y efectos concretos dependen de la implementación.

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

Si wantsJson() o isAjax(), devuelve error JSON predeterminado 422 con exc.error(). En otro caso devuelve redirección 302 a previous_url, encola exc.errors y filtra/encola request.data() como entrada anterior. Solo silencia errores de lectura de datos al repoblar; propaga fallos de respuesta/normalización de errores. El middleware persiste en sesión.

| Parámetro | Tipo | Significado |
|---|---|---|
| `exc` | `ValidationException` | Excepción de validación de schemas que proporciona errores estructurados. |
| `request` | `Request` | Request actual. |
| `responses` | `IDefaultResponses` | Constructor de respuestas predeterminadas para errores de validación JSON. |

Tipo de retorno declarado: `Response`.

<a id="api-022"></a>

### previous_url

[validation.py](../validation.py)

```python
def previous_url(request: Request) -> str:
```

Devuelve session.getPreviousUrl() no vacío sin revalidar origen; en otro caso acepta Referer solo si es ruta absoluta de una barra o comparte esquema/host/puerto efectivo con baseUrl. Rechaza barras inversas, caracteres de control, referencias // y credenciales en referencias absolutas. Usa request.url como alternativa. Propaga fallos de sesión/cabeceras; el Referer inválido se considera no local.

| Parámetro | Tipo | Significado |
|---|---|---|
| `request` | `Request` | Request actual. |

Tipo de retorno declarado: `str`.

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

Declaración enum con valores exactos. Construir desde un valor no enumerado lanza ValueError. WebSocketStatus solo proporciona códigos; no implementa transporte WebSocket.

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

Declaración enum con valores exactos. Construir desde un valor no enumerado lanza ValueError. WebSocketStatus solo proporciona códigos; no implementa transporte WebSocket.

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

Declaración enum con valores exactos. Construir desde un valor no enumerado lanza ValueError. WebSocketStatus solo proporciona códigos; no implementa transporte WebSocket.

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

Subclase declarativa de Schema; sin constructor ni métodos propios. Los tipos, restricciones, valores predeterminados y mensajes se copian arriba. orionis.schemas proporciona la validación. LoginSchema.remember es str nullable; RegisterSchema.Unique consulta users.email y por ello depende de configuración de base de datos.

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

Subclase declarativa de Schema; sin constructor ni métodos propios. Los tipos, restricciones, valores predeterminados y mensajes se copian arriba. orionis.schemas proporciona la validación. LoginSchema.remember es str nullable; RegisterSchema.Unique consulta users.email y por ello depende de configuración de base de datos.

<a id="api-028"></a>

### HttpResponse

[types.py](../types.py)

```python
type HttpResponse = Response
```

Alias de tipo Python de Response; no es otra implementación ni otro constructor de respuesta.

<a id="api-029"></a>

### `Router`

[router.py](../routes/router.py)

```python
class Router(IRouter):
```

Implementa `IRouter`; mantiene el registro mutable y crea constructores `FluentRoute`. Ni el constructor ni los métodos de registro ejecutan peticiones. Los métodos HTTP disponibles aquí son GET, POST, QUERY, PUT, DELETE y PATCH. Las acciones de controlador recibidas usan `parse_action`: una clase abstracta, suelta o en un par de controlador/método, lanza `TypeError` antes de modificar el registro de rutas.

**`__init__`**

```python
def __init__(
    self,
    app: IApplication,
) -> None:
```

`app: IApplication` aporta `routeHealthCheck`. Retorna `None`; guarda la aplicación, comienza con tipo `"web"` y registra de inmediato rutas GET para `/favicon.ico`, `/robots.txt`, `/sitemap.xml` y `app.routeHealthCheck` mediante `DefaultResponses`. Propaga los errores de registro de `FluentRoute`. Otro GET para una de las tres primeras rutas elimina el registro anterior solo si su ruta actual sigue siendo esa ruta; conserva la anterior si recibió un prefijo. La ruta de salud no tiene una regla especial equivalente.

**`_setKind`**

```python
def _setKind(self, kind: str) -> None:
```

Punto interno usado por el cargador: `kind: str` establece el contexto de los registros siguientes. Retorna `None` y modifica ese contexto; este método no valida el valor. `FluentRoute._kind` lo valida y normaliza al añadir una ruta.

**`auth`**

```python
def auth(
    self,
    login_controller: type | None = None,
    register_controller: type | None = None,
    forgot_password_controller: type | None = None,
) -> None:
```

Cada controlador es opcional y usa de forma independiente el controlador integrado correspondiente: acceso/cierre de sesión, registro/verificación de correo o recuperación/restablecimiento de contraseña. Retorna `None`. Registra GET/POST `/login`, GET/POST `/sign-up`, GET/POST `/forgot-password`, GET/POST `/reset-password` con `GuestMiddleware`, GET `/verify-email` y POST `/logout` con `AuthenticateSessionMiddleware`. Los nombres POST incluyen `login`, `register`, `forgot-password`, `password.update` y `logout`; el formulario de restablecimiento se llama `password.reset` y la verificación de correo `verify-email`. Lanza `ValueError` fuera del contexto web y propaga errores de importación y registro. Las llamadas repetidas crean conflictos detectados al compilar.

**`view`**

```python
def view(
    self,
    path: str,
    view: str,
) -> FluentRoute:
```

`path: str` se normaliza como ruta; `view: str` es el nombre de plantilla, guardado sin espacios de los extremos. Retorna el `FluentRoute` GET registrado. Lanza `ValueError` si `view` no es texto o está vacío, y `TypeError` si la ruta no es texto. Modifica el registro; no renderiza la plantilla.

**`post`**

```python
def post(
    self,
    path: str,
    action: RouteAction | None = None,
) -> FluentRoute:
```

`path: str` se normaliza; `action: RouteAction | None = None` se analiza de inmediato cuando no es `None`. Omitirla o pasar `None` registra un constructor incompleto; debe completarse con `.action(Controller, "method")` antes de exportar. Retorna el `FluentRoute` POST registrado y modifica el registro. Lanza `TypeError` si la ruta no es texto o una acción distinta de `None` no es admitida; los pares de controlador inválidos generan los `TypeError`/`ValueError` descritos en `parse_action`. Los registros ordinarios duplicados por método/ruta permanecen hasta que la compilación los rechaza.

**`query`**

```python
def query(
    self,
    path: str,
    action: RouteAction | None = None,
) -> FluentRoute:
```

`path: str` se normaliza; `action: RouteAction | None = None` se analiza de inmediato cuando no es `None`. Omitirla o pasar `None` registra un constructor incompleto; debe completarse con `.action(Controller, "method")` antes de exportar. Retorna el `FluentRoute` QUERY registrado y modifica el registro. Lanza `TypeError` si la ruta no es texto o una acción distinta de `None` no es admitida; los pares de controlador inválidos generan los `TypeError`/`ValueError` descritos en `parse_action`. Los registros ordinarios duplicados por método/ruta permanecen hasta que la compilación los rechaza.

**`get`**

```python
def get(
    self,
    path: str,
    action: RouteAction | None = None,
) -> FluentRoute:
```

`path: str` se normaliza; `action: RouteAction | None = None` se analiza de inmediato cuando no es `None`. Omitirla o pasar `None` registra un constructor incompleto; debe completarse con `.action(Controller, "method")` antes de exportar. Retorna el `FluentRoute` GET registrado y modifica el registro. Lanza `TypeError` si la ruta no es texto o una acción distinta de `None` no es admitida; los pares de controlador inválidos generan los `TypeError`/`ValueError` descritos en `parse_action`. Los registros ordinarios duplicados por método/ruta permanecen hasta que la compilación los rechaza.

**`put`**

```python
def put(
    self,
    path: str,
    action: RouteAction | None = None,
) -> FluentRoute:
```

`path: str` se normaliza; `action: RouteAction | None = None` se analiza de inmediato cuando no es `None`. Omitirla o pasar `None` registra un constructor incompleto; debe completarse con `.action(Controller, "method")` antes de exportar. Retorna el `FluentRoute` PUT registrado y modifica el registro. Lanza `TypeError` si la ruta no es texto o una acción distinta de `None` no es admitida; los pares de controlador inválidos generan los `TypeError`/`ValueError` descritos en `parse_action`. Los registros ordinarios duplicados por método/ruta permanecen hasta que la compilación los rechaza.

**`delete`**

```python
def delete(
    self,
    path: str,
    action: RouteAction | None = None,
) -> FluentRoute:
```

`path: str` se normaliza; `action: RouteAction | None = None` se analiza de inmediato cuando no es `None`. Omitirla o pasar `None` registra un constructor incompleto; debe completarse con `.action(Controller, "method")` antes de exportar. Retorna el `FluentRoute` DELETE registrado y modifica el registro. Lanza `TypeError` si la ruta no es texto o una acción distinta de `None` no es admitida; los pares de controlador inválidos generan los `TypeError`/`ValueError` descritos en `parse_action`. Los registros ordinarios duplicados por método/ruta permanecen hasta que la compilación los rechaza.

**`patch`**

```python
def patch(
    self,
    path: str,
    action: RouteAction | None = None,
) -> FluentRoute:
```

`path: str` se normaliza; `action: RouteAction | None = None` se analiza de inmediato cuando no es `None`. Omitirla o pasar `None` registra un constructor incompleto; debe completarse con `.action(Controller, "method")` antes de exportar. Retorna el `FluentRoute` PATCH registrado y modifica el registro. Lanza `TypeError` si la ruta no es texto o una acción distinta de `None` no es admitida; los pares de controlador inválidos generan los `TypeError`/`ValueError` descritos en `parse_action`. Los registros ordinarios duplicados por método/ruta permanecen hasta que la compilación los rechaza.

**`fallback`**

```python
def fallback(
    self,
    action: RouteAction,
) -> None:
```

`action: RouteAction` es obligatorio y se analiza de inmediato; retorna `None` y guarda una tupla de fallback, sin un constructor encadenable. Las funciones quedan como `(None, function)`, las clases invocables como `(Class, "__call__")` y los pares de controlador como `(Class, method)`. Omitir el argumento lanza `TypeError`; el análisis rechaza `None` explícito. Lanza `FallbackRouteAlreadyRegisteredException` si ya existe un fallback, antes de analizar la acción recibida; propaga los demás errores de análisis.

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

Parámetros solo por nombre: `prefix: str | None` se normaliza y antepone; `middleware: MiddlewareInput | None` se antepone a cada pila; `without_middleware: MiddlewareInput | None` agrega exclusiones; `routes: Sequence[FluentRoute | RouteGroup] | None` se aplana a rutas hoja únicas. Retorna `RouteGroup`. Lanza `TypeError` si la colección no es una secuencia, si es texto/bytes o tiene miembros inválidos; `ValueError` si está vacía, repite IDs, el prefijo no es texto o hay middleware inválido. Valida antes de modificar el grupo. Las expresiones internas de registro ya registraron sus rutas. Modifica los mismos objetos ruta, incluidos miembros creados externamente, y los incorpora a este router. Los padres anidados preceden al middleware descendiente; el compilador resuelve las exclusiones.

**`export`**

```python
def export(self) -> dict:
```

Sin parámetros; retorna `dict` con `routes: list[dict]` y `fallback: tuple`. Crea un diccionario/lista exterior nuevo, pero cada exportación conserva referencias a su lista de middleware y conjunto de exclusiones. El fallback sin registrar es `(None, None)`. Propaga `ValueError` si alguna ruta sigue sin acción ni plantilla; el mensaje identifica su método y ruta actual. Sin E/S.

<a id="api-030"></a>

### `FluentRoute`

[fluent.py](../routes/fluent.py)

```python
class FluentRoute(IFluentRoute):
```

Constructor mutable de rutas que implementa `IFluentRoute`. Los métodos encadenables retornan la misma instancia (`Self`). El ID generado no cambia al añadir prefijos a la ruta; `_ALLOWED_METHODS` contiene `{"GET", "POST", "PUT", "DELETE", "PATCH", "QUERY"}`.

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

`method: str` pasa a mayúsculas y se valida contra los métodos admitidos; `path: str` se normaliza. `action: RouteAction | None` proporciona la función/controlador, o deja la ruta incompleta si se omite o vale `None`. `view: str | None`, solo por nombre, omite el análisis de la acción y guarda la plantilla sin espacios extremos. Retorna `None`, crea un ID e inicializa nombre/middleware vacíos con tipo `"web"`. Lanza `TypeError` por método/ruta no textual o acción inválida; `ValueError` por método no admitido, plantilla vacía/no textual o par de controlador inválido. Sin plantilla, la ruta incompleta debe recibir `.action(controller, handler)` antes de `export()`; en otro caso, este lanza `ValueError` con el método y la ruta actual. El ID se asigna antes de validar acción/plantilla.

**`path`**

```python
@property
def path(self) -> str:
```

Propiedad de lectura sin parámetros. Retorna la ruta canónica actual (`str`), incluidos los prefijos heredados. Sin mutación ni excepciones explícitas.

**`id`**

```python
@property
def id(self) -> str:
```

Propiedad de lectura sin parámetros. Retorna el identificador original de la ruta (`str`). Sin mutación ni excepciones explícitas.

**`action`**

```python
def action(self, controller: type, handler: str) -> Self:
```

`controller: type` y `handler: str` se validan como `[controller, handler]` mediante `parse_action`; retorna `Self`. Completa una ruta incompleta o reemplaza su clase/método, borrando la función independiente y la plantilla. Un controlador abstracto lanza `TypeError` antes de consultar el método; una subclase concreta puede usar un método invocable heredado. Propaga `TypeError`/`ValueError` de análisis antes de modificar el estado.

**`name`**

```python
def name(self, name: str) -> Self:
```

`name: str` se guarda sin espacios extremos; retorna `Self`. Lanza `TypeError` si no es texto y `ValueError` si queda vacío. Solo el compilador verifica que un nombre no apunte a rutas distintas.

**`middleware`**

```python
def middleware(
    self,
    *middleware: MiddlewareInput,
) -> Self:
```

`*middleware: MiddlewareInput` acepta clases o secuencias/conjuntos de un nivel; retorna `Self` y añade las entradas validadas y aplanadas sin eliminar duplicados. Una entrada inválida lanza `TypeError` antes de extender la lista. Los conjuntos se ordenan por módulo/nombre cualificado.

**`withOutMiddleware`**

```python
def withOutMiddleware(
    self,
    *middleware: MiddlewareInput,
) -> Self:
```

`*middleware: MiddlewareInput` usa la misma validación/aplanado; retorna `Self` y actualiza el conjunto de exclusiones. Una entrada inválida lanza `TypeError` antes de modificarlo. La escritura exacta es `withOutMiddleware`.

**`prefix`**

```python
def prefix(self, prefix: str) -> Self:
```

`prefix: str` se normaliza y antepone a la ruta actual; retorna `Self`. Lanza `TypeError` si no es texto. Las rutas raíz evitan una barra final adicional. Cambia la ruta sin regenerar el ID.

**`inheritGroup`**

```python
def inheritGroup(
    self,
    prefix: str,
    middleware: tuple[type[BaseMiddleware], ...],
    without_middleware: frozenset[type[BaseMiddleware]],
) -> Self:
```

`prefix: str` debe llegar canónico sin barra final; `middleware: tuple[type[BaseMiddleware], ...]` se antepone; `without_middleware: frozenset[type[BaseMiddleware]]` se combina. Retorna `Self` y modifica el constructor. Este auxiliar público confía en la validación del llamador/`Router.group`; no añade validaciones ni excepciones explícitas.

**`_kind`**

```python
def _kind(self, kind: str) -> Self:
```

Punto interno de registro: `kind: str` se guarda sin espacios extremos y en minúsculas; retorna `Self`. Lanza `TypeError` si no es texto; no limita el resultado a `web`/`api`.

**`export`**

```python
def export(self) -> dict:
```

Sin parámetros; retorna un `dict` nuevo con `id`, `method`, `path`, `class`, `handler`, `callable_handler`, `view`, `name`, `middleware`, `without_middleware`, `kind`. Middleware y exclusiones son contenedores mutables compartidos, no copias. Lanza `ValueError` si no se asignó acción ni plantilla; el mensaje contiene el método y la ruta actual y solicita `.action(controller, handler)` antes de exportar. Sin E/S.

<a id="api-031"></a>

### `RouteGroup`

[group.py](../routes/group.py)

```python
@dataclass(frozen=True, slots=True)
class RouteGroup:
```

`@dataclass(frozen=True, slots=True)` guarda `routes: tuple[FluentRoute, ...]`, los miembros aplanados producidos por `Router.group`. El constructor generado recibe ese campo; la fuente no define un `__init__` explícito. Congelar impide reasignar campos, pero los constructores de ruta contenidos siguen siendo mutables. Sin validación, excepciones propias ni E/S; asignar campos congelados lanza `dataclasses.FrozenInstanceError`.

```python
routes: tuple[FluentRoute, ...]
```

<a id="api-032"></a>

### `RouteID`

[route_id.py](../routes/route_id.py)

```python
class RouteID:
```

Clase sin estado con `__slots__ = ()`. Las variables del módulo conservan el ID de proceso y `time.time_ns`, junto a un contador `itertools.count(1)`.

**`next`**

```python
@staticmethod
def next(method: str, path: str) -> str:
```

`method: str` y `path: str` se interpolan sin validación. Retorna `str` con formato `method:path:pid:time_ns:counter`; lee el reloj e incrementa el contador local del proceso. Sin excepciones explícitas. El código no contiene locks ni garantía explícita de unicidad entre procesos/hilos.

<a id="api-033"></a>

### `RouteCompiler`

[route_compiler.py](../routes/route_compiler.py)

```python
class RouteCompiler(IRouteCompiler):
```

Implementación de `IRouteCompiler` que convierte las rutas exportadas en mapas estáticos y listas dinámicas ordenadas por método. No define constructor explícito ni estado de instancia.

**`compile`**

```python
def compile(
    self,
    routes: list[dict],
    fallback: tuple | None,
    app_middleware: list[type] | None = None,
) -> tuple[dict[str, dict], tuple | None]:
```

`routes: list[dict]` es la exportación del router; `fallback: tuple | None` se devuelve sin modificar; `app_middleware: list[type] | None` aporta la pila global. Retorna `(dict[str, dict], tuple | None)` con cada método asociado a `{"static": {path: CompiledRoute}, "dynamic": [CompiledRoute, ...]}`. El middleware global precede al de ruta, las exclusiones afectan a ambos y la identidad de clase elimina duplicados conservando la primera aparición. Las rutas dinámicas se ordenan de forma estable por `static_segments * 10 - dynamic_segments` descendente. `ValueError`: método/ruta estático repetido; regex dinámicas estructuralmente iguales para el mismo método; un nombre para plantillas de ruta distintas; parámetros mal formados/duplicados/desconocidos; nombres cualificados del manejador con `<locals>`. La validación de acciones también lanza `TypeError`/`ValueError`. Las claves obligatorias ausentes propagan `KeyError`. Sin E/S ni modificación de los contenedores de entrada; las dataclasses creadas reciben copias de middleware/exclusiones.

**`compilePath`**

```python
@staticmethod
def compilePath(
    path: str,
) -> tuple[bool, re.Pattern | None, dict[str, Callable]]:
```

`path: str` es una plantilla de ruta; retorna `(is_static: bool, regex: re.Pattern | None, converters: dict[str, Callable])`. Una ruta estática devuelve `(True, None, {})`. `{name}` usa `str` por defecto; `{name:type}` consulta `PARAM_TYPES`, escapa los fragmentos literales y ancla la regex con `^`/`$`. Lanza `ValueError` por llaves desbalanceadas/mal formadas, identificadores inválidos/repetidos o tipos desconocidos; puede propagar errores de regex si se modifican los patrones de conversión. No normaliza la ruta ni modifica estado externo.

<a id="api-034"></a>

### `RouteCache`

[route_cache.py](../routes/route_cache.py)

```python
class RouteCache(IRouteCache):
```

Implementa `IRouteCache`; `VERSION = 2`. Serializa metadatos en diccionarios; la persistencia en archivos corresponde a `RouteLoader`. Omite regex y funciones conversoras del caché y las reconstruye desde cada ruta.

**`toCache`**

```python
def toCache(
    self,
    routes: dict[str, dict],
    fallback: tuple | None,
) -> dict:
```

`routes: dict[str, dict]` es la salida del compilador; `fallback: tuple | None` es el fallback original. Retorna un `dict` con `version`, `fallback` y `routes` agrupadas por método. Guarda valores del enum, descriptores de acción, métricas, tipo y nombres importables del middleware; sin E/S de archivos. `None`/`(None, None)` se convierte en fallback `None`. Las estructuras inválidas pueden propagar `KeyError`, `AttributeError` o errores de desempaquetado; no valida un esquema explícito. Los diccionarios `action` se conservan por referencia.

**`fromCache`**

```python
def fromCache(
    self,
    cached: dict,
) -> tuple[dict[str, dict], tuple | None]:
```

`cached: dict` aporta los metadatos serializados. Retorna `(routes: dict[str, dict], fallback: tuple | None)`, recompila las rutas e importa clases de middleware y objetos fallback. Memoriza las clases de middleware resueltas durante esta llamada. No verifica `version`; lo hace el cargador. Lanza/propaga `ValueError` por `RouteType` inválido, rutas inválidas o nombre cualificado de función fallback con `<locals>`; esquemas incorrectos pueden lanzar `KeyError`/`TypeError`, y los imports/atributos ausentes propagan sus errores. Ejecutar imports es un efecto secundario; aquí no hay E/S de archivos.

<a id="api-035"></a>

### `RouteLoader`

[loader.py](../routes/loader.py)

```python
class RouteLoader(IRouteLoader):
```

Implementación de `IRouteLoader` con carga diferida una vez por instancia. El flujo privado es consulta del caché → importación de rutas en orden `("web", "api")` → compilación → normalización del fallback ausente → persistencia opcional. Un `finally` restaura el tipo del router a `"web"`, incluso si falla un import. `__loaded` solo se activa tras restaurar el caché o completar compilación/persistencia.

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

`app: IApplication` aporta middleware, rutas y configuración de compilación; `router: IRouter` guarda registros; `compiler: RouteCompiler` construye rutas; `cache: RouteCache` las serializa. Retorna `None`, captura `app.getMiddleware()` y, si `app.compiled` es verdadero, crea `FileBasedCache(path=app.compiledPath, filename="routes", monitored_dirs=app.compiledInvalidationPathsDirs, monitored_files=app.compiledInvalidationPathsFiles)`. Propaga errores de configuración/colaboradores y construcción del caché; todavía no carga módulos de rutas.

**`load`**

```python
def load(self) -> dict[str, dict]:
```

Sin parámetros; retorna directamente el `dict[str, dict]` almacenado. En el primer acceso lee el caché persistente habilitado y solo acepta un diccionario no vacío con versión `RouteCache.VERSION`; en otro caso importa archivos de rutas relativos a `app.path("root")`, compila, normaliza el fallback ausente a `None` y guarda si la persistencia está habilitada. Tras compilar y antes de persistir, `case (None, None)` reconoce el centinela del router mediante comprobaciones de identidad con `None`, sin invocar métodos de igualdad de los manejadores; las tuplas de fallback válidas se conservan. Los imports ejecutan efectos de registro y el caché delega E/S de archivos. `Path.relative_to` puede lanzar `ValueError`; exportar también lanza `ValueError` para rutas incompletas. Propaga errores de importación, compilación, caché y persistencia. Tras el primer éxito reutiliza el mismo diccionario, incluso si está vacío.

**`fallback`**

```python
@property
def fallback(self) -> tuple | None:
```

Propiedad de lectura sin parámetros. Activa la misma carga y retorna `tuple | None`: `(Class, method_name)` para fallbacks de controlador, `(None, callable)` para fallbacks de función o `None` si no hay uno registrado. El fallback ausente es `None` con caché deshabilitado, tras compilar por falta de entrada en caché y tras restaurar el caché. `Router.export()` sigue produciendo el centinela original `(None, None)` y `RouteCompiler.compile()` lo devuelve sin modificar; el cargador lo normaliza antes de exponerlo y persistirlo. Comparte efectos secundarios y excepciones con `load()`.

<a id="api-036"></a>

### `RouteResolver`

[route_resolver.py](../routes/route_resolver.py)

```python
class RouteResolver(IRouteResolver):
```

Implementación de `IRouteResolver` con `__slots__`. Crea búsquedas estáticas y tablas dinámicas por profundidad; los grupos grandes también pueden dividirse por prefijos literales conservando el orden de prioridad. Comparte resultados dinámicos exitosos en un caché FIFO limitado. La búsqueda no ejecuta manejadores del usuario.

**`__init__`**

```python
def __init__(
    self,
    routes: dict[str, dict],
    hot_cache_size: int = 512,
    fallback: tuple | None = None,
) -> None:
```

`routes: dict[str, dict]` aporta datos compilados por método/estáticas/dinámicas; `hot_cache_size: int = 512` limita las entradas dinámicas exitosas (`0` desactiva el caché); `fallback: tuple | None` se guarda normalizando `(None, None)` a `None`. Retorna `None` y construye tablas, objetos `ResolvedRoute` estáticos y una tupla de rutas sin duplicados por identidad de objeto. Lanza `TypeError` si la capacidad no es `int`, incluido `bool`, y `ValueError` si es negativa; datos compilados inválidos pueden propagar errores estructurales/de regex. Sin E/S.

**`resolve`**

```python
def resolve(self, method: str, path: str) -> ResolvedRoute:
```

`method: str` pasa a mayúsculas cuando hace falta y `HEAD` usa `GET`; `path: str` pasa por `normalize_request_path`. Retorna `ResolvedRoute` con parámetros convertidos y de solo lectura; las coincidencias estáticas preceden a las dinámicas. Una búsqueda dinámica exitosa modifica el caché FIFO; los aciertos no renuevan el orden de expulsión. Lanza `MethodNotAllowed(path)` si la ruta normalizada coincide con otro método (o con cualquier ruta estática); en otro caso, `RouteNotFound(path)`. Un `ValueError`/`OverflowError` del conversor equivale a una coincidencia dinámica fallida; otros errores se propagan. La revisión de otros métodos prueba regex sin conversión. No ejecuta ni devuelve automáticamente el fallback.

**`options`**

```python
def options(self, path: str) -> list[str]:
```

`path: str` se normaliza; retorna `list[str]` ordenada con los métodos cuya tabla estática o regex dinámica coincide, más `HEAD` implícito para GET y `OPTIONS` si hay coincidencia. Si no coincide ninguna ruta pero hay fallback, retorna `["GET", "HEAD", "OPTIONS"]`; en otro caso, `[]`. No convierte parámetros ni modifica el caché. Sin excepciones explícitas para entradas válidas.

**`fallback`**

```python
def fallback(self) -> tuple | None:
```

Sin parámetros; retorna el fallback `tuple | None` guardado, sin ejecutarlo. Sin mutación ni excepciones explícitas.

**`allRoutes`**

```python
def allRoutes(self) -> list[CompiledRoute]:
```

Sin parámetros; retorna una `list[CompiledRoute]` nueva en el orden de recorrido de tablas por método, con cada objeto ruta original una vez por identidad. Sin mutación ni excepciones explícitas.

**`invalidateCache`**

```python
def invalidateCache(self) -> None:
```

Sin parámetros; retorna `None` y vacía el diccionario de resultados dinámicos y la cola FIFO. Las tablas estáticas y descriptores de ruta siguen disponibles. Sin excepciones explícitas.

<a id="api-037"></a>

### `RouterProvider`

[provider.py](../routes/provider.py)

```python
class RouterProvider(ServiceProvider):
```

Hereda `ServiceProvider`; integra el router con el contenedor y `orionis.support.facades.router.Route`. Este archivo no declara constructor.

**`register`**

```python
def register(self) -> None:
```

Sin parámetros; retorna `None`. Registra `IRouter` con implementación `Router` como singleton bajo el alias `"x-orionis-IRouter"` llamando a `self.app.singleton(IRouter, Router, alias="x-orionis-IRouter")` y modifica los registros del contenedor. Propaga errores del contenedor; sin excepciones locales explícitas.

**`boot`**

```python
async def boot(self) -> None:
```

Método asíncrono sin parámetros; al esperarlo retorna `None` tras `await RouteFacade.pin()`. Inicializa estado compartido de la fachada y propaga sus errores. El método no añade sincronización local.

<a id="api-038"></a>

### `CompiledRoute`

[entities/compiled_route.py](../routes/entities/compiled_route.py)

```python
@dataclass(slots=True, frozen=True)
class CompiledRoute:
```

Dataclass congelada y con slots; su constructor generado recibe los campos siguientes en orden (el archivo no contiene una firma de constructor explícita). Son obligatorios `path`, `method`, `type`, `action`, `name`, `regex`, `segment_count`. `path: str` es la plantilla; `method: str`, el método; `type: RouteType` elige el despacho; `action: dict` contiene `view`, o `module` más `function`, o `module`/`class`/`method`; `name: str | None` es el nombre para URL; `regex: Pattern | None` está ausente en rutas estáticas. `segment_count: int` acota la búsqueda dinámica; `priority_score: int` ordena la especificidad; `kind: str` conserva el tipo de pipeline. `converters: dict[str, Callable]` convierte parámetros; `middleware: list` y `without_middleware: set` conservan las declaraciones; `compiled_middlewares: tuple` fija el orden final. Las fábricas predeterminadas crean contenedores nuevos. La congelación es superficial: diccionarios, listas y conjuntos internos siguen siendo mutables. Sin validación propia ni E/S; reasignar campos produce el error estándar de dataclasses congeladas.

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

Dataclass congelada y con slots; el constructor generado recibe `route: CompiledRoute` (descriptor encontrado) y `params: Mapping[str, Any]` (parámetros convertidos). La fuente no contiene una firma explícita de constructor. Conserva la referencia a la ruta y hace de solo lectura la estructura de parámetros, sin copiar sus valores en profundidad.

```python
route: CompiledRoute
params: Mapping[str, Any]
```

**`__post_init__`**

```python
def __post_init__(self) -> None:
```

Punto invocado por el constructor generado, sin parámetros; retorna `None`. Copia el mapping no vacío mediante `dict` y lo envuelve en `MappingProxyType`; usa un proxy vacío compartido para mappings vacíos. Una entrada inválida puede propagar `TypeError`/`ValueError`. Modificar el mapping resultante lanza `TypeError`; reasignar campos congelados genera el error de dataclasses.

**`_fromOwnedParams`**

```python
@classmethod
def _fromOwnedParams(
    cls,
    route: CompiledRoute,
    params: dict[str, Any],
) -> ResolvedRoute:
```

Método de clase interno: `route: CompiledRoute` es el descriptor; `params: dict[str, Any]` transfiere un diccionario de propiedad exclusiva. Retorna `ResolvedRoute` sin copiarlo ni invocar el constructor normal. El resolver debe descartar referencias mutables; conservarlas y modificarlas cambia el contenido del proxy. Sin validación explícita ni E/S.

**`kind`**

```python
@property
def kind(self) -> str:
```

Propiedad de lectura sin parámetros. Retorna `str` directamente desde `route.kind`; no impone la restricción del docstring a `web` o `api`. Sin mutación ni excepciones explícitas.

<a id="api-040"></a>

### `RouteType`

[enums/route_types.py](../routes/enums/route_types.py)

```python
class RouteType(StrEnum):
```

Discriminante de despacho `StrEnum` con los miembros exactos siguientes. La construcción estándar con un valor desconocido lanza `ValueError`; no hay métodos propios ni efectos secundarios.

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

Subclase simple de `Exception` lanzada por `Router.fallback` si ya existe un fallback.

No declara constructor, campos, métodos ni retorno locales. Tipos/validación de argumentos propios:

> ⚠️ No especificado en el código fuente

<a id="api-042"></a>

### `MethodNotAllowed`

[exceptions/method_not_allowed.py](../routes/exceptions/method_not_allowed.py)

```python
class MethodNotAllowed(Exception):
```

Subclase simple de `Exception` lanzada por `RouteResolver.resolve` si la ruta existe para otro método. Recibe la ruta como argumento de excepción; esta clase no construye una respuesta HTTP.

No declara constructor, campos, métodos ni retorno locales. Tipos/validación de argumentos propios:

> ⚠️ No especificado en el código fuente

<a id="api-043"></a>

### `RouteNotFound`

[exceptions/route_not_found.py](../routes/exceptions/route_not_found.py)

```python
class RouteNotFound(Exception):
```

Subclase simple de `Exception` lanzada al fallar la resolución. `resolve` recibe la ruta como argumento; el extractor privado de regex combinadas puede usar un mensaje de error de invariantes.

No declara constructor, campos, métodos ni retorno locales. Tipos/validación de argumentos propios:

> ⚠️ No especificado en el código fuente

<a id="api-044"></a>

### `normalize_path`

[functions.py](../routes/functions.py)

```python
def normalize_path(path: str) -> str:
```

`path: str` pierde espacios extremos, colapsa barras consecutivas, recibe barra inicial y pierde barras finales salvo en la raíz. Retorna `str` canónico; una entrada vacía o de espacios produce `/`. No modifica estado externo ni valida tipos explícitamente; entradas no textuales pueden propagar `AttributeError`/`TypeError` de operaciones de texto/regex.

<a id="api-045"></a>

### `normalize_request_path`

[functions.py](../routes/functions.py)

```python
def normalize_request_path(path: str) -> str:
```

`path: str` recibe barra inicial si falta y pierde barras finales salvo en la raíz; la entrada vacía produce `/`. Retorna `str`. A diferencia de la normalización de registro, conserva espacios y barras internas repetidas. Sin mutación externa ni validación explícita de tipos; las entradas inválidas pueden propagar errores de indexación/operaciones de texto.

<a id="api-046"></a>

### `strip_regex_anchors`

[functions.py](../routes/functions.py)

```python
def strip_regex_anchors(pattern: str) -> str:
```

`pattern: str` se procesa como texto: elimina como máximo un `^` inicial y un `$` final. Retorna `str`; no analiza regex ni modifica estado externo, y no lanza excepciones explícitas con texto válido. Un dólar final escapado también se trata como carácter final.

<a id="api-047"></a>

### `flatten_middleware`

[functions.py](../routes/functions.py)

```python
def flatten_middleware(
    *middleware: MiddlewareInput,
) -> list[type[BaseMiddleware]]:
```

`*middleware: MiddlewareInput` acepta subclases de `BaseMiddleware` directamente o dentro de `Sequence`/`Set` abstracto, aplanando un nivel. Retorna una `list[type[BaseMiddleware]]` nueva; conserva el orden de secuencias y ordena cada conjunto por `(class.__module__, class.__qualname__)`. No elimina duplicados. Lanza `TypeError` si algún miembro no es una subclase de `BaseMiddleware`; rechaza contenedores anidados e instancias. No modifica los contenedores recibidos ni hace E/S.

<a id="api-048"></a>

### `is_valid_handler`

[functions.py](../routes/functions.py)

```python
def is_valid_handler(action: object) -> bool:
```

`action: object` se comprueba llamando a `parse_action(action)`. Retorna `True` si el análisis tiene éxito y `False` si lanza `TypeError` o `ValueError`. Por tanto, las funciones Python admitidas (incluidas las funciones coroutine), las clases de controlador concretas e invocables y los pares válidos de controlador concreto/método retornan `True`; los controladores abstractos en cualquiera de las dos formas, las instancias invocables, los métodos ligados, los builtins, los objetos `functools.partial`, los objetos coroutine, las lambdas y `None` retornan `False`.

Es una validación estructural; no garantiza que la acción se pueda importar ni que sus dependencias se puedan resolver. No instancia controladores ni invoca manejadores por sí misma. Consultar atributos del controlador puede ejecutar descriptores con efectos secundarios; las excepciones distintas de `TypeError` y `ValueError` se propagan.

<a id="api-049"></a>

### `parse_action`

[functions.py](../routes/functions.py)

```python
def parse_action( # NOSONAR
    action: object,
) -> tuple[Callable, None] | tuple[type, str]:
```

`action: object` admite una clase concreta invocable que defina/herede `__call__`, una función Python no lambda (incluido `async def`) o una lista/tupla de dos elementos `(concrete_class, method_name)`. Una subclase concreta puede usar un método invocable heredado. Retorna `(callable_or_class, None)` o `(class, str)` según la anotación. Comprueba las funciones Python directamente con `inspect.isfunction`, `callable`, la exclusión de objetos coroutine y la comprobación del nombre no lambda; el parser no llama a `is_valid_handler`.

Lanza `TypeError` por clases de controlador abstractas en cualquiera de las dos formas, clases sueltas no invocables, tipos incorrectos en el par, instancias invocables, métodos ligados, builtins, objetos `functools.partial`, objetos coroutine, lambdas, `None` u otras formas no admitidas; `ValueError` si el par no tiene dos elementos o el método falta/no es invocable. Una clase abstracta en un par se rechaza antes de consultar el método con `TypeError("First element of action list must be a concrete class")`. El error de forma no admitida enumera las formas válidas y excluye explícitamente instancias invocables y métodos ligados.

El registro ordinario de rutas, `FluentRoute.action` y `Router.fallback` usan este parser; `RouteCompiler.compile` también lo aplica a las declaraciones originales de manejadores/controladores de ruta. La validación es estructural y no garantiza que la acción se pueda importar ni que sus dependencias se puedan resolver. No instancia controladores ni invoca manejadores; consultar el atributo del par puede ejecutar descriptores con efectos secundarios, y sus excepciones se propagan.

<a id="api-050"></a>

### `RouteAction`

[types.py](../routes/types.py)

```python
type RouteAction = Callable | type | list[type | str] | tuple[type, str]
```

Alias público de tipos para registrar acciones. Conserva `Callable` por compatibilidad de tipado, representando aquí funciones Python; la aceptación en ejecución es más limitada. `parse_action` rechaza instancias invocables, métodos ligados, builtins y lambdas, como explica el comentario de la fuente. `is_valid_handler` permite comprobar la aceptación estructural del parser. El alias no aplica validación ni efectos secundarios.

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

Alias público para una clase de middleware o secuencia/conjunto de clases. `flatten_middleware` valida durante la ejecución y ordena los conjuntos de forma determinista.

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

Registro mutable de conversores usado por `RouteCompiler.compilePath`. `str` acepta uno o más caracteres distintos de barra; `slug`, letras ASCII minúsculas/dígitos/guiones; `int` usa `\d+` y convierte con `int`; `uuid` usa la forma hexadecimal canónica indicada y convierte con `uuid.UUID`. No declara segmentos opcionales, patrón de enteros negativos ni tipo que capture una ruta completa. Restaurar el caché consulta nuevamente el registro actual.

<a id="api-053"></a>

### `ParamConverter`

[route_resolver.py](../routes/route_resolver.py)

```python
ParamConverter = Callable[[str], object]
```

Función conversora: entrada `str`, salida `object`; los errores se propagan salvo `ValueError`/`OverflowError`, tratados por el resolver como coincidencias fallidas.

<a id="api-054"></a>

### `Extractor`

[route_resolver.py](../routes/route_resolver.py)

```python
Extractor = tuple[str, int, ParamConverter]
```

Tupla `(parameter_name: str, capture_group_index: int, converter: ParamConverter)` usada para extraer parámetros tipados.

<a id="api-055"></a>

### `BucketEntry`

[route_resolver.py](../routes/route_resolver.py)

```python
BucketEntry = tuple[list[Extractor], "CompiledRoute"]
```

Asocia una lista de descriptores de extracción con una ruta compilada. Lo usan los buckets privados de coincidencia dinámica.

<a id="api-056"></a>

### `DepthTable`

[route_resolver.py](../routes/route_resolver.py)

```python
type DepthTable = dict[int, _DepthBucket | _PrefixIndex]
```

Asocia profundidad de segmentos (`int`) a una regex combinada privada `_DepthBucket` o estructura de ramas `_PrefixIndex`. No define una función pública para construir/validar estos elementos internos.

<a id="api-057"></a>

### `IRouter`

[contracts/router.py](../routes/contracts/router.py)

```python
class IRouter(ABC):
```

Clase base abstracta (`ABC`). Cada declaración siguiente usa `@abstractmethod`; las subclases incompletas no pueden instanciarse (`TypeError`). Los cuerpos solo contienen documentación y no implementan validación, E/S ni cambios de estado. `Router` proporciona el comportamiento concreto documentado por separado. Excepciones o efectos adicionales de implementaciones de terceros:

> ⚠️ No especificado en el código fuente

**`auth`**

```python
@abstractmethod
def auth(
    self,
    login_controller: type | None = None,
    register_controller: type | None = None,
    forgot_password_controller: type | None = None,
) -> None:
```

Los controladores opcionales permiten sustituir, de manera independiente, los controladores de acceso/cierre de sesión, registro/verificación de correo y recuperación/restablecimiento de contraseña. Retorna `None` y documenta `ValueError` fuera del contexto web. El cuerpo abstracto no realiza operaciones; véase `Router.auth` para efectos y errores reales de la implementación.

**`view`**

```python
@abstractmethod
def view(
    self,
    path: str,
    view: str,
) -> FluentRoute:
```

`path: str` es la URL; `view: str`, la plantilla. Retorna el `FluentRoute` registrado. El cuerpo abstracto no realiza operaciones; véase `Router.view` para efectos y errores reales de la implementación.

**`post`**

```python
@abstractmethod
def post(
    self,
    path: str,
    action: RouteAction | None = None,
) -> FluentRoute:
```

`path: str` y `action: RouteAction | None` opcional registran una ruta POST; retorna `FluentRoute`. Si se omite la acción o vale `None`, debe asignarse mediante `.action(controller, handler)` antes de exportar. El cuerpo abstracto no realiza operaciones; véase `Router.post` para efectos y errores reales de la implementación.

**`query`**

```python
@abstractmethod
def query(
    self,
    path: str,
    action: RouteAction | None = None,
) -> FluentRoute:
```

`path: str` y `action: RouteAction | None` opcional registran una ruta QUERY; retorna `FluentRoute`. Si se omite la acción o vale `None`, debe asignarse mediante `.action(controller, handler)` antes de exportar. El cuerpo abstracto no realiza operaciones; véase `Router.query` para efectos y errores reales de la implementación.

**`get`**

```python
@abstractmethod
def get(
    self,
    path: str,
    action: RouteAction | None = None,
) -> FluentRoute:
```

`path: str` y `action: RouteAction | None` opcional registran una ruta GET; retorna `FluentRoute`. Si se omite la acción o vale `None`, debe asignarse mediante `.action(controller, handler)` antes de exportar. El cuerpo abstracto no realiza operaciones; véase `Router.get` para efectos y errores reales de la implementación.

**`put`**

```python
@abstractmethod
def put(
    self,
    path: str,
    action: RouteAction | None = None,
) -> FluentRoute:
```

`path: str` y `action: RouteAction | None` opcional registran una ruta PUT; retorna `FluentRoute`. Si se omite la acción o vale `None`, debe asignarse mediante `.action(controller, handler)` antes de exportar. El cuerpo abstracto no realiza operaciones; véase `Router.put` para efectos y errores reales de la implementación.

**`delete`**

```python
@abstractmethod
def delete(
    self,
    path: str,
    action: RouteAction | None = None,
) -> FluentRoute:
```

`path: str` y `action: RouteAction | None` opcional registran una ruta DELETE; retorna `FluentRoute`. Si se omite la acción o vale `None`, debe asignarse mediante `.action(controller, handler)` antes de exportar. El cuerpo abstracto no realiza operaciones; véase `Router.delete` para efectos y errores reales de la implementación.

**`patch`**

```python
@abstractmethod
def patch(
    self,
    path: str,
    action: RouteAction | None = None,
) -> FluentRoute:
```

`path: str` y `action: RouteAction | None` opcional registran una ruta PATCH; retorna `FluentRoute`. Si se omite la acción o vale `None`, debe asignarse mediante `.action(controller, handler)` antes de exportar. El cuerpo abstracto no realiza operaciones; véase `Router.patch` para efectos y errores reales de la implementación.

**`fallback`**

```python
@abstractmethod
def fallback(
    self,
    action: RouteAction,
) -> None:
```

`action: RouteAction` obligatorio aporta un fallback completo; retorna `None` sin encadenamiento. Documenta `FallbackRouteAlreadyRegisteredException` por registro repetido y `TypeError` para `None` o una forma de manejador no admitida. El cuerpo abstracto no realiza operaciones; véase `Router.fallback` para efectos y errores reales de la implementación.

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

`prefix: str | None`, `middleware: MiddlewareInput | None`, `without_middleware: MiddlewareInput | None` y `routes: Sequence[FluentRoute | RouteGroup] | None`, solo por nombre, describen contexto y miembros. Retorna `RouteGroup`; documenta `ValueError` por rutas vacías/prefijo o middleware inválidos y `TypeError` por miembros inválidos. El cuerpo abstracto no realiza operaciones; véase `Router.group` para efectos y errores reales de la implementación.

**`export`**

```python
@abstractmethod
def export(self) -> dict:
```

Sin parámetros; retorna `dict` con todas las rutas exportadas y el fallback. Documenta `ValueError` si una ruta incompleta carece de acción y plantilla. El cuerpo abstracto no realiza operaciones; véase `Router.export` para efectos y errores reales de la implementación.

<a id="api-058"></a>

### `IFluentRoute`

[contracts/fluent.py](../routes/contracts/fluent.py)

```python
class IFluentRoute(ABC):
```

Clase base abstracta (`ABC`). Cada declaración siguiente usa `@abstractmethod`; las subclases incompletas no pueden instanciarse (`TypeError`). Los cuerpos solo contienen documentación y no implementan validación, E/S ni cambios de estado. `FluentRoute` proporciona el comportamiento concreto documentado por separado. Excepciones o efectos adicionales de implementaciones de terceros:

> ⚠️ No especificado en el código fuente

**`id`**

```python
@property
@abstractmethod
def id(self) -> str:
```

Sin parámetros; propiedad de lectura que retorna el identificador `str` de la ruta. El cuerpo abstracto no realiza operaciones; véase `FluentRoute.id` para efectos y errores reales de la implementación.

**`action`**

```python
@abstractmethod
def action(self, controller: type, handler: str) -> Self:
```

`controller: type` y `handler: str` identifican clase y método; retorna `Self` para encadenar. El cuerpo abstracto no realiza operaciones; véase `FluentRoute.action` para efectos y errores reales de la implementación.

**`name`**

```python
@abstractmethod
def name(self, name: str) -> Self:
```

`name: str` proporciona el nombre de ruta; retorna `Self`. El cuerpo abstracto no realiza operaciones; véase `FluentRoute.name` para efectos y errores reales de la implementación.

**`middleware`**

```python
@abstractmethod
def middleware(
    self,
    *middleware: MiddlewareInput,
) -> Self:
```

`*middleware: MiddlewareInput` aporta clases o contenedores para añadir; retorna `Self`. El cuerpo abstracto no realiza operaciones; véase `FluentRoute.middleware` para efectos y errores reales de la implementación.

**`withOutMiddleware`**

```python
@abstractmethod
def withOutMiddleware(
    self,
    *middleware: MiddlewareInput,
) -> Self:
```

`*middleware: MiddlewareInput` aporta clases o contenedores para excluir; retorna `Self`. El cuerpo abstracto no realiza operaciones; véase `FluentRoute.withOutMiddleware` para efectos y errores reales de la implementación.

**`prefix`**

```python
@abstractmethod
def prefix(self, prefix: str) -> Self:
```

`prefix: str` aporta el prefijo de ruta; retorna `Self`. El cuerpo abstracto no realiza operaciones; véase `FluentRoute.prefix` para efectos y errores reales de la implementación.

**`export`**

```python
@abstractmethod
def export(self) -> dict:
```

Sin parámetros; retorna `dict` con la configuración completa de la ruta encadenable. Documenta `ValueError` si no tiene acción ni plantilla. El cuerpo abstracto no realiza operaciones; véase `FluentRoute.export` para efectos y errores reales de la implementación.

<a id="api-059"></a>

### `IRouteLoader`

[contracts/loader.py](../routes/contracts/loader.py)

```python
class IRouteLoader(ABC):
```

Clase base abstracta (`ABC`). Cada declaración siguiente usa `@abstractmethod`; las subclases incompletas no pueden instanciarse (`TypeError`). Los cuerpos solo contienen documentación y no implementan validación, E/S ni cambios de estado. `RouteLoader` proporciona el comportamiento concreto documentado por separado. Excepciones o efectos adicionales de implementaciones de terceros:

> ⚠️ No especificado en el código fuente

**`load`**

```python
@abstractmethod
def load(self) -> dict[str, dict]:
```

Sin parámetros; retorna `dict[str, dict]` compilado con grupos `static` y `dynamic` por método. El cuerpo abstracto no realiza operaciones; véase `RouteLoader.load` para efectos y errores reales de la implementación.

**`fallback`**

```python
@property
@abstractmethod
def fallback(self) -> tuple | None:
```

Propiedad de lectura sin parámetros; su acceso documentado activa la carga. Retorna `(Class, method_name)` para fallbacks de controlador, `(None, callable)` para fallbacks de función o `None` si no hay uno registrado, tanto al compilar bajo demanda como al restaurar el caché. El cuerpo abstracto no realiza operaciones; véase `RouteLoader.fallback` para efectos y errores reales de la implementación.

<a id="api-060"></a>

### `IRouteCompiler`

[contracts/route_compiler.py](../routes/contracts/route_compiler.py)

```python
class IRouteCompiler(ABC):
```

Clase base abstracta (`ABC`). Cada declaración siguiente usa `@abstractmethod`; las subclases incompletas no pueden instanciarse (`TypeError`). Los cuerpos solo contienen documentación y no implementan validación, E/S ni cambios de estado. `RouteCompiler` proporciona el comportamiento concreto documentado por separado. Excepciones o efectos adicionales de implementaciones de terceros:

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

`routes: list[dict]` aporta rutas originales; `fallback: tuple | None`, el fallback; `app_middleware: list[type] | None` opcional precede al middleware de ruta. Retorna `(compiled_routes, fallback): tuple[dict[str, dict], tuple | None]`; documenta `ValueError` por colisiones dinámicas y `TypeError` por clases invocables inválidas. El cuerpo abstracto no realiza operaciones; véase `RouteCompiler.compile` para efectos y errores reales de la implementación.

**`compilePath`**

```python
@staticmethod
@abstractmethod
def compilePath(
    path: str,
) -> tuple[bool, re.Pattern | None, dict[str, Callable]]:
```

Método estático abstracto; `path: str` es la plantilla. Retorna `(is_static, regex, converters): tuple[bool, re.Pattern | None, dict[str, Callable]]`. El cuerpo abstracto no realiza operaciones; véase `RouteCompiler.compilePath` para efectos y errores reales de la implementación.

<a id="api-061"></a>

### `IRouteCache`

[contracts/route_cache.py](../routes/contracts/route_cache.py)

```python
class IRouteCache(ABC):
```

Clase base abstracta (`ABC`). Cada declaración siguiente usa `@abstractmethod`; las subclases incompletas no pueden instanciarse (`TypeError`). Los cuerpos solo contienen documentación y no implementan validación, E/S ni cambios de estado. `RouteCache` proporciona el comportamiento concreto documentado por separado. Excepciones o efectos adicionales de implementaciones de terceros:

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

`routes: dict[str, dict]` aporta datos compilados y `fallback: tuple | None`, su fallback. Retorna un `dict` serializado para caché. El cuerpo abstracto no realiza operaciones; véase `RouteCache.toCache` para efectos y errores reales de la implementación.

**`fromCache`**

```python
@abstractmethod
def fromCache(
    self,
    cached: dict,
) -> tuple[dict[str, dict], tuple | None]:
```

`cached: dict` aporta datos serializados; retorna `(routes, fallback): tuple[dict[str, dict], tuple | None]` reconstruido. El cuerpo abstracto no realiza operaciones; véase `RouteCache.fromCache` para efectos y errores reales de la implementación.

<a id="api-062"></a>

### `IRouteResolver`

[contracts/route_resolver.py](../routes/contracts/route_resolver.py)

```python
class IRouteResolver(ABC):
```

Clase base abstracta (`ABC`). Cada declaración siguiente usa `@abstractmethod`; las subclases incompletas no pueden instanciarse (`TypeError`). Los cuerpos solo contienen documentación y no implementan validación, E/S ni cambios de estado. `RouteResolver` proporciona el comportamiento concreto documentado por separado. Excepciones o efectos adicionales de implementaciones de terceros:

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

`method: str` es el método HTTP; `path: str`, la ruta original. Retorna `ResolvedRoute`; documenta `RouteNotFound` y `MethodNotAllowed` por rutas inexistentes/método incorrecto. El cuerpo abstracto no realiza operaciones; véase `RouteResolver.resolve` para efectos y errores reales de la implementación.

**`options`**

```python
@abstractmethod
def options(self, path: str) -> list[str]:
```

`path: str` es la ruta original; retorna métodos permitidos ordenados como `list[str]`. El cuerpo abstracto no realiza operaciones; véase `RouteResolver.options` para efectos y errores reales de la implementación.

**`fallback`**

```python
@abstractmethod
def fallback(self) -> tuple | None:
```

Sin parámetros; retorna el fallback `tuple | None` registrado. En `IRouteLoader` es una propiedad cuyo acceso documentado activa la carga; en `IRouteResolver` es un método. El cuerpo abstracto no realiza operaciones; véase `RouteResolver.fallback` para efectos y errores reales de la implementación.

**`allRoutes`**

```python
@abstractmethod
def allRoutes(self) -> list:
```

Sin parámetros; la firma retorna `list` (el docstring especifica `list[CompiledRoute]`), con todas las rutas compiladas sin duplicados. El cuerpo abstracto no realiza operaciones; véase `RouteResolver.allRoutes` para efectos y errores reales de la implementación.

**`invalidateCache`**

```python
@abstractmethod
def invalidateCache(self) -> None:
```

Sin parámetros; retorna `None` y declara el vaciado del caché de resolución. El cuerpo abstracto no realiza operaciones; véase `RouteResolver.invalidateCache` para efectos y errores reales de la implementación.

<a id="api-063"></a>

### PayloadTooLargeException

Fuente: [body.py](../payload/body.py).

```python
class PayloadTooLargeException(Exception):
```

Subclase de `Exception` que `BodyStream` lanza cuando los fragmentos no vacíos acumulados del transporte superan el límite configurado. No añade constructor, atributos ni métodos; la construcción y los argumentos provienen de `Exception`.

<a id="api-064"></a>

### BodyStream

Fuente: [body.py](../payload/body.py).

```python
class BodyStream(IBodyStream):
```

Administra un callable receive de ASGI o un iterable asíncrono de RSGI. `interface is Interface.RSGI` selecciona RSGI; cualquier otro valor sigue la ruta ASGI. `None` se representa internamente mediante `sys.maxsize`, un centinela finito. No se valida un límite negativo. La marca de consumo se activa antes del primer await del transporte. No se inspecciona el tipo de mensaje ASGI: solo se consultan `body` y `more_body`.

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

Parámetros:

- `interface` (`Interface`): Selector de interfaz de transporte.
- `receive_or_protocol` (`object`): Callable receive ASGI o protocolo asíncrono RSGI.
- `max_body_size` (`int | None`): Máximo acumulado de bytes; `None` selecciona el límite centinela.

Guarda el transporte y el límite e inicializa la caché vacía y el estado sin consumir; devuelve `None`. No lee el transporte.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `None`.

#### BodyStream.isBuffered

```python
@property
def isBuffered(self) -> bool:
```

Propiedad: indica si hay un búfer completo de bytes en caché; no cambia el estado.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `bool`.

#### BodyStream.isConsumed

```python
@property
def isConsumed(self) -> bool:
```

Propiedad: indica si se inició el consumo, incluso si la lectura se interrumpió o falló; no significa que se recibieron todos los bytes.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `bool`.

#### BodyStream.stream

```python
async def stream(self) -> AsyncGenerator[bytes]:  # NOSONAR # noqa: C901
```

Generador asíncrono que entrega fragmentos no vacíos y comprueba el tamaño acumulado antes de entregar cada uno. Si existe caché, entrega el búfer completo una vez (incluido `b""`). En otro caso marca el transporte consumido; consumir este generador no llena la caché. Una lectura parcial o fallida no puede reiniciarse.

Excepciones: `RuntimeError("Request stream already consumed")` tras consumir sin caché; `PayloadTooLargeException("Request body too large")` cuando el tamaño acumulado supera el límite. Propaga errores del transporte y cancelaciones.

Tipo declarado de retorno/iteración: `AsyncGenerator[bytes]`.

#### BodyStream.read

```python
async def read(self) -> bytes:
```

Acumula fragmentos, los une en un único `bytes`, lo guarda en caché y lo devuelve. Las llamadas posteriores devuelven ese mismo objeto. Durante el almacenamiento conserva la lista de fragmentos y el resultado unido.

Excepciones: Propaga los errores de `stream()`; una lectura fallida no deja una caché completa y conserva la marca de consumo.

Tipo declarado de retorno/iteración: `bytes`.

<a id="api-065"></a>

### Headers

Fuente: [estructures/headers.py](../payload/estructures/headers.py).

```python
class Headers(metaclass=Final):
```

Búsqueda sin distinguir mayúsculas con pares ordenados que conservan las mayúsculas originales. Adopta sin copiar una entrada de tipo exacto `list`; materializa otros iterables. Modificar una lista adoptada puede desincronizarla del índice en minúsculas. La metaclase `Final` rechaza herencia con `TypeError`.

```python
__slots__ = ("_index", "_items")
```

#### Headers.__init__

```python
def __init__(self, raw: Iterable[tuple[str, str]]) -> None:
```

Parámetros:

- `raw` (`Iterable[tuple[str, str]]`): Pares ordenados de encabezados de cadenas.

Guarda/materializa `raw`, crea el índice en minúsculas y devuelve `None`. Conserva el orden de valores repetidos.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `None`.

#### Headers.get

```python
def get(self, key: str, default: str | None = None) -> str | None:
```

Parámetros:

- `key` (`str`): Nombre a consultar; las reglas de mayúsculas se describen en la clase.
- `default` (`str | None`): Valor alternativo cuando no existe el nombre.

Devuelve el último valor de `key` sin distinguir mayúsculas, o `default`.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `str | None`.

#### Headers.count

```python
def count(self, key: str) -> int:
```

Parámetros:

- `key` (`str`): Nombre a consultar; las reglas de mayúsculas se describen en la clase.

Devuelve cuántas entradas coinciden con `key` sin distinguir mayúsculas, o cero.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `int`.

#### Headers.getAll

```python
def getAll(
    self, key: str | None = None,
) -> dict[str, list[str]] | list[str]:
```

Parámetros:

- `key` (`str | None`): Nombre a consultar; las reglas de mayúsculas se describen en la clase.

Para `key=None`, devuelve un diccionario nuevo de nombres en minúsculas a listas copiadas. En otro caso devuelve una lista copiada para esa clave sin distinguir mayúsculas, o `[]`.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `dict[str, list[str]] | list[str]`.

#### Headers.__contains__

```python
def __contains__(self, key: str) -> bool:
```

Parámetros:

- `key` (`str`): Nombre a consultar; las reglas de mayúsculas se describen en la clase.

Indica si existe `key` sin distinguir mayúsculas.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `bool`.

#### Headers.__getitem__

```python
def __getitem__(self, key: str) -> str:
```

Parámetros:

- `key` (`str`): Nombre a consultar; las reglas de mayúsculas se describen en la clase.

Devuelve el último valor de `key` sin distinguir mayúsculas.

Excepciones: `KeyError(key)` si no existe.

Tipo declarado de retorno/iteración: `str`.

#### Headers.__iter__

```python
def __iter__(self) -> Iterator[tuple[str, str]]:
```

Devuelve un iterador de todos los pares `(name, value)` originales, incluidos duplicados.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `Iterator[tuple[str, str]]`.

#### Headers.items

```python
def items(self) -> list[tuple[str, str]]:
```

Devuelve una copia superficial de todos los pares originales en orden de inserción.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `list[tuple[str, str]]`.

#### Headers.byteItems

```python
def byteItems(self) -> Iterator[tuple[bytes, bytes]]:
```

Generador que entrega cada nombre y valor original codificado en UTF-8, conservando mayúsculas y duplicados.

Excepciones: `UnicodeEncodeError` para cadenas que no pueden codificarse como UTF-8 estricto.

Tipo declarado de retorno/iteración: `Iterator[tuple[bytes, bytes]]`.

#### Headers.keys

```python
def keys(self) -> set[str]:
```

Devuelve un conjunto de nombres únicos con sus mayúsculas originales: las variantes de mayúsculas siguen siendo distintas en este resultado.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `set[str]`.

#### Headers.values

```python
def values(self) -> list[str]:
```

Devuelve una lista nueva de todos los valores en orden de inserción, incluidos duplicados.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `list[str]`.

#### Headers.__len__

```python
def __len__(self) -> int:
```

Devuelve el total de pares, incluidos nombres duplicados.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `int`.

#### Headers.__repr__

```python
def __repr__(self) -> str:
```

Devuelve `Headers(...)` con los pares originales.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `str`.

<a id="api-066"></a>

### Cookies

Fuente: [estructures/cookies.py](../payload/estructures/cookies.py).

```python
class Cookies(metaclass=Final):
```

Mapa de cookies que distingue mayúsculas. Separa por punto y coma, ignora segmentos sin `=`, separa cada par por el primer `=`, recorta espacios, retira comillas dobles externas coincidentes y decodifica porcentajes mediante `urllib.parse.unquote`. Conserva los signos más. Para nombres repetidos prevalece el último valor. `Final` rechaza herencia con `TypeError`.

```python
__slots__ = ("_data",)
```

#### Cookies.__init__

```python
def __init__(self, cookie_header: str | None) -> None:
```

Parámetros:

- `cookie_header` (`str | None`): Encabezado Cookie sin procesar, o `None`.

Analiza `cookie_header` en el mapa interno; una entrada falsa/vacía crea un mapa vacío. Devuelve `None`.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `None`.

#### Cookies.get

```python
def get(self, key: str, default: str | None = None) -> str | None:
```

Parámetros:

- `key` (`str`): Nombre a consultar; las reglas de mayúsculas se describen en la clase.
- `default` (`str | None`): Valor alternativo cuando no existe el nombre.

Devuelve el valor de `key` distinguiendo mayúsculas, o `default`.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `str | None`.

#### Cookies.getAll

```python
def getAll(self) -> dict[str, str]:
```

Devuelve una copia superficial del diccionario de cookies.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `dict[str, str]`.

#### Cookies.__getitem__

```python
def __getitem__(self, key: str) -> str:
```

Parámetros:

- `key` (`str`): Nombre a consultar; las reglas de mayúsculas se describen en la clase.

Devuelve el valor de `key` distinguiendo mayúsculas.

Excepciones: `KeyError` si no existe.

Tipo declarado de retorno/iteración: `str`.

#### Cookies.__contains__

```python
def __contains__(self, key: str) -> bool:
```

Parámetros:

- `key` (`str`): Nombre a consultar; las reglas de mayúsculas se describen en la clase.

Indica si existe `key` distinguiendo mayúsculas.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `bool`.

#### Cookies.items

```python
def items(self) -> ItemsView[str, str]:
```

Devuelve la vista viva `dict_items` de pares nombre/valor de cookies, anotada como `ItemsView[str, str]` de `collections.abc`.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `ItemsView[str, str]`.

#### Cookies.keys

```python
def keys(self) -> KeysView[str]:
```

Devuelve la vista viva `dict_keys` de nombres de cookies, anotada como `KeysView[str]` de `collections.abc`.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `KeysView[str]`.

#### Cookies.values

```python
def values(self) -> ValuesView[str]:
```

Devuelve la vista viva `dict_values` de valores de cookies, anotada como `ValuesView[str]` de `collections.abc`.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `ValuesView[str]`.

#### Cookies.__iter__

```python
def __iter__(self) -> Iterator[tuple[str, str]]:
```

Devuelve un iterador de pares `(name, value)`, no solo de nombres.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `Iterator[tuple[str, str]]`.

#### Cookies.__len__

```python
def __len__(self) -> int:
```

Devuelve la cantidad de nombres de cookie distintos.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `int`.

#### Cookies.__repr__

```python
def __repr__(self) -> str:
```

Devuelve `Cookies(...)` con la representación del mapa interno.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `str`.

<a id="api-067"></a>

### QueryParams

Fuente: [estructures/query_params.py](../payload/estructures/query_params.py).

```python
class QueryParams(metaclass=Final):
```

Multimapa de query que distingue mayúsculas, construido con `parse_qsl(..., keep_blank_values=True, strict_parsing=False)`. Conserva pares duplicados ordenados y valores vacíos; usa la decodificación URL de la biblioteca estándar, incluido `+` como espacio. `Final` rechaza herencia con `TypeError`.

```python
__slots__ = ("_index", "_items")
```

#### QueryParams.__init__

```python
def __init__(self, query_string: str) -> None:
```

Parámetros:

- `query_string` (`str`): Cadena query de URL que se decodificará.

Analiza `query_string`, crea un índice separado de último valor/valores múltiples y devuelve `None`.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `None`.

#### QueryParams.get

```python
def get(self, key: str, default: str | None = None) -> str | None:
```

Parámetros:

- `key` (`str`): Nombre a consultar; las reglas de mayúsculas se describen en la clase.
- `default` (`str | None`): Valor alternativo cuando no existe el nombre.

Devuelve el último valor de `key` distinguiendo mayúsculas, o `default`.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `str | None`.

#### QueryParams.getAll

```python
def getAll(self, key: str) -> list[str]:
```

Parámetros:

- `key` (`str`): Nombre a consultar; las reglas de mayúsculas se describen en la clase.

Devuelve una lista ordenada nueva de valores de `key`, o `[]`.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `list[str]`.

#### QueryParams.getList

```python
def getList(self, key: str) -> list[str]:
```

Parámetros:

- `key` (`str`): Nombre a consultar; las reglas de mayúsculas se describen en la clase.

Alias que delega en `getAll(key)`; devuelve el mismo tipo de lista copiada.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `list[str]`.

#### QueryParams.multiItems

```python
def multiItems(self) -> list[tuple[str, str]]:
```

Devuelve una copia superficial de todos los pares ordenados, incluidos duplicados.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `list[tuple[str, str]]`.

#### QueryParams.__contains__

```python
def __contains__(self, key: str) -> bool:
```

Parámetros:

- `key` (`str`): Nombre a consultar; las reglas de mayúsculas se describen en la clase.

Indica si `key` está en el índice distinguiendo mayúsculas.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `bool`.

#### QueryParams.__getitem__

```python
def __getitem__(self, key: str) -> str:
```

Parámetros:

- `key` (`str`): Nombre a consultar; las reglas de mayúsculas se describen en la clase.

Devuelve el último valor de `key`.

Excepciones: `KeyError(key)` si no existe.

Tipo declarado de retorno/iteración: `str`.

#### QueryParams.items

```python
def items(self) -> list[tuple[str, str]]:
```

Devuelve una copia superficial de todos los pares, equivalente a `multiItems()`.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `list[tuple[str, str]]`.

#### QueryParams.keys

```python
def keys(self) -> set[str]:
```

Devuelve un conjunto nuevo de nombres de parámetros únicos.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `set[str]`.

#### QueryParams.values

```python
def values(self) -> list[str]:
```

Devuelve una lista nueva de todos los valores en el orden de pares, incluidos duplicados.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `list[str]`.

#### QueryParams.__iter__

```python
def __iter__(self) -> Iterator[tuple[str, str]]:
```

Devuelve un iterador de todos los pares `(key, value)`, incluidos duplicados.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `Iterator[tuple[str, str]]`.

#### QueryParams.__len__

```python
def __len__(self) -> int:
```

Devuelve el total de pares, incluidos nombres repetidos.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `int`.

#### QueryParams.__repr__

```python
def __repr__(self) -> str:
```

Devuelve `QueryParams(...)` con sus pares ordenados.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `str`.

<a id="api-068"></a>

### FormData

Fuente: [form_data.py](../payload/form_data.py).

```python
class FormData(IFormData):
```

Pares multipart ordenados con un índice separado de nombres únicos. El constructor copia la lista externa, pero comparte los objetos de archivos. Reconoce texto con `isinstance(value, str)`; trata cualquier otro valor como archivo. El acceso usa el último valor de nombres repetidos. Proporciona un gestor de contexto síncrono.

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

Parámetros:

- `items` (`list[tuple[str, str | UploadedFile]]`): Pares multipart `(name, value)` ordenados.

Copia `items`, construye el índice y devuelve `None`; los nombres repetidos conservan el orden de inserción.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `None`.

#### FormData.fields

```python
@property
def fields(self) -> dict[str, list[str]]:
```

Propiedad: devuelve un diccionario y listas nuevos que agrupan solo cadenas por nombre. No modifica los pares almacenados.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `dict[str, list[str]]`.

#### FormData.files

```python
@property
def files(self) -> dict[str, list[UploadedFile]]:
```

Propiedad: devuelve un diccionario y listas nuevos que agrupan valores que no son cadenas; comparte los objetos `UploadedFile`.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `dict[str, list[UploadedFile]]`.

#### FormData.get

```python
def get(
    self,
    key: str,
    default: object | None = None,
) -> object | None:
```

Parámetros:

- `key` (`str`): Nombre a consultar; las reglas de mayúsculas se describen en la clase.
- `default` (`object | None`): Valor alternativo cuando no existe el nombre.

Devuelve el último valor de `key`, o `default` si no existe. No modifica estado; comparte el archivo devuelto.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `object | None`.

#### FormData.getAll

```python
def getAll(self, key: str) -> list[str | UploadedFile]:
```

Parámetros:

- `key` (`str`): Nombre a consultar; las reglas de mayúsculas se describen en la clase.

Devuelve una lista nueva con todos los valores de `key` en orden de inserción, o `[]`; comparte los archivos.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `list[str | UploadedFile]`.

#### FormData.allItems

```python
@property
def allItems(self) -> list[tuple[str, str | UploadedFile]]:
```

Propiedad: devuelve la lista interna sin copiar. El docstring indica que no debe modificarse: hacerlo puede desincronizarla del índice de búsqueda.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `list[tuple[str, str | UploadedFile]]`.

#### FormData.multiItems

```python
def multiItems(self) -> list[tuple[str, str | UploadedFile]]:
```

Devuelve una copia superficial de todos los pares ordenados.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `list[tuple[str, str | UploadedFile]]`.

#### FormData.__getitem__

```python
def __getitem__(self, key: str) -> object:
```

Parámetros:

- `key` (`str`): Nombre a consultar; las reglas de mayúsculas se describen en la clase.

Delega en `get(key)` y devuelve el último valor. Una clave inexistente devuelve `None`, sin lanzar `KeyError`.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `object`.

#### FormData.__contains__

```python
def __contains__(self, key: str) -> bool:
```

Parámetros:

- `key` (`str`): Nombre a consultar; las reglas de mayúsculas se describen en la clase.

Indica si el nombre `key` existe en el índice.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `bool`.

#### FormData.__iter__

```python
def __iter__(self) -> Iterator[str]:
```

Devuelve un iterador de nombres únicos en orden de primera aparición.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `Iterator[str]`.

#### FormData.__len__

```python
def __len__(self) -> int:
```

Devuelve la cantidad de nombres únicos, no la cantidad de pares almacenados.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `int`.

#### FormData.__repr__

```python
def __repr__(self) -> str:
```

Devuelve `FormData(...)` con la representación de todos los pares.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `str`.

#### FormData.close

```python
def close(self) -> None:
```

Llama a `close()` en cada valor que no es cadena y devuelve `None`; no elimina pares ni deduplica archivos repetidos.

Excepciones: Un fallo del cierre delegado se propaga e interrumpe la limpieza de los elementos posteriores.

Tipo declarado de retorno/iteración: `None`.

#### FormData.__enter__

```python
def __enter__(self) -> Self:
```

Devuelve esta instancia (`Self`).

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `Self`.

#### FormData.__exit__

```python
def __exit__(
    self,
    exc_type: type[BaseException] | None,
    exc_val: BaseException | None,
    exc_tb: TracebackType | None,
) -> None:
```

Parámetros:

- `exc_type` (`type[BaseException] | None`): Clase de excepción del contexto, o `None`.
- `exc_val` (`BaseException | None`): Instancia de excepción del contexto, o `None`.
- `exc_tb` (`TracebackType | None`): Traceback del contexto, o `None`.

Ignora los argumentos de excepción, llama a `close()` y devuelve `None`; no suprime las excepciones del cuerpo del contexto.

Excepciones: Propaga errores de limpieza de `close()`.

Tipo declarado de retorno/iteración: `None`.

<a id="api-069"></a>

### MediaTypeRegistry

Fuente: [media_types.py](../payload/media_types.py).

```python
class MediaTypeRegistry(IMediaTypeRegistry):
```

Mapa mutable de tipos de contenido en minúsculas a parsers síncronos. Convierte claves a minúsculas, pero no quita parámetros, espacios ni sufijos de proveedor. No ejecuta parsers ni valida que sean invocables. `extend()` crea un mapa independiente y comparte los callables.

```python
__slots__ = ("_parsers",)
```

#### MediaTypeRegistry.__init__

```python
def __init__(self, parsers: dict[str, BodyParser] | None = None) -> None:
```

Parámetros:

- `parsers` (`dict[str, BodyParser] | None`): Mapa de tipo de contenido a parser síncrono.

Copia `parsers` con claves en minúsculas, o crea un mapa vacío para `None`/un mapa vacío; devuelve `None`.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `None`.

#### MediaTypeRegistry.register

```python
def register(self, media_type: str, parser: BodyParser) -> None:
```

Parámetros:

- `media_type` (`str`): Clave de tipo de contenido para consultar/registrar.
- `parser` (`BodyParser`): Callable síncrono que recibe bytes y devuelve un objeto.

Agrega o reemplaza `media_type.lower()` por `parser` en este registro; devuelve `None`.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `None`.

#### MediaTypeRegistry.get

```python
def get(self, media_type: str) -> BodyParser | None:
```

Parámetros:

- `media_type` (`str`): Clave de tipo de contenido para consultar/registrar.

Devuelve el parser de `media_type.lower()`, o `None`; no lo invoca.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `BodyParser | None`.

#### MediaTypeRegistry.extend

```python
def extend(self, parsers: dict[str, BodyParser]) -> MediaTypeRegistry:
```

Parámetros:

- `parsers` (`dict[str, BodyParser]`): Mapa de tipo de contenido a parser síncrono.

Devuelve un `MediaTypeRegistry` nuevo en el que prevalecen las entradas normalizadas de `parsers`; conserva el registro original.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `MediaTypeRegistry`.

<a id="api-070"></a>

### BodyParser

Fuentes: [media_types.py](../payload/media_types.py), [contracts/media_types.py](../payload/contracts/media_types.py).

```python
BodyParser = Callable[[bytes], object]
```

Alias idéntico definido en ambos módulos: callable síncrono que recibe un `bytes` y devuelve `object`; no aporta validación en tiempo de ejecución.

<a id="api-071"></a>

### DEFAULT_MEDIA_TYPES

Fuente: [media_types.py](../payload/media_types.py).

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

Singleton mutable del módulo. Llamar a `register()` en este objeto cambia los valores compartidos. No incluye parser multipart, coincidencia por sufijos ni entrada de `parse_urlencoded_multi`.

<a id="api-072"></a>

### parse_content_type

Fuente: [parsers.py](../payload/parsers.py).

```python
def parse_content_type(header: str) -> tuple[str, dict[str, str]]:
```

Parámetros:

- `header` (`str`): Cadena Content-Type sin procesar.

Devuelve `(media_type, params)` de `header`: recorta y convierte a minúsculas el tipo y nombres de parámetros; retira espacios y comillas dobles de los extremos de valores; prevalece el último duplicado. Los separadores de parámetros son puntos y coma fuera de valores entre comillas dobles, por lo que `boundary="a;b"` permanece como un solo parámetro. Los caracteres escapados dentro de comillas no cierran el valor entrecomillado; este parser conserva sus barras inversas. Ignora segmentos sin `=`. No modifica la entrada.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `tuple[str, dict[str, str]]`.

**Helper interno `_split_header_parameters`**

```python
def _split_header_parameters(
    header: str, *, quote_chars: str = '"',
) -> list[str]:
```

`header: str` es texto de encabezado/parámetros; `quote_chars: str = '"'`, solo por nombre, selecciona los delimitadores de comillas admitidos. Devuelve una `list[str]` nueva de segmentos originales sin los puntos y coma separadores, conservando espacios, comillas y escapes. Una comilla solo abre en el primer carácter no blanco tras el primer `=` de un segmento; los apóstrofos dentro de valores sin comillas, incluidos los separadores de charset/idioma RFC 5987, no abren comillas. Dentro de un valor entrecomillado, una barra inversa protege el carácter siguiente para que no lo cierre. Un valor sin comilla de cierre consume el resto del encabezado. El helper no retira comillas ni desescapa, no modifica la entrada ni realiza E/S; no contiene `raise` explícito. `parse_content_type` usa comillas dobles; `MultipartPart` habilita comillas simples y dobles y aplica su propia decodificación de valores.

<a id="api-073"></a>

### parse_json

Fuente: [parsers.py](../payload/parsers.py).

```python
def parse_json(raw: bytes) -> object:
```

Parámetros:

- `raw` (`bytes`): Bytes del contenido sin procesar.

Devuelve el objeto Python decodificado desde `raw` mediante `msgspec.json.decode`; no modifica estado del módulo.

Excepciones: `msgspec.DecodeError` para JSON inválido, propagado desde el decodificador.

Tipo declarado de retorno/iteración: `object`.

<a id="api-074"></a>

### parse_msgpack

Fuente: [parsers.py](../payload/parsers.py).

```python
def parse_msgpack(raw: bytes) -> object:
```

Parámetros:

- `raw` (`bytes`): Bytes del contenido sin procesar.

Devuelve el objeto Python decodificado desde `raw` mediante `msgspec.msgpack.decode`; no modifica estado del módulo.

Excepciones: `msgspec.DecodeError` para MessagePack inválido, propagado desde el decodificador.

Tipo declarado de retorno/iteración: `object`.

<a id="api-075"></a>

### parse_urlencoded

Fuente: [parsers.py](../payload/parsers.py).

```python
def parse_urlencoded(raw: bytes) -> dict[str, str]:
```

Parámetros:

- `raw` (`bytes`): Bytes del contenido sin procesar.

Decodifica `raw` como UTF-8 estricto, llama a `parse_qsl(..., keep_blank_values=True)` y construye un diccionario. Conserva valores vacíos; para nombres repetidos conserva el último valor. Usa los valores predeterminados de la biblioteca estándar, incluido `+` como espacio.

Excepciones: `UnicodeDecodeError` si falla la decodificación UTF-8 inicial.

Tipo declarado de retorno/iteración: `dict[str, str]`.

<a id="api-076"></a>

### parse_urlencoded_multi

Fuente: [parsers.py](../payload/parsers.py).

```python
def parse_urlencoded_multi(raw: bytes) -> dict[str, str | list[str]]:
```

Parámetros:

- `raw` (`bytes`): Bytes del contenido sin procesar.

Devuelve campos decodificados, con una aparición como `str` y nombres repetidos como `list[str]` ordenada. Conserva valores vacíos y comparte el comportamiento UTF-8 y de query de `parse_urlencoded`.

Excepciones: `UnicodeDecodeError` si falla la decodificación UTF-8 inicial.

Tipo declarado de retorno/iteración: `dict[str, str | list[str]]`.

<a id="api-077"></a>

### parse_xml

Fuente: [parsers.py](../payload/parsers.py).

```python
def parse_xml(raw: bytes) -> XMLElement:
```

Parámetros:

- `raw` (`bytes`): Bytes del contenido sin procesar.

Devuelve un `xml.etree.ElementTree.Element` mediante `defusedxml.ElementTree.fromstring(raw)` sin opciones. El código de la dependencia instalada usa `forbid_dtd=False`, `forbid_entities=True` y `forbid_external=True`. Se rechazan declaraciones de entidades internas y externas; se permiten DTD sin declaraciones de entidades y no se resuelven recursos externos. Esta envoltura no implementa lecturas de archivos ni consultas de red.

Excepciones: `xml.etree.ElementTree.ParseError` para XML mal formado; `defusedxml.common.EntitiesForbidden` para declaraciones de entidades internas o externas. `EntitiesForbidden` es subclase de `defusedxml.common.DefusedXmlException` y no es un `ParseError`. Estas excepciones se propagan sin transformar.

Tipo declarado de retorno/iteración: `XMLElement`.

<a id="api-078"></a>

### parse_text

Fuente: [parsers.py](../payload/parsers.py).

```python
def parse_text(raw: bytes) -> str:
```

Parámetros:

- `raw` (`bytes`): Bytes del contenido sin procesar.

Devuelve la decodificación UTF-8 estricta de `raw`; no modifica estado.

Excepciones: `UnicodeDecodeError` para UTF-8 inválido.

Tipo declarado de retorno/iteración: `str`.

<a id="api-079"></a>

### parse_binary

Fuente: [parsers.py](../payload/parsers.py).

```python
def parse_binary(raw: bytes) -> bytes:
```

Parámetros:

- `raw` (`bytes`): Bytes del contenido sin procesar.

Devuelve `raw` sin cambios, conservando la identidad del objeto; no modifica estado.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `bytes`.

<a id="api-080"></a>

### UploadedFile

Fuente: [uploaded_file.py](../payload/uploaded_file.py).

```python
class UploadedFile(IUploadedFile):
```

Envoltura síncrona de `tempfile.SpooledTemporaryFile`; comienza en memoria y puede pasar a disco. El atributo público `filename` está saneado y `content_type: str | None` conserva los metadatos del cliente sin inspeccionar el contenido. Calcula la extensión una vez; cambiar `filename` después no la recalcula. Esta clase no tiene protocolo de gestor de contexto; `FormData` proporciona limpieza.

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

Parámetros:

- `filename` (`str`): Nombre de archivo del cliente que se saneará.
- `content_type` (`str | None`): Tipo MIME declarado por el cliente o `None`.
- `memory_threshold` (`int`): Umbral del búfer por archivo, en bytes.

Normaliza separadores, conserva el último componente de la ruta, elimina caracteres de control/prohibidos y puntos iniciales, y usa `"upload"` si queda vacío. Crea el búfer temporal, inicializa tamaño/estado de disco y guarda el sufijo en minúsculas; devuelve `None`. El saneamiento no valida todos los nombres reservados por el SO (por ejemplo, dispositivos). `memory_threshold=0` desactiva el paso automático a disco por tamaño.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `None`.

#### UploadedFile.requiresDiskWrite

```python
def requiresDiskWrite(self, size: int = 0) -> bool:
```

Parámetros:

- `size` (`int`): Cantidad prevista de bytes de escritura.

Devuelve `_rolled` o si el contador de bytes más `size` superaría un umbral distinto de cero; no modifica estado. Usa el contador registrado, no la posición del archivo.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `bool`.

#### UploadedFile.write

```python
def write(self, chunk: bytes | bytearray | memoryview) -> None:
```

Parámetros:

- `chunk` (`bytes | bytearray | memoryview`): Secuencia de bytes que se escribirá.

Busca EOF con `seek(0, SEEK_END)` y agrega `chunk` al final, conservando el contenido previo tras lecturas parciales con `chunks()` tanto en memoria como en disco. Actualiza el estado previsto de disco antes de escribir e incrementa el contador en `len(chunk)` tras una escritura exitosa; devuelve `None`. El cursor compartido termina en EOF, incluso si hay un iterador de `chunks()` suspendido.

Excepciones: Errores delegados de búsqueda/escritura, incluido `ValueError` después del cierre. El estado de disco se actualiza tras buscar el final y antes de escribir; el contador de bytes solo aumenta cuando la escritura tiene éxito.

Tipo declarado de retorno/iteración: `None`.

#### UploadedFile.size

```python
@property
def size(self) -> int:
```

Propiedad que devuelve el contador de bytes; las escrituras lo incrementan y `replace()` lo fija a la longitud de reemplazo.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `int`.

#### UploadedFile.extension

```python
@property
def extension(self) -> str:
```

Propiedad que devuelve el último sufijo en minúsculas con su punto, o `""` si no hay punto después del primer carácter.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `str`.

#### UploadedFile.read

```python
def read(self) -> bytes:
```

Busca la posición cero, lee todo el contenido en `bytes` y deja la posición al final de la lectura.

Excepciones: Errores delegados de E/S, incluido `ValueError` después del cierre.

Tipo declarado de retorno/iteración: `bytes`.

#### UploadedFile.chunks

```python
def chunks(self, size: int = _CHUNK_SIZE) -> Iterator[bytes]:
```

Parámetros:

- `size` (`int`): Máximo de bytes solicitados por lectura.

Generador que rebobina al iniciar la iteración y entrega lecturas sucesivas de `size` bytes. `_CHUNK_SIZE` equivale a `64 * 1024`. No exige tamaños positivos: cero no entrega datos y un tamaño negativo delega una lectura completa al archivo. La iteración cambia la posición compartida.

Excepciones: Errores delegados de lectura/búsqueda, incluido `ValueError` después del cierre.

Tipo declarado de retorno/iteración: `Iterator[bytes]`.

#### UploadedFile.replace

```python
def replace(self, data: bytes) -> None:
```

Parámetros:

- `data` (`bytes`): Bytes de reemplazo.

Busca cero, trunca, escribe `data` y fija `size` a `len(data)`; devuelve `None`. Un archivo que pasó a disco permanece en disco. El reemplazo no es atómico: puede fallar después de truncar.

Excepciones: Errores delegados de E/S, incluido `ValueError` después del cierre.

Tipo declarado de retorno/iteración: `None`.

#### UploadedFile.save

```python
def save(self, path: str | Path) -> None:
```

Parámetros:

- `path` (`str | Path`): Destino en el sistema de archivos.

Construye `Path(path)`, rebobina el búfer y después abre el destino en modo `wb` (crea o trunca) y copia en fragmentos de 64 KiB; devuelve `None`. No crea directorios padre, sanea `path`, cierra la carga ni garantiza una escritura atómica.

Excepciones: Errores del sistema de archivos como `FileNotFoundError`, `PermissionError` y otros `OSError`; errores de lectura/búsqueda después del cierre.

Tipo declarado de retorno/iteración: `None`.

#### UploadedFile.close

```python
def close(self) -> None:
```

Cierra el búfer y libera el archivo temporal subyacente; devuelve `None`.

Excepciones: No captura errores delegados de limpieza/E/S.

Tipo declarado de retorno/iteración: `None`.

#### UploadedFile.__del__

```python
def __del__(self) -> None:
```

Llama a `close()` durante la finalización y suprime `Exception`; devuelve `None`.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `None`.

<a id="api-081"></a>

### MultipartPart

Fuente: [part.py](../payload/part.py).

```python
class MultipartPart(IMultipartPart):
```

Representa una parte multipart. Sus atributos públicos son `headers` (el diccionario original), `name: str | None`, `filename: str | None`, `content_type: str | None`, `is_file: bool` y `data: UploadedFile | bytearray`. Un filename declarado, incluso vacío, selecciona un archivo. `filename` conserva el valor analizado, mientras `data.filename` se sanea mediante `UploadedFile`.

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

Parámetros:

- `headers` (`dict[str, str]`): Encabezados MIME con claves en minúsculas.
- `memory_threshold` (`int`): Umbral del búfer por archivo, en bytes.

Guarda `headers`, analiza `content-disposition` y crea un `UploadedFile` con `memory_threshold` o un `bytearray`; devuelve `None`. Las claves deben estar ya en minúsculas. El privado `_parseContentDisposition` usa `_split_header_parameters` para separar solo por puntos y coma fuera de valores entre comillas simples o dobles, conservando valores como `filename="a;b.txt"`. Retira comillas coincidentes, desescapa comillas y prioriza valores RFC 5987 `name*`/`filename*` decodificados correctamente. Las comillas escapadas no cierran un segmento entrecomillado y los apóstrofos dentro de valores sin comillas o de sintaxis RFC 5987 no abren uno. Suprime errores al decodificar atributos extendidos.

Excepciones: No contiene `raise` explícito; no intercepta fallos de operaciones delegadas salvo lo descrito arriba.

Tipo declarado de retorno/iteración: `None`.

#### MultipartPart.write

```python
def write(self, chunk: bytes | bytearray | memoryview) -> None:
```

Parámetros:

- `chunk` (`bytes | bytearray | memoryview`): Secuencia de bytes que se escribirá.

Pasa `chunk` al escritor elegido al construir: `UploadedFile.write` o `bytearray.extend`; devuelve `None` y acumula los datos.

Excepciones: Propaga fallos de escritura en partes de archivo.

Tipo declarado de retorno/iteración: `None`.

#### MultipartPart.finalize

```python
def finalize(self) -> UploadedFile | str:  # NOSONAR
```

Devuelve una cadena decodificada para campos o el mismo `UploadedFile` para archivos. Reconoce content-transfer encoding `base64` y `quoted-printable` sin distinguir mayúsculas. Los campos usan la primera subcadena `charset=` de `content-type`, o UTF-8, con decodificación estricta. Lee completos los archivos con estas codificaciones, los decodifica y reemplaza su contenido. Finalizar de nuevo un archivo codificado decodifica otra vez su contenido ya reemplazado; no existe marca de finalización.

Excepciones: `UnicodeDecodeError` para texto inválido; `LookupError` para charset desconocido; errores base64 (`binascii.Error`) por padding/codificación inválidos; errores delegados de E/S de archivos.

Tipo declarado de retorno/iteración: `UploadedFile | str`.

<a id="api-082"></a>

### complete_in_thread

Fuente: [stream_parser.py](../payload/stream_parser.py).

```python
async def complete_in_thread[T](function: Callable[..., T], *args: object) -> T:
```

Parámetros:

- `function` (`Callable[..., T]`): Callable bloqueante que se ejecutará en un trabajador.
- `args` (`object`): Argumentos posicionales enviados a `function`.

Ejecuta `function(*args)` mediante `asyncio.to_thread`, crea una tarea y la espera con `shield`; devuelve su resultado `T`. Ante cancelación espera la tarea y relanza la cancelación si el trabajador termina correctamente. Bajo una sola cancelación mantiene vivo al trabajador que usa el memoryview multipart hasta terminar antes de limpiar el parser.

Excepciones: Propaga excepciones del trabajador; un fallo del trabajador mientras espera la cancelación puede reemplazar `CancelledError`. Una nueva cancelación durante `await task` sin shield se suprime allí; la función no implementa un bucle que garantice la finalización frente a cancelaciones repetidas.

Tipo declarado de retorno/iteración: `T`.

<a id="api-083"></a>

### MultipartStreamParser

Fuente: [stream_parser.py](../payload/stream_parser.py).

```python
class MultipartStreamParser(IMultipartStreamParser):
```

Parser multipart asíncrono con estado sobre un flujo suministrado. Expone `stream`, `boundary` con prefijo, `buffer` mutable, límites y contadores (`files_count`, `fields_count`, `current_part_size`). Reconoce delimitadores CRLF, espacios/tabulaciones opcionales y cierre, incluido cierre al final del flujo; rechaza entradas incompletas. Puede terminar sin agotar el flujo al reconocer el cierre. No reinicia su estado para otro análisis.

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

Parámetros:

- `stream` (`AsyncIterable[bytes]`): Iterable asíncrono de bytes multipart.
- `boundary` (`bytes`): Token boundary sin el prefijo `--`.
- `max_files` (`int`): Máximo de partes de archivo aceptadas.
- `max_fields` (`int`): Máximo de campos de texto aceptados.
- `max_part_size` (`int`): Máximo de bytes sin decodificar de una parte.
- `memory_threshold` (`int`): Umbral del búfer por archivo, en bytes.
- `max_header_size` (`int`): Límite de encabezados y del sufijo de línea delimitadora, en bytes.

Guarda `stream`, asigna `boundary = b"--" + boundary`, crea el bytearray de trabajo e inicializa contadores; devuelve `None`. Conserva los límites sin comprobar que sean positivos. `max_part_size` cuenta bytes recibidos antes de decodificar content-transfer encoding. `memory_threshold` solo se aplica a archivos.

Excepciones: `ValueError("Missing multipart boundary")` para un boundary falso/vacío.

Tipo declarado de retorno/iteración: `None`.

#### MultipartStreamParser.parse

```python
async def parse(self) -> FormData:
```

Consume el flujo asíncrono y devuelve `FormData` con campos y archivos ordenados. Decodifica encabezados de partes como Latin-1, convierte claves a minúsculas, reemplaza encabezados repetidos e ignora líneas sin dos puntos. Exige un atributo `name` (acepta nombre vacío). `_writePart` aplica el límite de bytes de la parte; las escrituras en disco y la finalización de archivos codificados en disco usan `complete_in_thread`. Ante `BaseException`, cierra el archivo actual y los archivos acumulados antes de relanzar; tras el éxito, el llamador se encarga de cerrar `FormData`.

Excepciones: `ValueError`: falta de nombre, demasiados archivos/campos, parte mayor al máximo, encabezados mayores al máximo, sufijo de línea delimitadora mayor a `max_header_size`, ausencia de parte actual o cuerpo incompleto. Propaga errores del transporte, cancelación, decodificación y E/S. Un error al limpiar puede interrumpir la limpieza y reemplazar el error original.

Tipo declarado de retorno/iteración: `FormData`.

<a id="api-084"></a>

### IBodyStream

Fuente: [contracts/body_stream.py](../payload/contracts/body_stream.py).

```python
class IBodyStream(ABC):
```

Contrato `ABC` de almacenamiento y reproducción del cuerpo; implementado por `BodyStream`. Todos los miembros listados son abstractos y la clase usa `__slots__ = ()`. Instanciarla con métodos abstractos sin resolver lanza `TypeError`. No define constructor.

#### IBodyStream.isBuffered

```python
@property
@abstractmethod
def isBuffered(self) -> bool:
```

Contrato abstracto; el propósito de parámetros y retorno corresponde a `BodyStream.isBuffered` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `bool`.

#### IBodyStream.isConsumed

```python
@property
@abstractmethod
def isConsumed(self) -> bool:
```

Contrato abstracto; el propósito de parámetros y retorno corresponde a `BodyStream.isConsumed` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `bool`.

#### IBodyStream.stream

```python
@abstractmethod
async def stream(self) -> AsyncGenerator[bytes]:  # NOSONAR
```

Contrato abstracto; el propósito de parámetros y retorno corresponde a `BodyStream.stream` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Su docstring declara `RuntimeError` por consumo repetido sin caché y `PayloadTooLargeException` por superar el límite; este cuerpo abstracto no lanza ninguna.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `AsyncGenerator[bytes]`.

#### IBodyStream.read

```python
@abstractmethod
async def read(self) -> bytes:
```

Contrato abstracto; el propósito de parámetros y retorno corresponde a `BodyStream.read` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `bytes`.

<a id="api-085"></a>

### IFormData

Fuente: [contracts/form_data.py](../payload/contracts/form_data.py).

```python
class IFormData(ABC):
```

Contrato `ABC` de campos/archivos multipart ordenados y limpieza; implementado por `FormData`. Todos los miembros listados son abstractos y la clase usa `__slots__ = ()`. Instanciarla con métodos abstractos sin resolver lanza `TypeError`. No define constructor.

#### IFormData.fields

```python
@property
@abstractmethod
def fields(self) -> dict[str, list[str]]:
```

Contrato abstracto; el propósito de parámetros y retorno corresponde a `FormData.fields` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `dict[str, list[str]]`.

#### IFormData.files

```python
@property
@abstractmethod
def files(self) -> dict[str, list[UploadedFile]]:
```

Contrato abstracto; el propósito de parámetros y retorno corresponde a `FormData.files` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `dict[str, list[UploadedFile]]`.

#### IFormData.allItems

```python
@property
@abstractmethod
def allItems(self) -> list[tuple[str, str | UploadedFile]]:
```

Contrato abstracto; el propósito de parámetros y retorno corresponde a `FormData.allItems` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `list[tuple[str, str | UploadedFile]]`.

#### IFormData.get

```python
@abstractmethod
def get(
    self,
    key: str,
    default: object | None = None,
) -> object | None:
```

Parámetros:

- `key` (`str`): Nombre a consultar; las reglas de mayúsculas se describen en la clase.
- `default` (`object | None`): Valor alternativo cuando no existe el nombre.

Contrato abstracto; el propósito de parámetros y retorno corresponde a `FormData.get` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `object | None`.

#### IFormData.getAll

```python
@abstractmethod
def getAll(self, key: str) -> list[str | UploadedFile]:
```

Parámetros:

- `key` (`str`): Nombre a consultar; las reglas de mayúsculas se describen en la clase.

Contrato abstracto; el propósito de parámetros y retorno corresponde a `FormData.getAll` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `list[str | UploadedFile]`.

#### IFormData.multiItems

```python
@abstractmethod
def multiItems(self) -> list[tuple[str, str | UploadedFile]]:
```

Contrato abstracto; el propósito de parámetros y retorno corresponde a `FormData.multiItems` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `list[tuple[str, str | UploadedFile]]`.

#### IFormData.close

```python
@abstractmethod
def close(self) -> None:
```

Contrato abstracto; el propósito de parámetros y retorno corresponde a `FormData.close` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `None`.

#### IFormData.__getitem__

```python
@abstractmethod
def __getitem__(self, key: str) -> object:
```

Parámetros:

- `key` (`str`): Nombre a consultar; las reglas de mayúsculas se describen en la clase.

Contrato abstracto; el propósito de parámetros y retorno corresponde a `FormData.__getitem__` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `object`.

#### IFormData.__contains__

```python
@abstractmethod
def __contains__(self, key: str) -> bool:
```

Parámetros:

- `key` (`str`): Nombre a consultar; las reglas de mayúsculas se describen en la clase.

Contrato abstracto; el propósito de parámetros y retorno corresponde a `FormData.__contains__` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `bool`.

#### IFormData.__iter__

```python
@abstractmethod
def __iter__(self) -> Iterator[str]:
```

Contrato abstracto; el propósito de parámetros y retorno corresponde a `FormData.__iter__` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `Iterator[str]`.

#### IFormData.__len__

```python
@abstractmethod
def __len__(self) -> int:
```

Contrato abstracto; el propósito de parámetros y retorno corresponde a `FormData.__len__` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `int`.

#### IFormData.__repr__

```python
@abstractmethod
def __repr__(self) -> str:
```

Contrato abstracto; el propósito de parámetros y retorno corresponde a `FormData.__repr__` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `str`.

#### IFormData.__enter__

```python
@abstractmethod
def __enter__(self) -> Self:
```

Contrato abstracto; el propósito de parámetros y retorno corresponde a `FormData.__enter__` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `Self`.

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

Parámetros:

- `exc_type` (`type[BaseException] | None`): Clase de excepción del contexto, o `None`.
- `exc_val` (`BaseException | None`): Instancia de excepción del contexto, o `None`.
- `exc_tb` (`TracebackType | None`): Traceback del contexto, o `None`.

Contrato abstracto; el propósito de parámetros y retorno corresponde a `FormData.__exit__` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `None`.

<a id="api-086"></a>

### IMediaTypeRegistry

Fuente: [contracts/media_types.py](../payload/contracts/media_types.py).

```python
class IMediaTypeRegistry(ABC):
```

Contrato `ABC` de registro y extensión de parsers por tipo de contenido; implementado por `MediaTypeRegistry`. Todos los miembros listados son abstractos y la clase usa `__slots__ = ()`. Instanciarla con métodos abstractos sin resolver lanza `TypeError`. No define constructor.

#### IMediaTypeRegistry.register

```python
@abstractmethod
def register(self, media_type: str, parser: BodyParser) -> None:
```

Parámetros:

- `media_type` (`str`): Clave de tipo de contenido para consultar/registrar.
- `parser` (`BodyParser`): Callable síncrono que recibe bytes y devuelve un objeto.

Contrato abstracto; el propósito de parámetros y retorno corresponde a `MediaTypeRegistry.register` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `None`.

#### IMediaTypeRegistry.get

```python
@abstractmethod
def get(self, media_type: str) -> BodyParser | None:
```

Parámetros:

- `media_type` (`str`): Clave de tipo de contenido para consultar/registrar.

Contrato abstracto; el propósito de parámetros y retorno corresponde a `MediaTypeRegistry.get` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `BodyParser | None`.

#### IMediaTypeRegistry.extend

```python
@abstractmethod
def extend(self, parsers: dict[str, BodyParser]) -> IMediaTypeRegistry:
```

Parámetros:

- `parsers` (`dict[str, BodyParser]`): Mapa de tipo de contenido a parser síncrono.

Contrato abstracto; el propósito de parámetros y retorno corresponde a `MediaTypeRegistry.extend` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `IMediaTypeRegistry`.

<a id="api-087"></a>

### IUploadedFile

Fuente: [contracts/uploaded_file.py](../payload/contracts/uploaded_file.py).

```python
class IUploadedFile(ABC):
```

Contrato `ABC` de contenido y recursos de archivos cargados; implementado por `UploadedFile`. Todos los miembros listados son abstractos y la clase usa `__slots__ = ()`. Instanciarla con métodos abstractos sin resolver lanza `TypeError`. No define constructor.

#### IUploadedFile.size

```python
@property
@abstractmethod
def size(self) -> int:
```

Contrato abstracto; el propósito de parámetros y retorno corresponde a `UploadedFile.size` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `int`.

#### IUploadedFile.extension

```python
@property
@abstractmethod
def extension(self) -> str:
```

Contrato abstracto; el propósito de parámetros y retorno corresponde a `UploadedFile.extension` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `str`.

#### IUploadedFile.write

```python
@abstractmethod
def write(self, chunk: bytes | bytearray | memoryview) -> None:
```

Parámetros:

- `chunk` (`bytes | bytearray | memoryview`): Secuencia de bytes que se escribirá.

Contrato abstracto; el propósito de parámetros y retorno corresponde a `UploadedFile.write` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `None`.

#### IUploadedFile.read

```python
@abstractmethod
def read(self) -> bytes:
```

Contrato abstracto; el propósito de parámetros y retorno corresponde a `UploadedFile.read` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `bytes`.

#### IUploadedFile.chunks

```python
@abstractmethod
def chunks(self, size: int = 65536) -> Iterator[bytes]:
```

Parámetros:

- `size` (`int`): Máximo de bytes solicitados por lectura.

Contrato abstracto; el propósito de parámetros y retorno corresponde a `UploadedFile.chunks` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `Iterator[bytes]`.

#### IUploadedFile.replace

```python
@abstractmethod
def replace(self, data: bytes) -> None:
```

Parámetros:

- `data` (`bytes`): Bytes de reemplazo.

Contrato abstracto; el propósito de parámetros y retorno corresponde a `UploadedFile.replace` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `None`.

#### IUploadedFile.save

```python
@abstractmethod
def save(self, path: str | Path) -> None:
```

Parámetros:

- `path` (`str | Path`): Destino en el sistema de archivos.

Contrato abstracto; el propósito de parámetros y retorno corresponde a `UploadedFile.save` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `None`.

#### IUploadedFile.close

```python
@abstractmethod
def close(self) -> None:
```

Contrato abstracto; el propósito de parámetros y retorno corresponde a `UploadedFile.close` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `None`.

<a id="api-088"></a>

### IMultipartPart

Fuente: [contracts/part.py](../payload/contracts/part.py).

```python
class IMultipartPart(ABC):
```

Contrato `ABC` de acumulación y finalización de partes multipart; implementado por `MultipartPart`. Todos los miembros listados son abstractos y la clase usa `__slots__ = ()`. Instanciarla con métodos abstractos sin resolver lanza `TypeError`. No define constructor.

#### IMultipartPart.write

```python
@abstractmethod
def write(self, chunk: bytes | bytearray | memoryview) -> None:
```

Parámetros:

- `chunk` (`bytes | bytearray | memoryview`): Secuencia de bytes que se escribirá.

Contrato abstracto; el propósito de parámetros y retorno corresponde a `MultipartPart.write` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `None`.

#### IMultipartPart.finalize

```python
@abstractmethod
def finalize(self) -> UploadedFile | str:
```

Contrato abstracto; el propósito de parámetros y retorno corresponde a `MultipartPart.finalize` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `UploadedFile | str`.

<a id="api-089"></a>

### IMultipartStreamParser

Fuente: [contracts/stream_parser.py](../payload/contracts/stream_parser.py).

```python
class IMultipartStreamParser(ABC):
```

Contrato `ABC` de análisis multipart asíncrono; implementado por `MultipartStreamParser`. Todos los miembros listados son abstractos y la clase usa `__slots__ = ()`. Instanciarla con métodos abstractos sin resolver lanza `TypeError`. No define constructor.

#### IMultipartStreamParser.parse

```python
@abstractmethod
async def parse(self) -> FormData:
```

Contrato abstracto; el propósito de parámetros y retorno corresponde a `MultipartStreamParser.parse` descrito arriba. La anotación se reproduce literalmente. El cuerpo contiene solo su docstring y no aporta implementación concreta.

Efectos concretos y excepciones adicionales:

> ⚠️ No especificado en el código fuente

Tipo declarado de retorno/iteración: `FormData`.

<a id="api-090"></a>

### TransportAdapter

Fuente: [adapters/request/contracts/transport.py](../adapters/request/contracts/transport.py).

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

Contrato abstracto de transporte de petición con `__slots__` (`ABC`). Sus diez métodos son `@abstractmethod`; instanciar la clase o una subclase incompleta lanza `TypeError`. Los cuerpos solo contienen docstrings: no leen ni modifican un transporte por sí mismos.

| Método | Parámetros y resultado declarado |
| --- | --- |
| `client` | Sin argumentos; dirección remota como `str \| None`. |
| `setClient` | `ip: str`, dirección nueva; devuelve `None`. |
| `scheme` | Sin argumentos; esquema de URL como `str \| None`. |
| `setScheme` | `value: str`, esquema nuevo; devuelve `None`. |
| `method` | Sin argumentos; método HTTP como `str \| None`. |
| `path` | Sin argumentos; ruta de petición como `str \| None`. |
| `headers` | Sin argumentos; `Headers` de la petición. |
| `setState` | `key: str`, nombre del estado; `value: Any`, valor almacenado; devuelve `None`. |
| `wantsJson` | Sin argumentos; preferencia JSON como `bool`. |
| `getScope` | Sin argumentos; representación del scope con sobrescrituras como `dict`. |

Efectos concretos, condiciones de error y almacenamiento más allá de estas declaraciones abstractas:

> ⚠️ No especificado en el código fuente

<a id="api-091"></a>

### ASGITransportAdapter

Fuente: [adapters/request/asgi.py](../adapters/request/asgi.py).

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

Envuelve por referencia el `scope: dict` recibido, construye `Headers` decodificando pares de bytes con Latin-1 e inicializa sobrescrituras y cachés por instancia. Si falta `headers`, usa una secuencia vacía. Implementa `TransportAdapter` con cinco slots.

| Método | Parámetros, resultado y cambios de estado |
| --- | --- |
| `__getitem__` | `key: str`, nombre de sobrescritura; devuelve su valor `object` o `None`, sin consultar el scope original. |
| `__setitem__` | `key: str` y `value: object`; guarda una sobrescritura, devuelve `None`. |
| `__contains__` | `key: str`; devuelve `bool` según la presencia únicamente en las sobrescrituras. |
| `__delitem__` | `key: str`; elimina la sobrescritura si existe, devuelve `None`; una clave ausente no lanza `KeyError`. |
| `client` | Sin argumentos; obtiene y almacena en caché la dirección (`str \| None`), y guarda sobrescrituras `client` y `port` entero cuando existen. |
| `setClient` | `ip: str`; actualiza la caché de dirección y la sobrescritura `client`, devuelve `None`; no actualiza `port`. |
| `scheme` | Sin argumentos; `str \| None` desde una sobrescritura distinta de `None` o desde el scope original. |
| `setScheme` | `value: str`; sobrescribe el esquema, devuelve `None`. |
| `method` | Sin argumentos; `str \| None` desde una sobrescritura distinta de `None` o desde el scope original. |
| `path` | Sin argumentos; `str \| None` leído directamente del scope original, ignorando las sobrescrituras. |
| `headers` | Sin argumentos; devuelve el objeto `Headers` creado y almacenado por el constructor. |
| `setState` | `key: str` y `value: Any`; guarda una sobrescritura, devuelve `None`. |
| `wantsJson` | Sin argumentos; almacena en caché un `bool` que indica si el último `Accept`, en minúsculas, contiene `application/json` o `+json`; valores ausentes/vacíos devuelven `False`. No interpreta factores de calidad. |
| `getScope` | Sin argumentos; devuelve un `dict` de campos originales más sobrescrituras, según se detalla abajo. |

El constructor y los métodos de escritura devuelven `None`. No realizan I/O ni usan locks explícitos. Escribir/eliminar sobrescrituras genéricas no sincroniza las cachés dedicadas de cliente o JSON: `setClient` sí sincroniza la dirección. Sobrescribir headers no reconstruye `headers()`. Salvo los errores de lectura del scope/headers indicados abajo, estos métodos no contienen `raise` explícitos.

`client()` espera que `scope["client"]` sea un par `(host, port)`; valores falsos/ausentes devuelven `None`. Un par inválido puede lanzar `IndexError`/`TypeError`, e `int(port)` puede lanzar `ValueError`/`TypeError`. Los headers cuyos elementos no ofrecen `.decode()` compatible con bytes lanzan `AttributeError`; desempaquetar pares inválidos puede lanzar `ValueError`.

`getScope()` devuelve **el propio diccionario original** mientras no haya sobrescrituras; después crea un diccionario combinado superficial. El adaptador no modifica directamente el diccionario recibido, pero quien obtiene esa referencia puede hacerlo. Consultar `client()` puede crear sobrescrituras y cambiar el comportamiento posterior de `getScope()`.

<a id="api-092"></a>

### RSGITransportAdapter

Fuente: [adapters/request/rsgi.py](../adapters/request/rsgi.py).

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

Envuelve por referencia un `scope: Scope` de Granian. El constructor recorre `scope.headers`, aplana cada colección `get_all(key)` en pares de nombre en minúsculas/valor, construye `Headers` e inicializa cinco slots para scope, headers, sobrescrituras y cachés.

| Método | Parámetros, resultado y cambios de estado |
| --- | --- |
| `__getitem__` | `key: str`, nombre de sobrescritura; devuelve su valor `object` o `None`, sin consultar el scope original. |
| `__setitem__` | `key: str` y `value: object`; guarda una sobrescritura, devuelve `None`. |
| `__contains__` | `key: str`; devuelve `bool` según la presencia únicamente en las sobrescrituras. |
| `__delitem__` | `key: str`; elimina la sobrescritura si existe, devuelve `None`; una clave ausente no lanza `KeyError`. |
| `client` | Sin argumentos; obtiene y almacena en caché la dirección (`str \| None`), y guarda sobrescrituras `client` y `port` entero cuando existen. |
| `setClient` | `ip: str`; actualiza la caché de dirección y la sobrescritura `client`, devuelve `None`; no actualiza `port`. |
| `scheme` | Sin argumentos; `str \| None` desde una sobrescritura distinta de `None` o desde el scope original. |
| `setScheme` | `value: str`; sobrescribe el esquema, devuelve `None`. |
| `method` | Sin argumentos; `str \| None` desde una sobrescritura distinta de `None` o desde el scope original. |
| `path` | Sin argumentos; `str \| None` leído directamente del scope original, ignorando las sobrescrituras. |
| `headers` | Sin argumentos; devuelve el objeto `Headers` creado y almacenado por el constructor. |
| `setState` | `key: str` y `value: Any`; guarda una sobrescritura, devuelve `None`. |
| `wantsJson` | Sin argumentos; almacena en caché un `bool` que indica si el último `Accept`, en minúsculas, contiene `application/json` o `+json`; valores ausentes/vacíos devuelven `False`. No interpreta factores de calidad. |
| `getScope` | Sin argumentos; devuelve un `dict` de campos originales más sobrescrituras, según se detalla abajo. |

El constructor y los métodos de escritura devuelven `None`. No realizan I/O ni usan locks explícitos. Escribir/eliminar sobrescrituras genéricas no sincroniza las cachés dedicadas de cliente o JSON: `setClient` sí sincroniza la dirección. Sobrescribir headers no reconstruye `headers()`. Salvo los errores de lectura del scope/headers indicados abajo, estos métodos no contienen `raise` explícitos.

`client()` divide la cadena `scope.client` por el último signo de dos puntos, elimina los corchetes IPv6 que rodean el host y convierte el componente final a `int`; valores falsos devuelven `None`. Por ejemplo, `[::1]:8000` produce cliente `::1` y puerto `8000`, permitiendo comprobar la dirección contra redes de proxies confiables. El análisis IPv4, la caché diferida y las sobrescrituras de `setClient` conservan el comportamiento descrito arriba. La falta de separador o un puerto no numérico lanza `ValueError`; atributos del scope/métodos de headers ausentes lanzan `AttributeError`.

`getScope()` siempre crea un diccionario con exactamente los campos base `proto`, `http_version`, `rsgi_version`, `server`, `client`, `scheme`, `method`, `path`, `query_string`, `authority` y `headers`, y aplica las sobrescrituras. Antes de resolver el cliente, `client` es la cadena original de host/puerto; después es la dirección en caché y se añade `port`.

<a id="api-093"></a>

### ResponseAdapter

Fuente: [adapters/response/contracts/response.py](../adapters/response/contracts/response.py).

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

`ABC` abstracta con slots para enviar respuestas. `send` recibe `adapter: TransportAdapter` para método/headers de petición, `response: Response` para enviar y `*args: object` / `**kwargs: object` específicos del protocolo. Su resultado asíncrono declarado es `None`. Instanciar esta clase o una subclase que mantenga `send` abstracto lanza `TypeError`.

El cuerpo abstracto solo contiene el docstring. I/O, excepciones y mutación de respuesta específicos del protocolo:

> ⚠️ No especificado en el código fuente

<a id="api-094"></a>

### ASGIResponseAdapter

Fuente: [adapters/response/asgi.py](../adapters/response/asgi.py).

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

`ResponseAdapter` sin estado con `__slots__ = ()`, `RESPONSE_START = "http.response.start"` y `RESPONSE_BODY = "http.response.body"`.

Parámetros de `send`: `adapter: TransportAdapter` aporta método y header de rango; `response: Response` aporta estado, headers, cuerpo/stream y tareas de fondo; `_receive: Callable[..., Awaitable[dict]]` se acepta pero no se usa; `send: Callable[..., Awaitable[None]]` recibe diccionarios de mensajes ASGI. Al esperarlo devuelve `None`.

Sobrescribe el header `server` de la respuesta con `Orionis ASGI`. Un `HEAD` exacto envía el inicio y un cuerpo final vacío, añadiendo content length al envío para archivo o cuerpo en memoria cuando falta. En HEAD no recorre el stream ni procesa rangos. Otras peticiones envían bytes en memoria, o inicio/chunks con `more_body=True` y un cuerpo final vacío. Si el iterador tiene `aclose()`, lo espera en `finally`.

Para `FileResponse`, un único rango válido cambia el estado enviado a 206 y reemplaza los headers enviados `content-length`, `content-range` y `accept-ranges`; no cambia a 206 el estado del objeto respuesta. El iterador privado de rango lee `[start, end)` en chunks de hasta `64 * 1024`, delega apertura/lectura/cierre al ejecutor del loop activo y cierra el archivo en `finally`. Rangos inválidos/no satisfacibles usan el envío completo; no se genera un 416.

Tras un envío exitoso espera `response.runBackground()`. Se propagan excepciones del envío, stream, cierre del iterador, archivo o tareas de fondo; si falla el envío/cierre, no se ejecutan las tareas de fondo. Headers de respuesta fuera de Latin-1 lanzan `UnicodeEncodeError` en `getRawHeaders()`. Las operaciones de archivo pueden lanzar subclases de `OSError`; la cancelación se propaga según los helpers descritos abajo. Realiza I/O mediante el callback y modifica los headers de respuesta; los headers añadidos para HEAD/rango pertenecen a la lista enviada.

<a id="api-095"></a>

### RSGIResponseAdapter

Fuente: [adapters/response/rsgi.py](../adapters/response/rsgi.py).

```python
class RSGIResponseAdapter(ResponseAdapter):

    async def send(
        self,
        adapter: TransportAdapter,
        response: Response,
        protocol: HTTPProtocol,
    ) -> None:
```

`ResponseAdapter` sin estado (`__slots__ = ()`). `send` recibe `adapter: TransportAdapter` para consultar método/rango, `response: Response` para transmitir y `protocol: HTTPProtocol` de Granian; al esperarlo devuelve `None`.

Sobrescribe `server` con `Orionis RSGI`, obtiene pares de headers de cadenas y usa `protocol.response_empty` para HEAD exacto (añadiendo content length de archivo/cuerpo en memoria cuando falta), `response_file_range(206, ..., start, end)` para rango de archivo válido, `response_file` para otros archivos, `response_stream` y `transport.send_bytes` esperado para streams, y `response_bytes`/`response_empty` para cuerpos no vacíos/vacíos. Procesa archivos antes que streams. El final del rango es exclusivo; rangos inválidos envían el archivo completo. Headers/estado de rango cambian los argumentos enviados, no el estado del objeto respuesta.

Los streams se cierran mediante `aclose()` esperado en `finally` cuando existe. Cada ruta exitosa espera después `response.runBackground()`; se propagan errores del protocolo/stream/cierre/tareas de fondo y un fallo previo omite las tareas de fondo. Granian realiza el envío de archivos; este adaptador no hace lecturas de archivo mediante el ejecutor de Python. Modifica el header server de la respuesta y realiza I/O del protocolo.

<a id="api-096"></a>

### open_file

Fuente: [adapters/response/files.py](../adapters/response/files.py).

```python
async def open_file(path: Path, start: int = 0) -> BinaryIO:
```

`path: Path` identifica el archivo abierto con `path.open("rb")`; `start: int = 0` es el desplazamiento en bytes, enviado a `seek` solo cuando es verdadero. Devuelve el `BinaryIO` abierto y posicionado. En el flujo normal, quien llama se responsabiliza del cierre.

La apertura/posicionamiento ocurre en el ejecutor predeterminado del loop asyncio actual. `asyncio.shield` evita que cancelar la tarea que espera cancele el future de apertura; ante `asyncio.CancelledError`, espera la apertura, cierra el archivo resultante en el ejecutor y relanza. Un `OSError` durante seek cierra el archivo y se propaga. Pueden propagarse errores de apertura/seek/cierre, incluidos `FileNotFoundError`/`PermissionError`; un fallo de limpieza durante la cancelación puede reemplazarla. Realiza I/O de archivo y usa un hilo trabajador.

<a id="api-097"></a>

### complete_file_read

Fuente: [adapters/response/files.py](../adapters/response/files.py).

```python
async def complete_file_read(pending: Future[bytes]) -> bytes:
```

`pending: Future[bytes]` es un future de lectura en un trabajador ya programado. Devuelve su resultado `bytes`, esperándolo mediante `asyncio.shield`. Si se cancela quien llama, espera `pending` antes de relanzar `asyncio.CancelledError`, evitando cerrar el lector mientras esa lectura siga pendiente. Los errores del future se propagan y pueden reemplazar la cancelación durante la limpieza. No programa lecturas ni cierra archivos por sí mismo.

<a id="api-098"></a>

### parse_range

Fuente: [adapters/response/ranges.py](../adapters/response/ranges.py).

```python
def parse_range(value: str | None, file_size: int) -> tuple[int, int] | None:
```

`value: str | None` es el header Range; `file_size: int` es el tamaño en bytes. Devuelve `(start, end)` como `tuple[int, int]` con `end` exclusivo, o `None` para valores ausentes, inválidos o no satisfacibles. Acepta exactamente `bytes=start-end`, `bytes=start-` y `bytes=-suffix` en minúsculas; los componentes numéricos deben ser dígitos decimales ASCII. Limita el final explícito al tamaño del archivo; sufijos mayores que el archivo lo abarcan completo. Rechaza archivos vacíos, sufijo cero, rangos múltiples, espacios y otras unidades. Captura `ValueError` de conversión numérica y no tiene I/O ni estado mutable; no escapa ninguna excepción explícita para los tipos anotados.

<a id="api-099"></a>

### IBaseMiddleware

Fuente: [layer/contracts/middleware.py](../layer/contracts/middleware.py).

```python
class IBaseMiddleware(ABC):

    @abstractmethod
    async def handle(
        self,
        request: Request,
        call_next: NextCallable,
    ) -> Response:
```

`ABC` abstracta con slots para middleware de aplicación por capas. `handle` recibe `request: Request` y `call_next: NextCallable`, callable sin argumentos que devuelve un `Response` esperable; su resultado asíncrono declarado es `Response`. El módulo define `NextCallable = Callable[[], Awaitable["Response"]]`. La instanciación directa/implementación incompleta lanza `TypeError`; el cuerpo abstracto es solo un docstring.

Tratamiento concreto de errores, mutación de petición y decisión de invocar el siguiente handler:

> ⚠️ No especificado en el código fuente

<a id="api-100"></a>

### MemoryRateLimitStore

Fuente: [layer/store/memory_rate_limit.py](../layer/store/memory_rate_limit.py).

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

Ventana deslizante en memoria por instancia de intentos **aceptados**. `__init__` no recibe argumentos, crea almacenamiento vacío mediante diccionario/deque y un contador de ticks en cero, y devuelve `None`. `_GC_INTERVAL: int = 16` y `_GC_BATCH_SIZE: int = 64` controlan la limpieza incremental.

Parámetros de `hit`: `key: str`, identificador de entidad; `limit: int`, máximo de intentos aceptados; `window: int`, segundos de la ventana. Devuelve `bool`: `False` si `limit <= 0` o se agotó la ventana; en otro caso registra el timestamp actual de `monotonic()` y devuelve `True`. Descarta timestamps aceptados `<= now - window`; los rechazos no entran en el deque de timestamps. Cada 16 intentos, incluidos rechazos, `__gc` privado revisa hasta 64 claves y elimina buckets vencidos. Su dataclass privada con slots `_RateLimitBucket` almacena `expires_at: float` y `timestamps: deque[float]`, con una nueva deque por defecto.

`hit` no contiene puntos `await`, por lo que llamadas en un mismo event loop no se intercalan dentro del método. No hay locks entre hilos/procesos ni persistencia compartida. Cada clave debe usar una ventana consistente; las llamadas directas no validan ventanas positivas ni tipos de entrada. No hay `raise` explícitos; tipos inválidos en operaciones/claves pueden propagar `TypeError`. La memoria crece con claves y timestamps aceptados retenidos; la limpieza ocurre solo con llamadas posteriores, sin temporizador.

<a id="api-101"></a>

### RateLimitMiddleware

Fuente: [layer/shared/rate_limit.py](../layer/shared/rate_limit.py).

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

`__init__` recibe `config: dict`, expandido en `HTTPRateLimit`, y `default_responses: IDefaultResponses`, constructor de errores; devuelve `None`. Las claves son `rate_limit_enabled: bool`, `rate_limit_requests: int` y `rate_limit_window_seconds: int`. Sus valores predeterminados leen `RATE_LIMIT_ENABLED` (respaldo `False`), `RATE_LIMIT_REQUESTS` (`100`) y `RATE_LIMIT_WINDOW` (`60`) mediante `Env`. Tipos inválidos/claves desconocidas lanzan `TypeError`; límites/ventanas no positivos y conversiones a entero fallidas del entorno lanzan `ValueError`. Crea `MemoryRateLimitStore` privado solo cuando está activo y precalcula `Retry-After` como toda la ventana configurada.

`isEnabled()` no recibe argumentos y devuelve el flag `bool` almacenado. `handle(adapter: TransportAdapter)` devuelve `Response | None` al esperarlo: limitación desactivada, IP de cliente ausente/falsa e intento aceptado devuelven `None`; un rechazo devuelve `default_responses.error(status_code=429, content="Too Many Requests", expects_json=adapter.wantsJson(), headers={"Retry-After": ...})`. La clave de cuota es únicamente la IP. Modifica el store, propaga errores del adaptador/store/respuestas predeterminadas y no tiene `raise` explícitos. `Retry-After` no se calcula desde el timestamp aceptado más antiguo.

<a id="api-102"></a>

### CORSException

Fuente: [layer/shared/cors.py](../layer/shared/cors.py).

```python
class CORSException(Exception):
```

Subclase directa de `Exception` cuyo cuerpo es una elipsis, sin constructor, campos ni métodos propios. `CORSMiddleware.__init__` la lanza si `allow_credentials` es verdadero y `allow_origins` contiene `"*"`. Hereda de `Exception` sus argumentos/comportamiento; el módulo no define API adicional para la excepción.

<a id="api-103"></a>

### CORSMiddleware

Fuente: [layer/shared/cors.py](../layer/shared/cors.py).

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

`__init__(config: dict)` construye `Cors(**config)`, normaliza y prepara valores de configuración, y devuelve `None`. Campos/valores predeterminados: `allow_origins: list[str] = []`, `allow_origin_regex: str | None = None`, `allow_methods: list[str] = []`, `allow_headers: list[str] = []`, `expose_headers: list[str] = []`, `allow_credentials: bool = False`, `max_age: int | None = 600`. La constante de métodos comodín es `ALL_METHODS: Final[str] = "DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT"`. Los métodos explícitos se convierten a mayúsculas; los nombres de headers permitidos/expuestos, a minúsculas; se eliminan barras finales de los orígenes. La coincidencia usa origen normalizado exacto o `re.Pattern.match`, no coincidencia total.

Excepciones del constructor: `CORSException` por credenciales con origen comodín; `TypeError` por campos desconocidos/tipos inválidos; `ValueError` por métodos rechazados por `Cors`; `re.PatternError` por expresiones regulares inválidas. El conjunto de métodos explícitos de la entidad omite `HEAD`, aunque la expansión del comodín sí lo contiene. Elementos inválidos de listas que superen la validación de la entidad también pueden lanzar `AttributeError` al normalizar cadenas.

`before(adapter: TransportAdapter)` devuelve `Response | None`: si hay Origin, método OPTIONS (normalizado cuando hace falta), presencia de `Access-Control-Request-Method` y origen permitido, crea una respuesta 204. Los demás casos devuelven `None`, incluidos orígenes rechazados. Anuncia los métodos/headers configurados, pero no comprueba los nombres solicitados contra esas listas. Con headers comodín refleja un `Access-Control-Request-Headers` no vacío y añade ese nombre a `Vary`; en otro caso usa el literal `*`. Añade credenciales y max-age cuando corresponde.

`after(adapter: TransportAdapter, response: Response)` devuelve el mismo `Response`, aplicando origen, credenciales y headers expuestos cuando hay Origin permitido. No comprueba si la petición es preflight. Orígenes específicos/con credenciales se reflejan y se combinan en `Vary: origin`; orígenes sin restricciones usan `*`. Conserva Vary existente sin añadir directivas duplicadas según comparación insensible a mayúsculas. Ambos métodos modifican headers, no realizan I/O y propagan errores del adaptador/respuesta sin `raise` explícitos.

<a id="api-104"></a>

### SecurityMiddleware

Fuente: [layer/shared/security.py](../layer/shared/security.py).

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

`__init__` recibe `config: dict`, expandido en `HTTPSecurity`, y `default_responses: IDefaultResponses` para rechazos, y devuelve `None`. `allowed_hosts: list[str] | Literal["*"]` tiene valor predeterminado `[]`; campos desconocidos, valores que no sean lista/`"*"` y elementos no string lanzan `TypeError`. Recorta espacios y pasa hosts a minúsculas; ignora entradas vacías. `*.example.com` admite tanto `example.com` como subdominios con ese sufijo. La cadena literal `"*"`, lista vacía o entradas solo de espacios desactivan la lista permitida; una lista que contiene `"*"` lo trata como host exacto.

`handle(adapter: TransportAdapter)` devuelve `Response | None`. En orden, rechaza CR/LF en nombres/valores de headers con 400 `Invalid header format.`, múltiples Host con 400 `Multiple Host headers not allowed.` y después Host ausente/no permitido con lista activa con 400 `Host header not allowed.`. Para comparar Host recorta espacios, pasa a minúsculas, elimina el puerto final y extrae IPv6 entre corchetes. Las respuestas usan `adapter.wantsJson()`; el éxito devuelve `None`. Las dos primeras comprobaciones siempre están activas. No modifica la petición ni realiza I/O; propaga errores del adaptador/respuestas predeterminadas y `handle` no lanza excepciones explícitas.

<a id="api-105"></a>

### ProxiesMiddleware

Fuente: [layer/shared/proxies.py](../layer/shared/proxies.py).

```python
class ProxiesMiddleware:

    def __init__(
        self,
        config: dict,
    ) -> None:

    def handle(self, adapter: TransportAdapter) -> TransportAdapter:
```

`__init__(config: dict)` construye `HTTPProxies`, compila redes de confianza y devuelve `None`. `trusted_proxies: list[str]` usa por defecto `Env.get("TRUSTED_PROXIES", [])`. Campos desconocidos/valores que no sean lista/elementos no string lanzan `TypeError`; IP/CIDR inválidos lanzan `ValueError` de `ip_network(..., strict=False)`. El token exacto `private` se expande únicamente a IPv4 `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12` y `192.168.0.0/16`. Sin redes se desactiva el procesamiento. Las constantes son `_IP_HEADER = "x-forwarded-for"` y `_PROTO_HEADER = "x-forwarded-proto"`.

`handle(adapter: TransportAdapter)` devuelve el mismo `TransportAdapter`. Solo modifica peticiones cuyo cliente actual sea una IP válida de una red confiable. Divide todos los valores X-Forwarded-For por comas y descarta direcciones inválidas/vacías. De derecha a izquierda selecciona la primera IP no confiable; si todas son confiables, elige la izquierda. Sin cadena válida conserva el cliente actual. `proxies` contiene todas las cadenas distintas del cliente seleccionado, no solo el sufijo confiable; no añade automáticamente el peer directo a una cadena válida.

Invoca `setClient`, opcionalmente `setScheme` si el primer valor completo de X-Forwarded-Proto, recortado y en minúsculas, es `http` o `https`, y después `setState("forwarded", {"client": real_ip, "proxies": proxies, "chain": chain})`. No acepta listas de protocolos separadas por comas. Captura como `ValueError` e ignora direcciones reenviadas inválidas. Los errores del adaptador se propagan; `handle` no tiene `raise` explícitos ni I/O, y modifica sobrescrituras/caché del scope.

<a id="api-106"></a>

### UnderMaintenanceMiddleware

Fuente: [layer/shared/maintenance.py](../layer/shared/maintenance.py).

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

`__init__` exige argumentos por nombre `under_maintenance: bool`, flag de mantenimiento almacenado, y `default_responses: IDefaultResponses`, fábrica de respuestas; devuelve `None` y no valida tipos.

`handle(adapter: TransportAdapter)` usa la preferencia JSON del adaptador y devuelve `Response | None`: flag falso devuelve `None`; de lo contrario invoca la fábrica con estado 503 y contenido `The application is currently under maintenance.`. El flag se fija en la construcción y se evalúa por veracidad. No hay I/O directo ni mutación de petición; no hay `raise` explícitos y se propagan errores del adaptador/fábrica.

<a id="api-107"></a>

### StartSessionMiddleware

Fuente: [layer/web/start_session.py](../layer/web/start_session.py).

```python
class StartSessionMiddleware(BaseMiddleware):

    def __init__(self, manager: SessionManager, catch: ICatch) -> None:

    async def handle(
        self,
        request: Request,
        call_next: Callable[[], Awaitable[Response]],
    ) -> Response:
```

Extiende `BaseMiddleware`; los slots `_manager` y `_catch` almacenan colaboradores inyectados. `__init__(manager: SessionManager, catch: ICatch)` guarda el gestor del ciclo de sesión y el handler que convierte errores a respuestas, y devuelve `None`.

`handle` recibe `request: Request` y `call_next: Callable[[], Awaitable[Response]]` asíncrono sin argumentos; al esperarlo devuelve el `Response` de salida. Espera `manager.start(request)`, escribe `request.state.session`, llama al siguiente handler, aplica `response.getFlashData()` no vacío mediante `orionis.session.flash.apply_flash`, registra URL según las reglas siguientes y espera `manager.save(response, session)`. El gestor puede añadir la cookie de sesión y realiza el I/O de persistencia configurado.

`__response` privado captura `Exception` de `call_next` y espera `catch.exception(exc, request)` mientras la sesión sigue disponible. Fallos `BaseException` posteriores dentro del bloque de procesamiento/guardado, incluidas cancelaciones y errores del handler de excepciones, esperan `manager.abort(session)` y se relanzan; un fallo de abort puede reemplazar el error original. `manager.start` y la asignación al estado ocurren antes de ese bloque protegido.

`__storeCurrentUrl` privado registra `request.url` solo para GET/HEAD exactos cuando ni `isAjax()` ni `wantsJson()` son verdaderos y `200 <= status < 300`. Los demás métodos, las peticiones AJAX/JSON y las respuestas fuera del rango 2xx conservan la URL previamente guardada. Modifica petición/sesión/respuesta y propaga errores de colaboradores; no define un tipo de excepción nuevo.

<a id="api-108"></a>

### CSRFTokenMismatchException

Fuente: [layer/web/exceptions.py](../layer/web/exceptions.py).

```python
class CSRFTokenMismatchException(Exception):
```

Subclase directa de `Exception`, sin constructor, campos ni métodos propios. `CSRFTokenMiddleware` la lanza por token inválido/ausente en cualquier método fuera de GET/HEAD/OPTIONS/TRACE, no solo los cuatro verbos no seguros enumerados en el docstring. `orionis.failure.base.handler` la asocia con `(419, "CSRF token mismatch")`. Hereda argumentos y comportamiento estándar de excepción; no crea una respuesta por sí misma.

<a id="api-109"></a>

### CSRFTokenMiddleware

Fuente: [layer/web/csrf_token.py](../layer/web/csrf_token.py).

```python
class CSRFTokenMiddleware(BaseMiddleware):

    def __init__(self, config: dict) -> None:

    async def handle(
        self,
        request: Request,
        call_next: Callable[[], Awaitable[Response]],
    ) -> Response:
```

Extiende `BaseMiddleware`. `__init__(config: dict)` expande campos en `HTTPCsrf`, almacena configuración y devuelve `None`. Valores predeterminados: `enabled=True`, `token_length=32` bytes aleatorios, `session_key="_csrf_token"`, `xsrf_cookie=False`, `cookie_name="XSRF-TOKEN"`, `cookie_secure=False`, `cookie_same_site="lax"`, `cookie_path="/"`, `cookie_domain=None`. Los tipos son, respectivamente, `bool`, `int`, `str`, `bool`, `str`, `bool`, `Literal["lax", "strict", "none"]`, `str` y `str | None`. Campos desconocidos y tipos validados inválidos lanzan `TypeError`; longitud menor de 32, clave de sesión/nombre de cookie inválidos o vacíos y SameSite no admitido lanzan `ValueError`. La entidad no valida explícitamente `cookie_secure`.

`handle` recibe `request: Request` y `call_next: Callable[[], Awaitable[Response]]`, siguiente handler asíncrono sin argumentos; al esperarlo devuelve su `Response`. Desactivado delega inmediatamente. De lo contrario, `__resolveToken` privado reutiliza un valor verdadero de la sesión o genera `secrets.token_urlsafe(token_length)` y lo guarda; sin `request.state.session` genera un token efímero sin persistencia. Publica `request.state.csrf_token` incluso para métodos seguros. Genera un token nuevo cuando el almacenado falta/es falso.

[Session.regenerate()](../../session/session.py) solicita rotar el ID conservando los datos de sesión, incluido el token CSRF almacenado. El [SessionGuard](../../auth/guards/session_guard.py) incluido reemplaza explícitamente ese token durante `login()` y actualiza `request.state.csrf_token`; `logout()` invalida la sesión y borra sus datos almacenados. El middleware crea un token cuando una sesión activa posterior carece de él.

Los métodos seguros exactos son GET, HEAD, OPTIONS y TRACE. Otros comprueban `x-csrf-token` antes de `x-xsrf-token`, recortando espacios de headers. Un primer header solo de espacios devuelve `None` sin probar el segundo; después intenta el cuerpo. Sin token de header, content type debe contener la subcadena sensible a mayúsculas `application/x-www-form-urlencoded` o `multipart/form-data`; espera `request.data()` y comprueba strings no vacíos `_csrf` y luego `csrf_token`, sin recortar valores de formulario. Los errores de `request.data()` se tratan como token ausente; ese `except Exception` no captura cancelación.

`secrets.compare_digest(token.encode(), submitted.encode())` verifica el valor. Token ausente/distinto lanza `CSRFTokenMismatchException` antes de `call_next`; otros errores de acceso a sesión, tipos de token almacenado incorrectos o handlers posteriores se propagan. No valida contra la cookie de petición.

Tras `call_next`, la cookie opcional usa nombre/path/domain/SameSite configurados, fija `http_only=False` y calcula `secure = cookie_secure or request.scheme == "https"`. Una sesión invalidada elimina la cookie; de lo contrario un token de sesión recién almacenado sustituye al previo para la cookie. Modifica petición/sesión/cookies de salida y puede leer el cuerpo; esta clase no implementa locks ni sincronización entre peticiones.

## Ejemplos de uso

Cada bloque de esta sección es un programa completo para Python 3.14+. Ejecútalo de forma independiente después de instalar Orionis y sus dependencias declaradas (o desde este checkout con esas dependencias disponibles). Estos ejemplos no necesitan servidor activo ni aplicación configurada.

### Construir una respuesta JSON

Usa la factoría pública, cabeceras y encadenado de cookies sin arrancar aplicación ni servidor.

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

### Leer una petición y manejar errores de parseo

Proporciona una entrada ASGI completa con adaptadores reales y límite explícito de cuerpo. Demuestra reutilización del cuerpo cacheado, JSON inválido, MIME no admitido y exceso de tamaño.

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

### Integrar tareas de fondo con envío ASGI

Integra `orionis.background.task.BackgroundTask`. El callable send local registra mensajes ASGI reales; la tarea finaliza después de entregar la respuesta.

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

### Compilar y resolver rutas

Crea una ruta sin acción inicial, la completa con `.action(UserController, "show")` y la compila con middleware. Resuelve HEAD implícito, maneja errores de búsqueda y serializa/restaura metadatos mediante RouteCache. Resolver devuelve metadatos; no ejecuta el handler ni el middleware.

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

### Parsear multipart y cerrar recursos

Parsea bytes multipart completos mediante la implementación real y cierra los recursos del formulario/archivo.

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
## Consideraciones de rendimiento y concurrencia

Los siguientes son límites/valores predeterminados de implementación, no resultados de benchmarks:

| Componente | Comportamiento verificado |
|---|---|
| `BodyStream` | `read()` almacena todo el cuerpo; `stream()` reproduce ese buffer si ya fue leído. El streaming directo consume el transporte una sola vez. El límite predeterminado se representa con `sys.maxsize`; `KernelHTTP` no configura un límite menor. |
| `MultipartStreamParser` | Valores predeterminados: 1000 archivos, 1000 campos, 10 MiB por parte, umbral de archivo en memoria de 1 MiB y 64 KiB de cabeceras por parte. No son un tope de memoria total de la petición. |
| Salida de archivos | `FileResponse` lee 64 KiB por defecto; los rangos ASGI también usan 64 KiB. El `stat()` del constructor es síncrono; las lecturas usan helpers con executor. RSGI delega el envío de archivos a Granian. |
| Rutas | Las rutas estáticas usan mappings; las dinámicas se indexan por cantidad de segmentos. Las resoluciones dinámicas exitosas usan caché FIFO de 512 entradas por defecto; cero la desactiva. Los aciertos no actualizan el orden de expulsión. |
| Rate limiting | Deques en memoria guardan timestamps aceptados; la limpieza revisa como máximo 64 claves cada 16 intentos. No hay tope global configurado de claves/memoria ni estado compartido entre procesos. |
| Páginas predeterminadas | El primer acceso HTML lee plantillas incluidas de forma síncrona; las cachés de instancia conservan bytes/plantillas/planes de sustitución. Las etiquetas de error usan un dict de módulo. |

`MemoryRateLimitStore.hit()` no contiene suspensión y su código limita la afirmación de atomicidad a un único event loop. Peticiones, lectores de cuerpo y parsers multipart contienen estado mutable de consumo; las cachés de rutas y respuestas predeterminadas no tienen locks de sincronización. El kernel cachea y reutiliza instancias de middleware, mientras el estado de continuación es por petición. No garantiza arranque concurrente ni uso general entre hilos.

Seguridad general entre hilos, rendimiento medido, latencia y límites globales de memoria:

> ⚠️ No especificado en el código fuente

Los helpers de archivos protegen operaciones de workers y esperan su finalización antes de propagar cancelación. Los fallos multipart limpian archivos activos/completados ante `BaseException`; un parseo exitoso transfiere la propiedad al formulario devuelto. Esto no establece garantías frente a cancelación repetida arbitraria o fallos de colaboradores de limpieza. La salida de iterables síncronos sigue iterando en el hilo del event loop. Las tareas de fondo se esperan tras el envío correcto; no se despachan como trabajo desacoplado.

## Notas de compatibilidad

El [pyproject.toml](../../../pyproject.toml) inspeccionado declara Orionis `0.756.0` y **Python >=3.14**. Algunos archivos sin `from __future__ import annotations` (por ejemplo `kernel.py` y middleware web) usan en anotaciones nombres importados solo bajo `TYPE_CHECKING`; las anotaciones diferidas de Python 3.14 permiten definirlos sin resolución anticipada en runtime. El código también usa alias `type`/parámetros de funciones genéricas, `Self`, `StrEnum`, `mimetypes.guess_file_type` y el atributo de cookie `Partitioned`. Esas características individuales anteriores no reducen el mínimo declarado. Evaluar anotaciones en runtime todavía puede requerir el namespace de tipos ausentes.

Imports directos de terceros y restricciones de dependencias declaradas por este checkout:

| Paquete | Restricción declarada | Uso |
|---|---|---|
| `msgspec` | `>=0.21.1` | Codificación/decodificación JSON/MessagePack; resultados `Struct` admitidos en handlers. |
| `defusedxml` | `>=0.7.1,<1.0` | Parser XML. |
| `granian[dotenv,pname,reload,uvloop,winloop]` | `>=2.8.3,<3.0` | Tipos/protocolo de transporte RSGI; los imports directos de HTTP están bajo `TYPE_CHECKING`. |

Estos paquetes ya son dependencias del proyecto que instala `pip install orionis`; no se declara requisito de instalación ni extra HTTP separado. Las versiones anteriores son rangos declarados, no afirmaciones sobre versiones instaladas. Los servicios internos tienen sus propias dependencias y configuración; importar la raíz `orionis` también carga infraestructura de aplicación.

Comportamientos relevantes al integrar esta revisión:

- `json()` acepta `+json`, mientras `data()` solo acepta sus cuatro MIME exactos; los helpers de Accept buscan subcadenas y no respetan factores de calidad.
- Los verbos de Router y `FluentRoute` admiten acciones omitidas/`None` para asignarlas después con `.action(...)`; exportar una ruta incompleta lanza `ValueError`. `fallback(action)` exige un manejador inmediato y no devuelve un constructor. HEAD se resuelve con GET; el descubrimiento OPTIONS es separado.
- Los rangos de archivo inválidos/no admitidos producen envío completo en los adaptadores, sin generar respuesta 416.
- El middleware de sesión guarda URL previa solo para respuestas GET/HEAD con estado 2xx y excluye peticiones AJAX y JSON.
- `RegisterController` requiere modelo de usuario de aplicación, servicios de base de datos/hash configurados y vistas de aplicación. `Router.auth()` carga esos controladores de forma diferida.
- Los nombres públicos como `estructures`, `httpVersion`, `formUrlEncoded`, `robotsTxt` y `noContent` conservan su escritura en el código.
- `WebSocketStatus` enumera códigos de cierre; el kernel HTTP no proporciona API de despacho WebSocket.
