# Reglas de aplicación y validación con I/O

Las constraints describen límites estructurales que se compilan al declarar la clase. Una `Rule` comprueba una condición de aplicación después de convertir los tipos. Combínalas con `Field[T, ...]`; `Field` es un alias de `typing.Annotated`, no una función que reciba `default=`.

Las 47 validaciones incluidas se componen de 37 reglas ejecutables y 10 constraints estructurales compilados. Todas las reglas ejecutables exponen el mismo método `enforce` obligatoriamente asíncrono; los constraints estructurales siguen siendo metadata de declaración, no una segunda API de ejecución.

## Elegir una regla incluida

| Necesidad | Reglas y parámetros relevantes |
|---|---|
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

`StrongPassword` exige al menos ocho caracteres, una mayúscula ASCII, una minúscula ASCII y un dígito. No exige un símbolo ni consulta contraseñas filtradas. La validación no reemplaza el [hashing](../../../hashing/docs/es/README.md).

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

registration = await Validator.validate({
    "email": "ada@example.com",
    "password": "Example42",
    "password_confirmation": "Example42",
    "accepted_terms": True,
}, Registration)
assert registration.email == "ada@example.com"
```

Fuentes: [Rule](../../rule.py) · [Rules](../../rules/__init__.py) · [Validator](../../validator.py).

[Índice](README.md).
