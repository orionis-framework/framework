# Declarar schemas y convertir datos

Los bloques del ejemplo `Profile` se ejecutan en orden dentro del mismo módulo; los ejemplos de `Batch` y el handler muestran casos separados. `Validator` es el alias de la utilidad de validación, distinto de la clase base de declaración.

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


### Esperar validación async

```python
import asyncio
from orionis.schemas.validator import Schema as Validator


async def example() -> None:
    profile = await Validator.validateAsync({"name": "Lin", "age": 21}, Profile)
    assert profile.name == "Lin"


asyncio.run(example())
```


### Usar parámetros schema con invocación del contenedor

```python
from orionis.http import JSONResponse, Response


async def store_profile(payload: Profile) -> Response:
    return JSONResponse({"profile": payload.toDict()}, status_code=201)
```

## Configuración

El paquete no tiene configuración global ni variables de entorno. Cada constraint/regla se declara en el campo. Reglas de I/O llevan parámetros propios—por ejemplo `Unique(table, column, connection=...)`—y consumen servicios ya configurados.

## Fuentes y siguientes pasos

[schema.py](../../schema.py) · [compiler.py](../../compiler.py) · [validator.py](../../validator.py) · [fields.py](../../fields.py)

[Volver al índice del módulo](README.md).
