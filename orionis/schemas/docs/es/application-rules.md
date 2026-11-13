# Reglas de aplicación y validación con I/O

Las constraints describen límites estructurales que se compilan al declarar la clase. Una `Rule` comprueba una condición de aplicación después de convertir los tipos. Combínalas con `Field[T, ...]`; `Field` es un alias de `typing.Annotated`, no una función que reciba `default=`.

Las 49 validaciones incluidas se componen de 39 reglas ejecutables y 10 constraints estructurales compilados. Todas las reglas ejecutables exponen el mismo método `enforce` obligatoriamente asíncrono; los constraints estructurales siguen siendo metadata de declaración, no una segunda API de ejecución.

## Elegir una regla incluida

| Necesidad | Reglas y parámetros relevantes |
|---|---|
| Valores vacíos | `Empty`, `NoEmpty`. Comparten la definición de vacío y siempre devuelven resultados opuestos. |
| Texto | `Alpha(ascii_only=False)`, `Ascii`, `Lowercase`, `Uppercase`, `Encoding(encoding="utf-8")`. |
| Prefijos y sufijos | `StartsWith(*prefixes)`, `EndsWith(*suffixes)`, `DoesntStartWith(*prefixes)`, `DoesntEndWith(*suffixes)`. |
| Formatos | `Email`, `Json`, `IpAddress(version=4)`, `MacAddress`, `Uuid(version=None)`, `Ulid`. Usa `IpAddress(version=None)` para permitir IPv4 o IPv6. |
| Tamaño | `Between(minimum, maximum)`, `Size(size)`, `MaxDigits(maximum)`, `DecimalPlaces(minimum, maximum=None)`, `Integer`. |
| Fecha | `DateFormat(*formats)`, `After(reference=None)`, `AfterOrEqual`, `Before`, `BeforeOrEqual`. Las comparaciones temporales comparten normalización; revisa el tipo de fecha que declara tu schema. |
| Campos relacionados | `ConfirmPassword(other_field="password")`, `GreaterThanOrEqualField(other_field)`, `LessThanOrEqualField(other_field)`. `ConfirmPassword` se coloca sobre la confirmación. |
| Valores y claves | `Accepted`, `Different(*values)`, `StrongPassword`. `Different` compara con valores configurados; no significa «diferente de otro campo». |
| Archivos | `File`, `Image`, `MimeTypes(*mime_types)`, `Dimensions(...)`. Requieren un objeto de archivo compatible; una ruta enviada por el cliente no equivale a un upload. |
| Servicios externos | `ActiveUrl`, `Unique(table, column, *, ignore=None, ignore_column="id", connection=None)`. |

Todas aceptan `message=` como opción keyword. `Between` y `Size` usan magnitud numérica, longitud para texto/colecciones y kilobytes para uploads. `Dimensions` admite `width`, `height`, `min_width`, `max_width`, `min_height`, `max_height`, `ratio`, `min_ratio`, `max_ratio`; los ratios pueden ser números o textos como `"3/2"`. El lector de imágenes inspecciona cabeceras; no convierte ni sanea un archivo.

Las reglas que leen uploads ejecutan el lector síncrono fuera del hilo del loop.
Si se cancela la operación, esperan a que termine la lectura activa antes de
propagar `CancelledError`. El upload sigue perteneciendo al llamador y el lector
no lo cierra.

Las comparaciones de magnitud conservan la precisión de `Decimal`, incluidos los
límites entre campos. `MaxDigits` requiere un entero o un texto de dígitos con
signo opcional; rechaza letras y signos mal ubicados. `Integer`, `Email`,
`MacAddress` y `Uuid` comprueban el formato completo y rechazan saltos de línea
finales. `Ulid` exige el alfabeto Crockford ASCII y el rango de 128 bits en ambas
cajas.

`Image` y `Dimensions` reconocen cabeceras compatibles de PNG, JPEG, GIF, BMP y
WebP con dimensiones positivas. No decodifican píxeles, comprueban checksums ni
verifican todo el contenido comprimido. Reconocer la cabecera no demuestra que
un decodificador pueda leer la imagen completa. `Encoding` devuelve un fallo de
regla si el upload está cerrado o no puede leerse.

Las reglas de comparación temporal rechazan textos que no representan una fecha. Los números y `None` siguen sujetos al tipo declarado del campo. `Dimensions` exige ratios finitos y `Json` rechaza textos que no se pueden codificar como UTF-8 válido.

`StrongPassword` exige al menos ocho caracteres, una mayúscula ASCII, una minúscula ASCII y un dígito ASCII. No exige un símbolo ni consulta contraseñas filtradas. La validación no reemplaza el [hashing](../../../hashing/docs/es/README.md).

## Valores vacíos y no vacíos

`Empty()` acepta `None`, strings vacíos o compuestos solo por espacios en blanco, cero numérico, `False` y valores de longitud cero. Esto incluye listas, tuplas, diccionarios, sets, bytes, arrays y contenedores similares. Los uploads están vacíos cuando su tamaño en bytes es cero; comprobarlo nunca lee el contenido del archivo. `NoEmpty()` rechaza exactamente esos valores.

Los espacios solo se comprueban: no se eliminan del valor almacenado. `"0"` y `"false"` son strings no vacíos; con `Coerce()`, las reglas reciben el valor convertido, por lo que `0` numérico y `False` booleano están vacíos. Las colecciones se comprueban por su longitud, no por el contenido: `[None]` y `{"key": None}` no están vacíos. Los iteradores sin longitud y otros objetos se consideran presentes sin consumirlos.

```python
from orionis.schemas import Schema
from orionis.schemas.fields import Field
from orionis.schemas.rules import Empty, NoEmpty


class Form(Schema):
    name: Field[str, NoEmpty(message="Name required.")]
    tags: Field[list[str], NoEmpty()]
    reserved: Field[str | None, Empty()] = None
```

Ambas reglas aceptan `message=`. Sus errores usan los códigos `empty` y `no_empty`. Los campos ausentes conservan la obligatoriedad del schema y la conversión de tipos ocurre antes de las reglas: aceptar `None` exige un tipo declarado compatible. También se reexportan desde `orionis.schemas.constraints`.

## Componer registro y confirmación

El ejemplo completo inferior valida un registro con aceptación explícita y confirmación. La política de contraseñas se aplica al valor original y la comparación al campo de confirmación. No se persisten las contraseñas ni se ejecuta autenticación en este ejemplo.

## Validación que consulta otros servicios

`ActiveUrl` comprueba resolución DNS del hostname, no que el recurso HTTP exista o sea seguro para descargar. `await Validator.validate(...)` usa resolución mediante el loop sin bloquearlo. Aplica una política de acceso a recursos independiente de la validación del formato.

`Unique` necesita Database preparado. La validación espera su I/O nativo y conserva la conexión/transacción activa. La consulta de validación no garantiza unicidad frente a carreras; define también la restricción de unicidad en la base de datos y maneja el conflicto al persistir. Nunca derives `table`, `column`, `ignore_column` o la conexión directamente de entrada no confiable.

## Escribir una regla propia

Hereda de `Rule`, define `__code__` y `__message__` e implementa `async def enforce(field, value, instance) -> bool`, incluso para predicados puros. El retorno falso crea un fallo; `instance` permite consultar campos hermanos. `Rule.validate` siempre espera `enforce`; no hay otro método de evaluación ni un camino síncrono alternativo. Un override síncrono produce `TypeError` al crear la clase de la regla. Usa `await` nativo para I/O y no escondas operaciones bloqueantes dentro de `enforce`. Los checks puros breves permanecen en el hilo del llamador, sin hilos auxiliares. Conserva las reglas sin estado mutable por solicitud: el schema y sus planes se reutilizan.

```python
from orionis.schemas.rule import Rule


class Even(Rule):
    __code__ = "even"
    __message__ = "Value must be even."

    async def enforce(self, field: str, value: object, instance: object) -> bool:
        return isinstance(value, int) and value % 2 == 0
```

Puedes combinar `Even()` con `Field[int, Even()]`. Las opciones inválidas o constraints incompatibles fallan al declarar el schema; corrige la declaración en lugar de convertir el error de programación en un fallo de usuario. Las reglas que leen contenido de uploads delegan la lectura síncrona a un hilo auxiliar para no bloquear el loop cuando el archivo reside en disco.

Ejecuta el siguiente fragmento de validación dentro de una función async o una consola que admite `await`.

```python
from orionis.schemas import Schema
from orionis.schemas.fields import Field
from orionis.schemas.rules import Accepted, ConfirmPassword, Email, StrongPassword
from orionis.schemas.validator import Schema as Validator


class Registration(Schema):
    email: Field[str, Email()]
    password: Field[str, StrongPassword()]
    password_confirmation: Field[str, ConfirmPassword()]
    accepted_terms: Field[bool, Accepted()]


registration = await Validator.validate(
    {
        "email": "ada@example.com",
        "password": "Example42",
        "password_confirmation": "Example42",
        "accepted_terms": True,
    },
    Registration,
)
assert registration.email == "ada@example.com"
```

Fuentes: [Rule](../../rule.py) · [Rules](../../rules/__init__.py) · [Validator](../../validator.py).

[Índice](README.md).
