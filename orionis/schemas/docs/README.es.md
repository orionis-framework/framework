# orionis.schemas

> `orionis.schemas` proporciona esquemas tipados y compilados con constraints estructurales, reglas de aplicación, errores anidados y validación async.

## Descripción general

Un `Schema` Orionis es un `msgspec.Struct` procesado por `SchemaMeta`. Los campos usan anotaciones Python; `Annotated`—alias `Field`—adjunta constraints, reglas, documentación y mensajes. La metaclase compila constraints y planes al crear la clase para mantener pequeño el camino exitoso.

Declaración y validación están separadas. La construcción directa confía en valores ya tipados bajo la semántica del constructor `msgspec`. `orionis.schemas.validator.Schema.validate()` y `validateAsync()` convierten payloads no confiables y lanzan `ValidationException` con fallos por campo.

## Requisitos

- Python 3.14 o posterior; la compilación usa evaluación diferida de anotaciones.
- Imports explícitos desde `fields`, `constraints`, `metadata`, `rules`, `validator` y `exceptions`; la raíz solo exporta `Schema`.
- Conexión database iniciada para `Unique` y contexto de red/archivo para reglas que lo necesiten.

## Inicio rápido

```python
from orionis.schemas import Schema
from orionis.schemas.constraints import GreaterThanOrEqual, MaxLength, MinLength
from orionis.schemas.fields import Field


class Profile(Schema):
    name: Field[str, MinLength(2), MaxLength(80)]
    age: Field[int, GreaterThanOrEqual(18)]
    newsletter: bool = False


profile = Profile(name="Ada", age=36)
assert profile.toDict() == {"name": "Ada", "age": 36, "newsletter": False}
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

## Conceptos principales

### Schema y Field

`Schema` ofrece almacenamiento compacto y `toDict()`. `Field` es `typing.Annotated`, no descriptor runtime: `Field[str, MinLength(2)]` conserva `str` y adjunta metadata. `Choice`, `Nullable`, `AnyOf`, `Constant`, `Alias` y `Static` son aliases legibles de typing estándar.

### Constraints estructurales

`GreaterThan`, `GreaterThanOrEqual`, `LessThan`, `LessThanOrEqual`, `MultipleOf`, `Pattern`, `MinLength`, `MaxLength`, `TimezoneAware` y `TimezoneNaive` compilan al descriptor de conversión. Combinaciones duplicadas, incompatibles, imposibles o inválidas fallan al crear la clase.

### Reglas de aplicación

Las reglas hacen checks de dominio tras convertir: strings, fechas, números, campos cruzados, aceptación, passwords, archivos/imágenes, red, URL, JSON, UUID/ULID, MIME/tamaño/dimensiones y unicidad database. Un plan recorre schemas/contenedores y acumula fallos.

### Validación síncrona y asíncrona

`validate()` convierte y ejecuta reglas síncronas. `validateAsync()` también espera reglas async y es preferido por DI. `Unique` usa la conexión/transacción activa async; su puente síncrono puede necesitar conexión aislada dentro de event loop.

### Metadata documental

`Title`, `Description`, `Examples` y `ExtraJsonSchema` alimentan JSON Schema/OpenAPI. `Extra` transporta metadata propia. `Message` cambia error de tipo; muchos constraints/reglas aceptan `message=`.

## Estructura del módulo

| Ruta | Responsabilidad |
|---|---|
| `schema.py` | `Schema`, metaclase PEP 649, constraints y calentamiento de planes. |
| `fields.py` | Aliases legibles de typing. |
| `constraints.py`, `compiler.py` | Metadata estructural y compilación segura. |
| `rule.py`, `rules/` | Base y reglas síncronas/asíncronas. |
| `validator.py`, `rules_executor.py` | Conversión y ejecución anidada cacheada. |
| `failure_collector.py`, `exception_parser.py` | Recuperación multicausa y mensajes. |
| `metadata.py`, `meta/` | Metadata documental y de validación. |
| `entities/failure.py`, `exceptions/validation.py` | Fallos inmutables y excepción agrupada. |

## API pública

`from orionis.schemas import Schema` es el único export raíz. APIs avanzadas son explícitas:

- `orionis.schemas.fields`: `Field`, `Choice`, `Nullable`, `AnyOf`, `Constant`, `Alias`, `Static`.
- `orionis.schemas.constraints`: constraints estructurales y reglas incluidas.
- `orionis.schemas.metadata`: `Title`, `Description`, `Examples`, `ExtraJsonSchema`, `Extra`, `Message`.
- `orionis.schemas.validator.Schema`: `validate`/`validateAsync`; use alias `Validator`.
- `orionis.schemas.rule.Rule`: base de reglas personalizadas.
- `ValidationException`: `failures`, `failure`, `errors`, `message` y `error()`.

## Flujos de trabajo comunes

### Validar payload HTTP/controlador

Anote un parámetro invocado por contenedor con un `Schema`. Orionis convierte la entrada apropiada y espera validación antes del handler. Un fallo se vuelve respuesta normal de validación.

### Validar manualmente

Use `Validator.validate` en código síncrono y `await Validator.validateAsync` en async. No use construcción directa para diccionarios no confiables.

### Personalizar mensajes

Adjunte `Message("...")` para tipo erróneo y `message=` en el constraint/regla correspondiente. Los errores conservan rutas para campos/contenedores anidados.

### Escribir regla personalizada

Subclasifique `Rule`, defina `__code__`/`__message__` e implemente `enforce`. Para I/O async nativo sobrescriba `enforceAsync` y valide async.

## Ejemplos

### Convertir y validar mapping no confiable

```python
from orionis.schemas.validator import Schema as Validator

profile = Validator.validate(
    {"name": "Grace", "age": 37, "newsletter": True},
    Profile,
)
assert isinstance(profile, Profile)
assert profile.newsletter is True
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Inspeccionar fallos agrupados

```python
from orionis.schemas.exceptions import ValidationException

try:
    Validator.validate({"name": "x", "age": 12}, Profile)
except ValidationException as exception:
    assert set(exception.errors) == {"name", "age"}
    assert len(exception.failures) == 2
    payload = exception.error()
    assert payload["message"]
else:
    raise AssertionError("invalid profile was accepted")
```

Validación: **Ejecutado correctamente** en CPython 3.14.6; se recolectaron ambos fallos.

### Definir y ejecutar regla personalizada

```python
from orionis.schemas import Schema
from orionis.schemas.fields import Field
from orionis.schemas.rule import Rule
from orionis.schemas.validator import Schema as Validator


class Even(Rule):
    __code__ = "even"
    __message__ = "Value must be even."

    def enforce(self, field: str, value: object, instance: object) -> bool:
        return isinstance(value, int) and value % 2 == 0


class Batch(Schema):
    size: Field[int, Even()]


assert Validator.validate({"size": 4}, Batch).size == 4
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Esperar validación async

```python
import asyncio
from orionis.schemas.validator import Schema as Validator


async def example() -> None:
    profile = await Validator.validateAsync({"name": "Lin", "age": 21}, Profile)
    assert profile.name == "Lin"


asyncio.run(example())
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Usar parámetros schema con invocación del contenedor

```python
from orionis.http import Response


async def store_profile(payload: Profile) -> Response:
    return Response.json({"profile": payload.toDict()}, status=201)
```

Validación: **Importación y sintaxis validadas** en CPython 3.14.6; la inyección automática requiere ámbito HTTP/contenedor.

## Configuración

El paquete no tiene configuración global ni variables de entorno. Cada constraint/regla se declara en el campo. Reglas de I/O llevan parámetros propios—por ejemplo `Unique(table, column, connection=...)`—y consumen servicios ya configurados.

## Integración con Orionis

El contenedor detecta parámetros `Schema`, selecciona entrada y llama `validateAsync`. El kernel HTTP renderiza `ValidationException`. Realtime compila schemas para remotos y MCP los usa para entradas, JSON Schema de salida y errores de parámetros.

La metadata documental alimenta compiladores JSON Schema/OpenAPI sin formar parte de la validación de instancia.

## Errores y casos límite

- Campos extra/ausentes, valores incompatibles y límites producen `ValidationException` bajo `Validator`.
- `msgspec.convert` directo lanza `msgspec.ValidationError`, no la excepción agrupada.
- Construcción directa no ejecuta todo el pipeline no confiable.
- El orden de reglas sigue metadata; se acumulan fallos entre campos y anidados.
- `Message` cubre tipo, no toda regla; use `message=` en la regla exacta.
- `ActiveUrl` usa red; `Unique` usa database; reglas de archivo/imagen requieren upload compatible.
- Metadata conflictiva falla al declarar la clase.

## Rendimiento y concurrencia

Metadata estructural y planes se compilan al crear la clase y cachean por tipo. La conversión exitosa usa una llamada optimizada `msgspec.convert`; inspección detallada se reserva para errores.

Instancias y planes son compactos y no retienen estado global. Reglas async preservan loop/transacción. Evite reglas síncronas con I/O en event loop y use `validateAsync`.

## Compatibilidad

Los schemas son `msgspec.Struct` y pueden codificarse con codecs compatibles. La declaración pública depende de anotaciones diferidas Python 3.14. Use metadata Orionis en vez de construir `msgspec.Meta` para conservar mensajes/documentación consistentes.

## Notas de verificación

- `tests/schemas`: **450 métodos de prueba aprobados** con el runner de Orionis en CPython 3.14.6.
- Se compilaron seis programas bilingües; cinco programas autónomos se ejecutaron correctamente.
- El handler contenedor/HTTP se validó por importación/sintaxis porque la inyección requiere request live.
- La evidencia cubrió metaclase, constraints/conflictos, reglas, anidados, async, metadata, package boundary y unicidad database.

