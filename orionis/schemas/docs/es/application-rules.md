# Reglas de aplicación y validación con I/O

Las constraints describen límites estructurales que se compilan al declarar la clase. Una `Rule` comprueba una condición de aplicación después de convertir los tipos. Combínalas con `Field[T, ...]`; `Field` es un alias de `typing.Annotated`, no una función que reciba `default=`.

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

`ActiveUrl` comprueba resolución DNS del hostname, no que el recurso HTTP exista o sea seguro para descargar. La variante síncrona bloquea; la asíncrona usa resolución mediante el loop. Para solicitudes utiliza `validateAsync()` y una política de acceso a recursos independiente de la validación del formato.

`Unique` necesita Database preparado. Su variante async conserva la conexión/transacción activa. La variante sync puede puentear a un loop y, si ya existe un loop, usar una conexión aislada: no asumas visibilidad de los cambios no confirmados de otra conexión. La consulta de validación no garantiza unicidad frente a carreras; define también la restricción de unicidad en la base de datos y maneja el conflicto al persistir. Nunca derives `table`, `column`, `ignore_column` o la conexión directamente de entrada no confiable.

## Escribir una regla propia

Hereda de `Rule`, define `__code__` y `__message__` e implementa `enforce(field, value, instance) -> bool`. El retorno falso crea un fallo; `instance` permite consultar campos hermanos. La base ofrece `enforceAsync` que usa `enforce`, por lo que una regla CPU breve funciona en ambos caminos. Para I/O nativo, sobrescribe `async enforceAsync(...)` y espera el servicio; no escondas I/O bloqueante dentro de `enforce` en un handler async. Conserva las reglas sin estado mutable por solicitud: el schema y sus planes se reutilizan.

```python
from orionis.schemas.rule import Rule

class Even(Rule):
    __code__ = "even"
    __message__ = "Value must be even."

    def enforce(self, field: str, value: object, instance: object) -> bool:
        return isinstance(value, int) and value % 2 == 0
```

Puedes combinar `Even()` con `Field[int, Even()]`. Las opciones inválidas o constraints incompatibles fallan al declarar el schema; corrige la declaración en lugar de convertir el error de programación en un fallo de usuario.

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

registration = Validator.validate({
    "email": "ada@example.com",
    "password": "Example42",
    "password_confirmation": "Example42",
    "accepted_terms": True,
}, Registration)
assert registration.email == "ada@example.com"
```

Fuentes: [Rule](../../rule.py) · [Rules](../../rules/__init__.py) · [Validator](../../validator.py).

[Índice](README.md).
