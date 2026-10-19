# Declarar schemas y convertir datos

Los bloques del ejemplo `Profile` se ejecutan en orden dentro del mismo módulo; los ejemplos de `Batch` y el handler muestran casos separados. `Validator` es el alias de la utilidad de validación, distinto de la clase base de declaración.

Los fragmentos de validación se ejecutan dentro de una función async o una consola que admite `await`. El ejemplo con un runner independiente muestra cómo entrar en código async desde una aplicación síncrona.

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

`toDict()` convierte recursivamente las instancias anidadas de `Schema` y de `msgspec.Struct` en diccionarios, incluso dentro de valores de diccionarios, listas y tuplas. Conserva los nombres de campos de Python, las claves de diccionarios y los tipos lista/tupla; los demás valores hoja, como objetos `datetime` y `Decimal`, permanecen sin cambios. La conversión no modifica la instancia original ni sus contenedores.

### Constraints estructurales

`GreaterThan`, `GreaterThanOrEqual`, `LessThan`, `LessThanOrEqual`, `MultipleOf`, `Pattern`, `MinLength`, `MaxLength`, `TimezoneAware` y `TimezoneNaive` compilan al descriptor de conversión. Combinaciones duplicadas, incompatibles, imposibles o inválidas fallan al crear la clase.

### Reglas de aplicación

Las reglas hacen checks de dominio tras convertir: strings, fechas, números, campos cruzados, aceptación, passwords, archivos/imágenes, red, URL, JSON, UUID/ULID, MIME/tamaño/dimensiones y unicidad database. Un plan recorre schemas/contenedores y acumula fallos.

### Validación siempre asíncrona

`await Validator.validate(payload, schema)` convierte y completa todas las reglas aplicables antes de devolver la instancia. No existe una entrada de validación síncrona. Los predicados puros breves se ejecutan directamente; las reglas de I/O nativo se esperan en el loop del llamador. `Unique` conserva la conexión y transacción activas.

### Metadata documental

`Title`, `Description`, `Examples` y `ExtraJsonSchema` alimentan JSON Schema/OpenAPI. `Extra` transporta metadata propia. `Message` cambia error de tipo; muchos constraints/reglas aceptan `message=`.

## Flujos de trabajo comunes

### Validar payload HTTP/controlador

Anote un parámetro invocado por contenedor con un `Schema`. Orionis convierte la entrada apropiada y espera validación antes del handler. Un fallo se vuelve respuesta normal de validación.

### Validar manualmente

Use siempre `await Validator.validate`. En el límite externo de una aplicación síncrona, ejecute una entrada async mediante `asyncio.run(main())`; no inicie otro loop dentro de uno activo. No use construcción directa para diccionarios no confiables.

### Personalizar mensajes

Adjunte `Message("...")` para tipo erróneo y `message=` en el constraint/regla correspondiente. Los errores conservan rutas para campos/contenedores anidados.

### Escribir regla personalizada

Subclasifique `Rule`, defina `__code__`/`__message__` e implemente `enforce` para un predicado puro breve. Para I/O async nativo sobrescriba `enforceAsync`. El método heredado `validate` siempre es asíncrono y espera la evaluación nativa.

## Ejemplos

### Convertir y validar mapping no confiable

```python
from orionis.schemas.validator import Schema as Validator

profile = await Validator.validate(
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
    await Validator.validate({"name": "x", "age": 12}, Profile)
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


assert (await Validator.validate({"size": 4}, Batch)).size == 4
```


### Esperar validación async

```python
import asyncio
from orionis.schemas.validator import Schema as Validator


async def example() -> None:
    profile = await Validator.validate({"name": "Lin", "age": 21}, Profile)
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
