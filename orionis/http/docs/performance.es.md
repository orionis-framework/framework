# Ejecución HTTP y respuestas constantes

Las rutas conservan su comportamiento de sesión, CSRF e identidad por defecto.
`Route.get(...).public()` selecciona explícitamente un endpoint sin ese contexto
automático. El nombre describe un perfil sin sesión, no una autorización que anule
middleware: las validaciones globales, CORS, mantenimiento, rate limiting y todos
los middleware declarados para aplicación, grupo o ruta continúan ejecutándose.

```python
from orionis.http import Response, ResponseTemplate
from orionis.support.facades.router import Route

HELLO = ResponseTemplate(
    b"Hello, world!",
    headers={"content-type": "text/plain; charset=utf-8"},
)


def hello() -> Response:
    """Create an independent response for a stateless endpoint.

    Returns
    -------
    Response
        Response with shared immutable content and request-local headers.
    """
    return HELLO.make()


Route.get("/hello", hello).public()
```

El perfil público omite `StartSessionMiddleware`, `CSRFTokenMiddleware` y la
resolución automática de identidad de sesión o token. Úsalo para rutas que no
dependen de credenciales en cookies, sesión, flash o redirecciones de validación
web. Los errores de validación sin contexto web reciben la respuesta JSON 422.
No conviertas endpoints de login o formularios con sesión a este perfil para
reducir tiempos de un benchmark.

Un grupo puede pasar `public=True`. Una elección explícita en un hijo, como
`.public(enabled=False)`, tiene precedencia sobre el perfil heredado. Los grupos
internos también conservan su elección cuando se componen dentro de otro grupo.
La elección se guarda en los metadatos compilados y en la caché de rutas.

## Qué se reutiliza

`ResponseTemplate` copia y valida su contenido y headers una vez. Cada `make()`
produce una `Response` independiente: comparte bytes inmutables y headers
codificados inmutables; cookies, modificaciones de headers, flash y background
pertenecen a esa respuesta. La plantilla no acepta streams ni contenido mutable.
El constructor básico mantiene la misma semántica de `media_type` que `Response`;
declara `content-type` en `headers` cuando lo necesites.

Los headers codificados se invalidan al reemplazar o agregar valores, quitar
headers o exponer la lista mutable de `getHeader()`. Después de exponer esa lista,
los envíos reflejan sus mutaciones posteriores; no se vuelve a almacenar un cache
que pueda quedar obsoleto. `getRawHeaders()` entrega una lista independiente para
que el adaptador pueda agregar datos de HEAD/rangos sin modificar la plantilla.
Los adaptadores ejecutan los hooks `runBackground()` sobrescritos por subclases,
aunque no tengan un objeto `background` adjunto.

## Trabajo diferido y middleware

El kernel sigue creando un `Request` y un scope DI por petición para mantener el
aislamiento y permitir facades e inyección. El `BodyStream` nace al primer acceso
al cuerpo; la representación completa del scope del transporte nace al primer
acceso a sus campos. GET sin lectura de cuerpo evita el stream. RSGI evita crear
el diccionario completo cuando ningún consumidor necesita el scope.

Los headers de entrada se decodifican, indexan y revisan para detectar CR/LF en
el mismo recorrido; seguridad consulta el resultado sin recorrerlos otra vez.
Los duplicados, orden original y valores Latin-1 se preservan. El contenedor es
dueño de los pares recibidos: modificar la lista original no puede desincronizar
el índice y la comprobación de formato.

Una pila vacía llama directamente al siguiente bloque. Una capa usa una sola
continuación por petición. Las pilas de varias capas entregan a cada middleware
su propia continuación para rechazar dos llamadas concurrentes a `next()` sin
saltar un middleware suspendido. Esa garantía necesita estado por capa; no se
comparte un pipeline mutable entre peticiones para reducir asignaciones.

Las pruebas de regresión están en `tests/http/test_execution_resources.py`.
Los resultados de throughput integrados se documentan por separado: estas
reducciones de trabajo no constituyen por sí solas una comparación con otro
framework, un servidor real o una carga de producción.
