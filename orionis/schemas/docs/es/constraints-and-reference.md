# Constraints, metadatos y referencia

## API pública

`from orionis.schemas import Schema` es el único export raíz. APIs avanzadas son explícitas:

- `orionis.schemas.fields`: `Field`, `Choice`, `Nullable`, `AnyOf`, `Constant`, `Alias`, `Static`.
- `orionis.schemas.constraints`: constraints estructurales y reglas incluidas.
- `orionis.schemas.metadata`: `Title`, `Description`, `Examples`, `ExtraJsonSchema`, `Extra`, `Message`.
- `orionis.schemas.validator.Schema`: `validate`/`validateAsync`; use alias `Validator`.
- `orionis.schemas.rule.Rule`: base de reglas personalizadas.
- `ValidationException`: `failures`, `failure`, `errors`, `message` y `error()`.

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

## Fuentes y siguientes pasos

[constraints.py](../../constraints.py) · [metadata.py](../../metadata.py) · [rule.py](../../rule.py)

[Volver al índice del módulo](README.md).
