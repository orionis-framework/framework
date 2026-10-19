# Validation, errors, and integration

## Integration with Orionis

The container detects `Schema` parameters, selects route input, and awaits `validate`. The HTTP kernel renders `ValidationException` as structured validation errors. Realtime compiles schema parameter plans for remote methods, and MCP awaits schema validation for tool inputs and structured output, including streamed results.

Schema documentation metadata is consumed by JSON Schema/OpenAPI-related compilers without making those concerns part of instance validation.

## Errors and edge cases

- Missing required fields, incompatible values, and structural bounds become `ValidationException` under `Validator`.
- Direct `msgspec.convert` raises `msgspec.ValidationError`, not the grouped Orionis exception.
- Direct construction does not run the full untrusted-payload validation pipeline.
- Rule ordering follows field metadata order; failures are accumulated across fields and nested containers.
- `Message` covers type mismatch, not every rule. Put `message=` on the exact constraint/rule being customized.
- `ActiveUrl` performs network resolution; `Unique` performs database I/O; file/image rules require an uploaded-file-like object.
- Conflicting metadata such as two `MinLength` values or mutually exclusive timezone constraints fails at class declaration.

## Performance and concurrency

Structural metadata and rule traversal plans are compiled at class creation and cached by schema type. Successful conversion uses a single optimized `msgspec.convert` call. Detailed field-by-field inspection is reserved for failure reporting.

Schema instances and metadata plans are compact; validation itself retains no global request state. Asynchronous rules preserve the caller's event loop and transaction. Always await `validate`, even for schemas with no I/O rules. Every rule implements `async def enforce`; use native asynchronous I/O there to avoid blocking the loop. Pure checks do not require worker threads.

## Compatibility

Schema classes are `msgspec.Struct` subclasses and can be encoded by supported `msgspec` codecs. Public declaration relies on Python 3.14 deferred annotations. Constraint semantics follow Orionis' compiler; application code should import Orionis metadata rather than constructing `msgspec.Meta` directly when it needs consistent messages and documentation.

Validation now has only the asynchronous `validate` entry point. Migrate every caller to `await Validator.validate(...)`; synchronous calls and the former alternate entry point are no longer supported. Custom rules must implement `async def enforce`, and direct enforcement calls must also be awaited. Failure collection awaits rules on conversion-error paths.

## Rules inside schema collections

Child schema rules run for direct nested fields and for schemas inside lists, dictionary values, tuples, sets and frozensets, including nested collections, optional values and supported collection aliases such as `Sequence` and `Mapping`. These are Orionis checks in addition to msgspec's type conversion and compiled structural constraints; no manual per-element validation is required.

```python
class Contact(Schema):
    email: Field[str, Email()]

class Accounts(Schema):
    contacts: list[Contact]
    by_name: dict[str, Contact]
```

With the imports from the example below, `await Validator.validate(...)` rejects an invalid child email as `contacts[0].email` or `by_name['primary'].email`. Direct nesting still reports paths such as `contact.email`. Dictionary keys are represented with Python `repr`, so punctuation inside a key stays part of that key.

If a field or collection item fails conversion, rules still run on its successfully converted siblings, including valid fields of a partially converted child. The incompatible value does not run its own rules. Collection-level constraints are preserved alongside child failures. Cross-field rules receive the child instance, or its successfully converted fields on the error path, rather than the parent collection.

## Validate an order with nested records

This is a standalone program. It declares the input shape, converts an external dictionary, and uses the instance only after validation. `forbid_unknown_fields=True` is a `msgspec.Struct` option forwarded by the Orionis metaclass; unknown fields are not rejected by default without this option. An optional annotation does not create a default: use `= None` if the client may omit the field.

Conversion and structural constraints run before application rules. Failed conversion collects errors and awaits rules on successfully converted sibling fields and collection items. Rules cannot run on a value that did not convert to its declared type. Client logic should not depend on an exact count of failures from several stages at once.

Messages are grouped in `exception.errors`, the full list is in `exception.failures`, and `exception.error()` supplies a serializable body. Return permitted fields and messages to clients; avoid logging passwords or complete payloads. HTTP/container invocation chooses input and awaits `validate`; this program validates explicitly so it can run without a server.

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

## Evidence and next steps

[validator.py](../../validator.py) · [validation.py](../../exceptions/validation.py) · [rules_executor.py](../../rules_executor.py)

[Return to the module index](README.md).
