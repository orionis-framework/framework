# Validación, errores e integración

## Integración con Orionis

El contenedor detecta parámetros `Schema`, selecciona entrada y espera `validate`. El kernel HTTP renderiza `ValidationException`. Realtime compila schemas para remotos y MCP espera la validación de entradas y salidas estructuradas, incluidos los resultados en streaming.

En HTTP, una instancia `Schema` devuelta directamente por el controlador se valida antes de crear la respuesta JSON. Esto comprueba también instancias construidas o modificadas en Python y sus schemas anidados. Una salida inválida produce estado `500`; no es un error `422` del cliente. La anotación de retorno por sí sola no convierte un diccionario en un schema. Las respuestas que no son instancias `Schema` no ejecutan este proceso; envolver previamente un schema en `JSONResponse` tampoco activa esta validación automática.

La metadata documental alimenta compiladores JSON Schema/OpenAPI sin formar parte de la validación de instancia.

## Errores y casos límite

- Campos obligatorios ausentes, valores incompatibles y límites producen `ValidationException` bajo `Validator`.
- `msgspec.convert` directo lanza `msgspec.ValidationError`, no la excepción agrupada.
- Construcción directa no ejecuta todo el pipeline no confiable.
- El orden de reglas sigue metadata; se acumulan fallos del mismo campo, de otros campos y de schemas anidados.
- Un límite incumplido no impide ejecutar otras restricciones ni reglas si el valor se pudo convertir a su tipo base. Un tipo incompatible impide ejecutar sus reglas de valor.
- `Message` cubre tipo, no toda regla; use `message=` en la regla exacta.
- `ActiveUrl` usa red; `Unique` usa database; reglas de archivo/imagen requieren upload compatible.
- Metadata conflictiva falla al declarar la clase.

## Rendimiento y concurrencia

Metadata estructural y planes se compilan al crear la clase y cachean por tipo. La conversión exitosa usa una llamada optimizada `msgspec.convert`; inspección detallada se reserva para errores.

Los planes se comparten por clase; no guarde datos de una solicitud en las instancias de reglas. Las reglas asíncronas preservan loop/transacción. Espere siempre `validate`, incluso en schemas sin reglas de I/O. Cada regla implementa `async def enforce`; use allí I/O asíncrono nativo para no bloquear el loop. Los checks puros no necesitan hilos auxiliares. Los tipos y constraints se verifican con el motor nativo de `msgspec`; las reglas Python y las consultas externas conservan su coste propio.

## Compatibilidad

Los schemas son `msgspec.Struct` y pueden codificarse con codecs compatibles. La declaración pública depende de anotaciones diferidas Python 3.14. Use metadata Orionis en vez de construir `msgspec.Meta` para conservar mensajes/documentación consistentes.

La validación ahora solo ofrece la entrada asíncrona `validate`. Migre cada llamada a `await Validator.validate(...)`; ya no se admiten llamadas síncronas ni el método alternativo anterior. Las reglas personalizadas deben implementar `async def enforce`, y las llamadas directas a ese método también se deben esperar. La recolección de fallos espera las reglas tras errores de conversión.

## Reglas dentro de colecciones de schemas

Las reglas del schema hijo se ejecutan tanto en campos anidados directos como en schemas dentro de listas, valores de diccionarios, tuplas, sets y frozensets, incluidas colecciones anidadas, valores opcionales y aliases compatibles como `Sequence` y `Mapping`. Son comprobaciones de Orionis adicionales a la conversión de tipos y los constraints estructurales compilados de msgspec; no hace falta validar manualmente cada elemento.

```python
class Contact(Schema):
    email: Field[str, Email()]

class Accounts(Schema):
    contacts: list[Contact]
    by_name: dict[str, Contact]
```

Con los imports del ejemplo inferior, `await Validator.validate(...)` rechaza un correo inválido del hijo con la ruta `contacts[0].email` o `by_name['primary'].email`. El anidamiento directo conserva rutas como `contact.email`. Las claves de diccionario usan su `repr` de Python, de modo que la puntuación de una clave sigue formando parte de ella.

Si un campo o elemento falla la conversión, se siguen esperando las reglas de sus hermanos convertidos correctamente, incluidos los campos válidos de un hijo convertido parcialmente. Si solo fallan constraints y el tipo base es válido, también se ejecutan las reglas del propio campo. El valor con tipo incompatible no ejecuta sus propias reglas. Los constraints de la colección se conservan junto a los fallos de sus hijos. Las reglas entre campos reciben la instancia del hijo, o un namespace con los atributos convertidos y valores predeterminados disponibles en el camino de error, no la colección padre.

## Validar una orden con registros anidados

El siguiente programa es independiente. Declara el formato de entrada, transforma un diccionario externo y solo utiliza la instancia después de validar. `forbid_unknown_fields=True` es una opción de `msgspec.Struct` que la metaclase de Orionis transmite; sin esa opción, los campos desconocidos no se rechazan de forma predeterminada. Una anotación opcional no crea un valor por defecto: usa `= None` si el cliente puede omitir el campo.

La conversión y los constraints estructurales ocurren antes de las reglas de aplicación. Una conversión fallida recoge errores y espera las reglas de campos y elementos con tipos compatibles. No se ejecutan reglas sobre un valor que no se convirtió a su tipo base declarado.

Los detalles se agrupan en `exception.errors`: cada campo contiene una lista de objetos `{"rule": "ge", "message": "..."}`. `rule` identifica el constraint o el `__code__` de la regla personalizada; no se deduce del mensaje. La lista completa de entidades está en `exception.failures`, `exception.failure` conserva el primer fallo y `exception.error()` ofrece el cuerpo serializable. El resumen usa el primer mensaje y añade `(and N more errors)` contando fallos, aunque varios pertenezcan al mismo campo. Los errores de formularios guardados en sesión conservan listas de mensajes para las plantillas.

El flujo HTTP y el contenedor eligen la entrada y esperan `validate`; este programa valida explícitamente para ser reproducible fuera de un servidor.

```python
import asyncio
from orionis.schemas import Schema
from orionis.schemas.fields import Field
from orionis.schemas.constraints import GreaterThan, MinLength
from orionis.schemas.rules import Email
from orionis.schemas.validator import Schema as Validator
from orionis.schemas.exceptions import ValidationException

class Line(Schema):
    sku: Field[str, MinLength(3)]
    quantity: Field[int, GreaterThan(0)]

class Order(Schema, forbid_unknown_fields=True):
    email: Field[str, Email()]
    lines: Field[list[Line], MinLength(1)]
    note: str | None = None

async def main() -> None:
    order = await Validator.validate({
        "email": "ada@example.com",
        "lines": [{"sku": "BK-1", "quantity": 2}],
    }, Order)
    assert order.lines[0].quantity == 2
    assert order.note is None
    try:
        await Validator.validate({
            "email": "ada@example.com",
            "lines": [{"sku": "BK-1", "quantity": 0}],
        }, Order)
    except ValidationException as error:
        assert error.failures
        assert error.error()["errors"] == error.errors
        assert error.errors["lines[0].quantity"][0]["rule"] == "gt"
    else:
        raise AssertionError("invalid order accepted")

asyncio.run(main())
```

### Varios errores del mismo campo

Este programa produce cuatro errores en dos campos y utiliza los mensajes declarados:

```python
import asyncio
from orionis.schemas import Schema
from orionis.schemas.constraints import Email, GreaterThanOrEqual, MinLength, MultipleOf
from orionis.schemas.exceptions import ValidationException
from orionis.schemas.fields import Field
from orionis.schemas.validator import Schema as Validator

class Purchase(Schema):
    quantity: Field[
        int, GreaterThanOrEqual(1, message="Quantity must be positive."),
        MultipleOf(2, message="Quantity must be even."),
    ]
    email: Field[
        str, MinLength(5, message="Email is too short."),
        Email(message="Email is invalid."),
    ]

async def main() -> None:
    try:
        await Validator.validate({"quantity": -3, "email": "x"}, Purchase)
    except ValidationException as error:
        assert error.message == "Quantity must be positive. (and 3 more errors)"
        assert error.errors["quantity"] == [
            {"rule": "ge", "message": "Quantity must be positive."},
            {"rule": "multiple_of", "message": "Quantity must be even."},
        ]
        assert [detail["rule"] for detail in error.errors["email"]] == [
            "min_length", "email",
        ]
    else:
        raise AssertionError("invalid purchase accepted")

asyncio.run(main())
```

## Fuentes y siguientes pasos

[validator.py](../../validator.py) · [validation.py](../../exceptions/validation.py) · [rules_executor.py](../../rules_executor.py)

[Volver al índice del módulo](README.md).
