# Respuestas, cookies y descargas

Importa `response` desde `orionis.http`. Es una fábrica compartida que construye una respuesta independiente por llamada. Devuelve respuestas desde el controlador; los adaptadores se encargan de encabezados y envío ASGI/RSGI.

## Seleccionar una representación

```python
import json
from orionis.http import response

result = response.json({"id": 7, "status": "created"}, status_code=201)
result.setHeader("X-Request-ID", "docs-example")
assert result.getStatusCode() == 201
assert json.loads(result.getBody()) == {"id": 7, "status": "created"}
assert result.getHeader("x-request-id") == ["docs-example"]
```

`html()` y `text()` aceptan texto o bytes. `json()` serializa valores de aplicación y ofrece opciones como `indent`, `ensure_ascii` y `default`. `make()` construye una respuesta genérica; establece explícitamente el media type cuando el contenido lo necesite. `noContent()` crea por defecto un 204. Una respuesta HTML no sanea HTML de entrada: escapa datos ajenos mediante el motor de plantillas.

Para una plantilla usa `return await response.view("catalog/index", products=products)` dentro de tu handler; `products` debe ser el resultado obtenido por tu servicio. `view()` devuelve un `PendingView`, por lo que no es intercambiable con un `Response` ya construido sin esperar su render. Consulta [vistas](../../../view/docs/es/README.md).

`response.view()` y `View.make()` también aceptan opciones HTTP exclusivamente por nombre: `status_code=200`, `headers=None` y `background=None`. El valor de background debe ser una `BackgroundTask`; se ejecuta después del envío, no durante el render. Por ejemplo, con una plantilla `errors/401.html` existente:

```python
from orionis.http import response


async def unauthorized(ip: str):
    return await response.view(
        "errors.401",
        status_code=401,
        headers={"Cache-Control": "no-store"},
        ip=ip,
    )
```

El equivalente por encadenamiento es `await response.view("errors.401", ip=ip).withStatusCode(401).withHeaders({"Cache-Control": "no-store"})`. Usa `.withBackground(task)` para añadir una tarea o `.withBackground(None)` para eliminarla. Primero se aplican las opciones y luego las mutaciones encadenadas en orden, con validación al esperar la vista pendiente. Estos mismos métodos funcionan sobre respuestas construidas y devuelven `self`, con validación inmediata.

Las opciones HTTP no son variables de plantilla. Para pasar una variable llamada `status_code`, `headers`, `background` o `context`, usa `context={...}`. Las variables adicionales por nombre prevalecen sobre las entradas de ese mapping. Las cabeceras personalizadas conservan el valor predeterminado `X-Orionis-Render: SSR` salvo que lo reemplacen explícitamente, sin distinguir mayúsculas.

## Redirigir con estado de formulario

```python
from orionis.http import response

result = (
    response
    .redirect("/settings", status_code=303)
    .withFlash("notice", "Preferences saved")
    .withInput({"theme": "dark"})
)
assert result.getStatusCode() == 303
```

La aplicación web aplica estos datos a la sesión. `withErrors()` admite errores normalizables. Sin middleware de sesión no existe el ciclo de persistencia flash. La redirección debe tener un destino confiable; `redirect` no sustituye una comprobación de origen de una URL proporcionada por el usuario.

## Encabezados y cookies

`setHeader()` reemplaza todos los valores de una cabecera; `addHeader()` añade otro. `withHeaders(mapping)` reemplaza los nombres proporcionados, conserva las demás cabeceras y devuelve la respuesta para encadenar. `getHeader()` devuelve una lista o `None`; las búsquedas ignoran mayúsculas. No añadas saltos de línea en nombres o valores. `withCookie()` permite encadenamiento; `setCookie()` devuelve `None`.

Las cabeceras salientes rechazan nombres que no sean tokens válidos y caracteres de control inseguros antes del envío, incluidas las mutaciones mediante listas devueltas y copias de plantillas. Se conservan las tabulaciones horizontales y los valores Latin-1.

Los tipos de respuesta incorporados inicializan sus metadatos estándar directamente cuando es posible, sin compartir cabeceras mutables entre respuestas. Se conserva la precedencia de las cabeceras personalizadas, incluidas las sustituciones de metadatos de redirección y archivo. Las subclases siguen utilizando sus hooks de cabeceras durante la construcción; la serialización JSON y el consumo de streams no cambian.

```python
from orionis.http import response

result = response.text("saved").withCookie(
    "theme",
    "dark",
    secure=True,
    http_only=True,
    same_site="lax",
    max_age=3600,
)
result.deleteCookie("obsolete", path="/")
assert result.hasHeader("set-cookie")
```

Para borrar una cookie usa el mismo `path` y `domain` con los que se creó. `Secure`, `HttpOnly`, `SameSite` y `Partitioned` controlan atributos emitidos; la aceptación depende del navegador. Usa [sesiones](../../../session/docs/es/README.md) para datos sensibles de aplicación almacenados en el servidor.

## Archivos y reutilización segura

`response.file(path, media_type=..., filename=...)` verifica que exista un archivo regular y lo entrega con streaming. `download(path, filename=...)` añade disposición attachment. Resuelve la ruta desde un identificador autorizado, no desde un path arbitrario del cliente. Los adaptadores admiten un único intervalo de bytes por petición, no el manejo automático de peticiones condicionales. El archivo puede desaparecer entre construcción y lectura.

`ResponseTemplate` permite conservar cuerpos codificados y encabezados base y obtener respuestas independientes con `make()`. No reutilices una misma respuesta mutable entre solicitudes. El trabajo `background` se ejecuta después del envío y la limpieza; no es una cola durable ni garantiza ejecución tras una caída del proceso.


```python
from orionis.http import ResponseTemplate

template = ResponseTemplate(
    "ready", headers={"X-Service": "catalog"}, media_type="text/plain"
)
first = template.make()
second = template.make()
first.setHeader("X-Request-ID", "one")
assert not second.hasHeader("X-Request-ID")
assert first.getBody() == second.getBody() == b"ready"
```

Evidencia: [fábrica](../../factory.py), [respuestas](../../responses.py), [archivos y rangos](../../adapters/response/files.py). Pruebas: [respuestas](../../../../tests/http/test_response.py), [transporte](../../../../tests/http/adapters/test_response_transport.py), [reutilización](../../../../tests/http/test_response_performance.py). Sigue con [streaming](streaming-and-sse.md).
