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

| Alias | Equivalente | Uso |
| --- | --- | --- |
| `Field` | `Annotated` | Adjuntar constraints, reglas y metadatos al tipo de un campo. |
| `Choice` | `Literal` | Admitir únicamente los valores literales enumerados. |
| `Nullable` | `Optional` | Permitir `None`; el campo sigue siendo obligatorio si no tiene default. |
| `AnyOf` | `Union` | Admitir tipos alternativos compatibles con `msgspec`. |
| `Constant` | `Final` | Indicar intención a las herramientas de tipos; no valida ni impide asignaciones en ejecución. |
| `Alias` | `TypeAlias` | Declarar aliases de tipos reutilizables. |
| `Static` | `ClassVar` | Declarar un atributo de clase que no pertenece al payload. |

Este programa utiliza los siete aliases. El alias de tipo y la constante se declaran a nivel de módulo; `Constant` no se usa como tipo de un campo del schema:

```python
import asyncio
from orionis.schemas import Schema
from orionis.schemas.constraints import MinLength
from orionis.schemas.exceptions import ValidationException
from orionis.schemas.fields import Alias, AnyOf, Choice, Constant, Field, Nullable, Static
from orionis.schemas.validator import Schema as Validator

DisplayName: Alias = Field[str, MinLength(2)]
DEFAULT_PAGE_SIZE: Constant[int] = 20

class Search(Schema):
    name: DisplayName
    reference: AnyOf[int, str]
    note: Nullable[str]
    priority: Choice["low", "normal", "high"] = "normal"
    page_size: int = DEFAULT_PAGE_SIZE
    source: Static[str] = "web"

class OptionalNote(Schema):
    note: Nullable[str] = None

async def main() -> None:
    search = await Validator.validate({
        "name": "Ada", "reference": 42, "note": None, "page_size": 50,
    }, Search)
    assert search.reference == 42
    assert search.note is None
    assert search.priority == "normal"
    assert search.page_size == 50  # Constant no obliga a utilizar 20.
    assert Search.source == "web"
    assert "source" not in search.toDict()
    assert (await Validator.validate({}, OptionalNote)).note is None

    alternate = await Validator.validate({
        "name": "Ada", "reference": "INV-42", "note": "Urgent",
    }, Search)
    assert alternate.reference == "INV-42"

    for invalid in (
        {"name": "A", "reference": 42, "note": None},
        {"name": "Ada", "reference": [], "note": None},
        {"name": "Ada", "reference": 42},
        {"name": "Ada", "reference": 42, "note": None, "priority": "urgent"},
    ):
        try:
            await Validator.validate(invalid, Search)
        except ValidationException:
            pass
        else:
            raise AssertionError("invalid search accepted")

asyncio.run(main())
```

`AnyOf[int, str]` permite distinguir ambos tipos. No todas las uniones admitidas por las herramientas de tipos son convertibles con `msgspec`; por ejemplo, `AnyOf[str, bytes]` no es una alternativa compatible. Para comprobar valores concretos use `Choice`, no `Constant`. Para datos opcionales que puedan omitirse combine `Nullable[T]` con `= None`.

`toDict()` convierte recursivamente las instancias anidadas de `Schema` y de `msgspec.Struct` en diccionarios, incluso dentro de valores de diccionarios, listas y tuplas. Conserva los nombres de campos de Python, las claves de diccionarios y los tipos lista/tupla; los demás valores hoja, como objetos `datetime` y `Decimal`, permanecen sin cambios. La conversión no modifica la instancia original ni sus contenedores.

### Constraints estructurales

`GreaterThan`, `GreaterThanOrEqual`, `LessThan`, `LessThanOrEqual`, `MultipleOf`, `Pattern`, `MinLength`, `MaxLength`, `TimezoneAware` y `TimezoneNaive` compilan al descriptor de conversión. Combinaciones duplicadas, incompatibles, imposibles o inválidas fallan al crear la clase.

También se compilan dentro de anotaciones de colecciones y uniones compatibles. `list[Field[int, GreaterThanOrEqual(1)]]` restringe cada elemento; `Field[list[int], MinLength(1)]` restringe el tamaño de la lista. Para un número nullable, coloque `Nullable` alrededor del tipo restringido: `Nullable[Field[int, GreaterThanOrEqual(1)]]`, no `Field[Nullable[int], GreaterThanOrEqual(1)]`.

Este programa independiente comprueba colecciones, `None` y varios fallos sobre un mismo valor:

```python
import asyncio

from orionis.schemas import Schema
from orionis.schemas.constraints import GreaterThanOrEqual, MultipleOf
from orionis.schemas.exceptions import ValidationException
from orionis.schemas.fields import Field, Nullable
from orionis.schemas.validator import Schema as Validator


class Quantities(Schema):
    items: list[Field[int, GreaterThanOrEqual(1), MultipleOf(2)]]
    limit: Nullable[Field[int, GreaterThanOrEqual(1), MultipleOf(2)]]


async def main() -> None:
    result = await Validator.validate({"items": [2, 4], "limit": None}, Quantities)
    assert result.items == [2, 4]
    assert result.limit is None

    try:
        await Validator.validate({"items": [-1, 0], "limit": -1}, Quantities)
    except ValidationException as error:
        codes = {
            field: {detail["rule"] for detail in details}
            for field, details in error.errors.items()
        }
        assert codes == {
            "items[0]": {"ge", "multiple_of"},
            "items[1]": {"ge"},
            "limit": {"ge", "multiple_of"},
        }
        print(error.error())
    else:
        raise AssertionError("Expected invalid quantities.")


asyncio.run(main())
```

El valor `-1` produce dos fallos en su campo; `0` sólo incumple el mínimo. `limit` sigue siendo obligatorio aunque admita `None`. Las reglas `Rule` internas, como `list[Field[str, Email()]]`, se rechazan con `TypeError` al declarar el schema: para reglas por elemento use un schema hijo con `email: Field[str, Email()]`; una regla en el `Field` exterior de la lista comprueba la colección completa.

### Reglas de aplicación

Las reglas hacen checks de dominio tras convertir: strings, fechas, números, campos cruzados, aceptación, passwords, archivos/imágenes, red, URL, JSON, UUID/ULID, MIME/tamaño/dimensiones y unicidad database. Un plan recorre schemas/contenedores y acumula fallos.

### Validación siempre asíncrona

`await Validator.validate(payload, schema)` convierte y completa todas las reglas aplicables antes de devolver la instancia. No existe una entrada de validación síncrona. Cada regla ejecutable implementa `async def enforce` y la validación siempre espera ese método. Los checks puros breves permanecen en el hilo del llamador; el I/O nativo usa su event loop. `Unique` conserva la conexión y transacción activas.

### Metadata documental

`Title`, `Description`, `Examples` y `ExtraJsonSchema` alimentan JSON Schema/OpenAPI. `Extra` transporta metadata propia. `Message` cambia error de tipo; muchos constraints/reglas aceptan `message=`.

## Flujos de trabajo comunes

### Validar payload HTTP/controlador

Anote un parámetro invocado por contenedor con un `Schema`. Orionis convierte la entrada apropiada y espera validación antes del handler. Un fallo se vuelve respuesta normal de validación.

Si el controlador devuelve directamente una instancia `Schema`, Orionis valida su contenido antes de responder JSON. La construcción directa y las mutaciones no ejecutan validación por sí mismas; una salida inválida se trata como fallo de servidor (`500`). Devolver un diccionario con una anotación `-> Profile` no activa esta comprobación.

### Validar manualmente

Use siempre `await Validator.validate`. En el límite externo de una aplicación síncrona, ejecute una entrada async mediante `asyncio.run(main())`; no inicie otro loop dentro de uno activo. No use construcción directa para diccionarios no confiables.

### Personalizar mensajes

Adjunte `Message("...")` para tipo erróneo y `message=` en el constraint/regla correspondiente. Los errores conservan rutas para campos/contenedores anidados.

### Escribir regla personalizada

Subclasifique `Rule`, defina `__code__`/`__message__` e implemente `async def enforce` tanto para checks puros como para I/O asíncrono nativo. El método heredado `validate` siempre espera esa evaluación. Los overrides síncronos se rechazan al declarar la clase.

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
    assert exception.errors["name"][0]["rule"] == "min_length"
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

    async def enforce(self, field: str, value: object, instance: object) -> bool:
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
