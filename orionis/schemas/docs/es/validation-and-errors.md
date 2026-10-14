# Validación, errores e integración

## Integración con Orionis

El contenedor detecta parámetros `Schema`, selecciona entrada y llama `validateAsync`. El kernel HTTP renderiza `ValidationException`. Realtime compila schemas para remotos y MCP los usa para entradas, JSON Schema de salida y errores de parámetros.

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

Instancias y planes son compactos y no retienen estado global. Reglas async preservan loop/transacción. Evite reglas síncronas con I/O en event loop y use `validateAsync`.

## Compatibilidad

Los schemas son `msgspec.Struct` y pueden codificarse con codecs compatibles. La declaración pública depende de anotaciones diferidas Python 3.14. Use metadata Orionis en vez de construir `msgspec.Meta` para conservar mensajes/documentación consistentes.

## Validar una orden con registros anidados

El siguiente programa es independiente. Declara el formato de entrada, transforma un diccionario externo y solo utiliza la instancia después de validar. `forbid_unknown_fields=True` es una opción de `msgspec.Struct` que la metaclase de Orionis transmite; sin esa opción, los campos desconocidos no se rechazan de forma predeterminada. Una anotación opcional no crea un valor por defecto: usa `= None` si el cliente puede omitir el campo.

La validación de conversión y constraints ocurre antes de las reglas de aplicación. Una conversión fallida recoge errores de esa fase; no garantiza que también se hayan ejecutado todas las reglas de negocio. En la fase de reglas sí se recorren los valores convertidos y sus objetos anidados. No bases la lógica de cliente en el número exacto de fallos de varias fases a la vez.

Los mensajes se agrupan en `exception.errors`, la lista completa está en `exception.failures` y `exception.error()` ofrece el cuerpo serializable. Devuelve campos y mensajes permitidos al cliente; evita incluir contraseñas o el payload íntegro en logs. El flujo HTTP y el contenedor eligen la entrada y esperan `validateAsync`; este programa valida explícitamente para ser reproducible fuera de un servidor.

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
    order = await Validator.validateAsync({
        "email": "ada@example.com",
        "lines": [{"sku": "BK-1", "quantity": 2}],
    }, Order)
    assert order.lines[0].quantity == 2
    assert order.note is None
    try:
        await Validator.validateAsync({
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
