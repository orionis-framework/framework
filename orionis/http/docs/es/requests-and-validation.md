# Leer solicitudes y validar entrada

`Request` separa metadatos síncronos de lectura asíncrona del cuerpo. Sus propiedades `method`, `path`, `scheme`, `url`, `baseUrl`, `headers`, `queryParams`, `cookies`, `ip`, `port` y `state` no requieren `await`. Los parsers sí leen un stream: espera `body()`, `text()`, `json()`, `xml()`, `msgpack()`, `formUrlEncoded()`, `form()`, `payload()` o `data()`.

## Un endpoint de preferencias

```python
from orionis.http import Request, response
from orionis.schemas import Schema
from orionis.schemas.validator import Schema as Validator

class Preferences(Schema):
    theme: str
    compact: bool = False

async def save_preferences(request: Request):
    values = await request.data()
    preferences = await Validator.validateAsync(values, Preferences)
    return response.json({"theme": preferences.theme, "compact": preferences.compact})
```

Registra este handler en una ruta con la política de autenticación apropiada. El ejemplo enseña decodificación y validación explícita de un schema; añade reglas de negocio y persistencia según [schemas](../../../schemas/docs/es/README.md). El kernel también soporta parámetros schema tipados mediante sus planes de inyección; no necesitas duplicar lectura manual cuando eliges ese flujo.

## Elegir el parser

`json()` preserva cualquier valor JSON válido, incluidas listas y escalares. `payload()` selecciona el parser por `Content-Type` y mantiene la forma del resultado. `data()` ofrece un diccionario normalizado para formularios y payloads de aplicación; no lo utilices si necesitas preservar una lista JSON superior. Los helpers específicos rechazan un MIME incompatible con `UnsupportedMediaTypeException`.

`headers` permite consultas sin distinguir mayúsculas y `getAll()` para valores repetidos. `queryParams.get()` y `.getAll()` distinguen acceso a un valor y a todos. Las cookies y parámetros de URL siguen siendo entrada no confiable: una cabecera `Authorization` o un `bearerToken` presente no demuestra autenticación. Utiliza el contexto de [Auth](../../../auth/docs/es/README.md).

## Un único consumidor del cuerpo

`stream()` entrega bytes de forma incremental. El cuerpo puede releerse solo si quedó completamente retenido dentro del límite de buffer. No combines streaming de archivos grandes con `json()` posterior ni hagas dos consumidores concurrentes sobre la misma petición. Los parsers cachean sus resultados cuando procede, pero esa caché no convierte un stream consumido sin buffer en un recurso reproducible.

`HTTP_MAX_BODY_SIZE` limita el total, `HTTP_MAX_BUFFER_SIZE` la memoria de relectura y `HTTP_MAX_CONCURRENT_REQUESTS` las peticiones activas por worker. Los valores predeterminados del bootstrap son 16 MiB, 2 MiB y 128. El límite se aplica también mientras llegan los chunks; un `Content-Length` pequeño no permite superarlo. Framing duplicado o contradictorio se rechaza antes de ejecutar el handler.

## Negociación y errores

`wantsJson()`, `wantsHtml()`, `wantsXml()`, `accepts(mime)` e `isAjax()` ayudan a elegir representación. No validan permisos. Los fallos schema de rutas API/JSON se presentan como errores estructurados; los formularios web pueden redirigir con errores e input filtrado. Los helpers de validación comprueban que el destino de retorno sea seguro para evitar una redirección controlada por entrada ajena.

Para depurar una lectura fallida revisa `Content-Type`, tamaño, consumo previo y formato antes de relajar límites. No registres cuerpos completos con credenciales.


## Formatos y parsers propios

`data()` exige un mapping superior para JSON/MessagePack y colapsa claves de formulario a valor único o lista según repetición. Su dispatch acepta los MIME exactos `application/json`, `application/msgpack`, `application/x-www-form-urlencoded` y `multipart/form-data`; a diferencia de `json()`, no reconoce automáticamente todo subtipo `+json`. `payload()` devuelve bytes si no hay parser registrado. XML usa defusedxml para rechazar entidades internas/externas.

Puedes crear un registro para construir Requests de infraestructura sin modificar el singleton predeterminado:

```python
from orionis.http.payload.media_types import DEFAULT_MEDIA_TYPES

registry = DEFAULT_MEDIA_TYPES.extend({"application/vnd.example.label": lambda raw: raw.decode("utf-8")})
parser = registry.get("application/vnd.example.label")
assert parser is not None and parser(b"ready") == "ready"
assert DEFAULT_MEDIA_TYPES.get("application/vnd.example.label") is None
```

Pasa `registry=` al constructor de Request cuando controles esa integración. `register` modifica el registro existente y `extend` crea uno nuevo. No modifica el dispatch de `data()`. El constructor nativo del kernel utiliza el registro predeterminado; esta API no registra por sí sola un provider de parser global.

El límite de buffer también acota la materialización de `body()`, JSON y parsers similares. Un cuerpo permitido por el límite total de 16 MiB puede superar el buffer de 2 MiB y no admitir lectura completa con esos helpers; usa streaming o ajusta ambos presupuestos deliberadamente.

Evidencia: [Request](../../request.py), [BodyStream](../../payload/body.py), [validación HTTP](../../validation.py). Pruebas: [solicitudes](../../../../tests/http/test_request.py), [límites](../../../../tests/http/test_request_limits.py), [validación](../../../../tests/http/test_validation.py). Continúa con [formularios y archivos](forms-and-uploads.md).
