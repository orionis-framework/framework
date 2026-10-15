# Middleware y políticas de seguridad

Un middleware HTTP recibe `Request` y una función sin argumentos para avanzar. Puede devolver una respuesta antes del controlador o modificarla después. Adjunta clases a rutas; el kernel puede reutilizar sus instancias entre solicitudes.

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

Registra con `.middleware(RequestIdMiddleware)`. No guardes el identificador en `self`. Cada continuation puede llamarse una sola vez: dos llamadas a `call_next()` generan `RuntimeError`. Para cortocircuitar devuelve directamente una respuesta. Usa `try/finally` si abres recursos; la cancelación también debe limpiarlos.

## Sesión y CSRF

El pipeline web restaura sesión, comprueba CSRF y resuelve identidad, en ese orden. Los métodos GET, HEAD, OPTIONS y TRACE son seguros para la comprobación CSRF. Los demás requieren el token en `X-CSRF-Token`, `X-XSRF-Token`, `_csrf` o `csrf_token` de formulario. En JSON utiliza la cabecera; no se busca un token arbitrario dentro de JSON.

`request.csrfToken()` obtiene el token preparado por middleware. `CSRF_ENABLED` es verdadero por defecto; el token utiliza `CSRF_TOKEN_LENGTH=32` bytes aleatorios. Las opciones `CSRF_SESSION_KEY`, `CSRF_XSRF_COOKIE`, `CSRF_COOKIE_NAME`, `CSRF_COOKIE_SECURE`, `CSRF_COOKIE_SAME_SITE`, `CSRF_COOKIE_PATH` y `CSRF_COOKIE_DOMAIN` ajustan almacenamiento y cookie. La cookie XSRF es accesible a scripts por diseño; no es la cookie de sesión. Desactivar CSRF o usar `public()` en un endpoint con cookies elimina una protección necesaria.

## Hosts, proxies y CORS

`ALLOWED_HOSTS` vacío permite cualquier host; configúralo para despliegues que dependan del nombre público. La capa de seguridad rechaza encabezados con CR/LF y múltiples Host. `TRUSTED_PROXIES` establece qué peers pueden modificar esquema/IP mediante forwarded headers; el bootstrap confía en localhost. Confía solo en tus proxies para que rate limits y URLs no dependan de cabeceras falsificadas.

Las direcciones de proxies de un solo host se indexan al inicializar el middleware, evitando repetir el análisis de IP cuando el peer coincide exactamente. Los rangos CIDR y las formas equivalentes de IPv6 conservan la validación de red. Los saltos forwarded se analizan y comprueban en cada petición; no se cachean metadatos de solicitudes ni decisiones de confianza.

CORS configura `CORS_ALLOW_ORIGINS`, `CORS_ALLOW_ORIGIN_REGEX`, `CORS_ALLOW_METHODS`, `CORS_ALLOW_HEADERS`, `CORS_EXPOSE_HEADERS`, `CORS_ALLOW_CREDENTIALS` y `CORS_MAX_AGE` (600 segundos). Las credenciales están desactivadas por defecto. Declara orígenes concretos cuando uses cookies. CORS es una política del navegador, no autenticación del servidor. WebSocket y MCP leen el mismo `CORS_ALLOW_ORIGINS` en bootstrap pero validan con reglas propias; MCP rechaza wildcards.

## Capacidad y rate limiting

`RATE_LIMIT_ENABLED` es falso por defecto. Al habilitarlo, el presupuesto inicial es 100 peticiones por 60 segundos (`RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW`). La clave es la IP resuelta del cliente. `RATE_LIMIT_STORE` elige memoria local o Redis. `RATE_LIMIT_MAX_KEYS` y `RATE_LIMIT_MAX_EVENTS` acotan memoria; `RATE_LIMIT_REDIS_PREFIX` y `RATE_LIMIT_REDIS_TIMEOUT` configuran Redis. La conexión comparte `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB` y `REDIS_PASSWORD`.

Un exceso produce 429 con `Retry-After`; un error de Redis reconocido produce 503 y un reintento corto. La memoria es local al worker y no limita una cuota global. El límite de concurrencia HTTP cubre también la entrega de respuesta y rechaza sobrecarga en vez de acumular una cola ilimitada.

Evidencia: [kernel](../../kernel.py), [CSRF](../../layer/web/csrf_token.py), [proxies](../../layer/shared/proxies.py), [rate limit](../../layer/shared/rate_limit.py), [config](../../../../config/http.py). Pruebas: [pipeline](../../../../tests/http/test_middleware.py), [seguridad](../../../../tests/http/layer/shared/test_security.py), [proxies](../../../../tests/http/layer/shared/test_proxies.py), [CORS](../../../../tests/http/layer/shared/test_cors.py), [CSRF](../../../../tests/http/layer/web/test_csrf_token.py). Protección por identidad: [Auth](../../../auth/docs/es/README.md).
