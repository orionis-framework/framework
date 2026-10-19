# Validación, errores e integración

## Integración con Orionis

El contenedor detecta parámetros `Schema`, selecciona entrada y espera `validate`. El kernel HTTP renderiza `ValidationException`. Realtime compila schemas para remotos y MCP espera la validación de entradas y salidas estructuradas, incluidos los resultados en streaming.

La metadata documental alimenta compiladores JSON Schema/OpenAPI sin formar parte de la validación de instancia.

## Errores y casos límite

- Campos obligatorios ausentes, valores incompatibles y límites producen `ValidationException` bajo `Validator`.
- `msgspec.convert` directo lanza `msgspec.ValidationError`, no la excepción agrupada.
- Construcción directa no ejecuta todo el pipeline no confiable.
- El orden de reglas sigue metadata; se acumulan fallos entre campos y anidados.
- `Message` cubre tipo, no toda regla; use `message=` en la regla exacta.
- `ActiveUrl` usa red; `Unique` usa database; reglas de archivo/imagen requieren upload compatible.
- Metadata conflictiva falla al declarar la clase.

## Rendimiento y concurrencia

Metadata estructural y planes se compilan al crear la clase y cachean por tipo. La conversión exitosa usa una llamada optimizada `msgspec.convert`; inspección detallada se reserva para errores.

Instancias y planes son compactos y no retienen estado global. Las reglas asíncronas preservan loop/transacción. Espere siempre `validate`, incluso en schemas sin reglas de I/O. Cada regla implementa `async def enforce`; use allí I/O asíncrono nativo para no bloquear el loop. Los checks puros no necesitan hilos auxiliares.

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

Si un campo o elemento falla la conversión, se siguen esperando las reglas de sus hermanos convertidos correctamente, incluidos los campos válidos de un hijo convertido parcialmente. El valor incompatible no ejecuta sus propias reglas. Los constraints de la colección se conservan junto a los fallos de sus hijos. Las reglas entre campos reciben la instancia del hijo, o sus campos convertidos correctamente en el camino de error, no la colección padre.

## Validar una orden con registros anidados

El siguiente programa es independiente. Declara el formato de entrada, transforma un diccionario externo y solo utiliza la instancia después de validar. `forbid_unknown_fields=True` es una opción de `msgspec.Struct` que la metaclase de Orionis transmite; sin esa opción, los campos desconocidos no se rechazan de forma predeterminada. Una anotación opcional no crea un valor por defecto: usa `= None` si el cliente puede omitir el campo.

La conversión y los constraints estructurales ocurren antes de las reglas de aplicación. Una conversión fallida recoge errores y espera las reglas de campos y elementos hermanos convertidos correctamente. No se pueden ejecutar reglas sobre un valor que no se convirtió a su tipo declarado. No bases la lógica de cliente en el número exacto de fallos de varias fases a la vez.

Los mensajes se agrupan en `exception.errors`, la lista completa está en `exception.failures` y `exception.error()` ofrece el cuerpo serializable. Devuelve campos y mensajes permitidos al cliente; evita incluir contraseñas o el payload íntegro en logs. El flujo HTTP y el contenedor eligen la entrada y esperan `validate`; este programa valida explícitamente para ser reproducible fuera de un servidor.

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
    else:
        raise AssertionError("invalid order accepted")

asyncio.run(main())
```

## Fuentes y siguientes pasos

[validator.py](../../validator.py) · [validation.py](../../exceptions/validation.py) · [rules_executor.py](../../rules_executor.py)

[Volver al índice del módulo](README.md).
