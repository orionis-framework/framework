# Constraints, metadata, and reference

## Public API

`from orionis.schemas import Schema` is the only root export. Advanced APIs are intentionally explicit:

- `orionis.schemas.fields`: `Field`, `Choice`, `Nullable`, `AnyOf`, `Constant`, `Alias`, `Static`.
- `orionis.schemas.constraints`: structural constraints plus all bundled rule classes.
- `orionis.schemas.metadata`: `Title`, `Description`, `Examples`, `ExtraJsonSchema`, `Extra`, `Message`.
- `orionis.schemas.validator.Schema`: static `validate(payload, schema)` and `validateAsync(payload, schema)` utility; alias it as `Validator` to avoid confusing it with the declaration base.
- `orionis.schemas.rule.Rule`: base for custom rules.
- `orionis.schemas.exceptions.ValidationException`: `failures`, first `failure`, grouped `errors`, summary `message`, and serializable `error()`.

## Module structure

| Path | Responsibility |
|---|---|
| `schema.py` | `Schema`, PEP 649-aware metaclass, constraint compilation, plan warming. |
| `fields.py` | Readable aliases for standard typing forms. |
| `constraints.py`, `compiler.py` | Structural metadata and conflict-safe `msgspec.Meta` compilation. |
| `rule.py`, `rules/` | Rule base and synchronous/asynchronous domain rules. |
| `validator.py`, `rules_executor.py` | Payload conversion and cached nested rule execution. |
| `failure_collector.py`, `exception_parser.py` | Multi-field conversion failure recovery and messages. |
| `metadata.py`, `meta/` | Documentation, message, and metadata marker types. |
| `entities/failure.py`, `exceptions/validation.py` | Immutable failure records and grouped exception output. |

## Evidence and next steps

[constraints.py](../../constraints.py) · [metadata.py](../../metadata.py) · [rule.py](../../rule.py)

[Return to the module index](README.md).
