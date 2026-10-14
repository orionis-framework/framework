# Ciclo de petición y controladores

Una petición entra por un adaptador ASGI o RSGI. El kernel aplica políticas globales, resuelve la ruta compilada, abre el scope del contenedor y construye el pipeline correspondiente. El controlador trabaja con `Request`, servicios inyectados y respuestas independientes del servidor. Al finalizar se persiste la sesión cuando corresponde, se envía la respuesta y se liberan cuerpos, archivos y servicios del scope.

## Un controlador de lectura

```python
from orionis.http import Request, Response, response
from orionis.http.base.controller import BaseController

class CatalogController(BaseController):
    async def show(self, request: Request) -> Response:
        product_id = request.routeParam("product_id")
        return response.json({"id": product_id, "currency": "USD"})
```

En `routes/api.py`, registra `Route.get("/products/{product_id:int}", [CatalogController, "show"])` importando `Route` desde `orionis.support.facades`. La clase debe ser importable desde un módulo real de tu aplicación. `BaseController` es un marcador vacío: no proporciona métodos de autorización, validación ni acceso al ORM. Esas tareas pertenecen a sus servicios.

También puedes registrar una función o una clase con `__call__`. Para completar una declaración diferida usa `Route.get("/products").action(CatalogController, "show")` antes de compilar las rutas. El método y su información de tipos se inspeccionan durante el arranque; las dependencias del controlador se construyen mediante el contenedor.

## Elegir web o API

El loader importa primero `routes/web.py` y luego `routes/api.py`; la ubicación determina el tipo de ruta. Las rutas web incorporan sesión, CSRF y resolución de identidad de sesión. Las rutas API utilizan resolución de identidad mediante token y no añaden automáticamente estado de navegador. Resolver identidad permite invitados; exige autenticación explícitamente para proteger recursos.

`public()` selecciona el perfil HTTP sin estado y elimina las capas de sesión, CSRF e identidad. Úsalo para endpoints que no necesitan credenciales de cookies ni la identidad actual. Las políticas globales continúan aplicándose. No lo uses como sustituto de una decisión de autorización.

## Asincronía, scopes y fallos

Escribe `async def` para operaciones con I/O y espera las APIs asíncronas. El soporte para funciones síncronas no convierte una llamada bloqueante dentro de un controlador asíncrono en trabajo seguro para el event loop. Delega CPU o I/O síncrono largo a servicios adecuados.

La solicitud y su identidad viven en un scope. No conserves el `Request`, la sesión ni el contexto autenticado en singletons o variables globales. El kernel precarga y reutiliza instancias de middleware: almacena datos de cada petición en variables locales o `request.state`.

Las excepciones de validación y autenticación se convierten mediante los manejadores del framework. Una excepción después de enviar encabezados de streaming ya no puede reemplazar el estado HTTP enviado. Diseña el trabajo de preparación para fallar antes de devolver el stream.

## Evidencia y continuación

Consulta [rutas](routing.md), [middleware](middleware-and-security.md) y [fallos](../../../failure/docs/es/README.md). Implementación: [kernel](../../kernel.py), [loader](../../routes/loader.py), [BaseController](../../base/controller.py). Pruebas: [kernel](../../../../tests/http/test_kernel.py), [recursos por petición](../../../../tests/http/test_execution_resources.py), [planes de handlers](../../../../tests/http/test_handler_plan_warmup.py).
