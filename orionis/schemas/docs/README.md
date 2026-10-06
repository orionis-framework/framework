# orionis.schemas

> `orionis.schemas` provides compiled, typed request/data schemas with structural constraints, application rules, nested error collection, and async validation.

## Overview

An Orionis `Schema` is a `msgspec.Struct` processed by `SchemaMeta`. Fields use ordinary Python annotations; `Annotated`—aliased as `Field`—attaches constraints, rules, documentation, and custom messages. The metaclass compiles structural constraints and prebuilds rule plans when the class is created, keeping successful validation paths small.

The package separates declaration from validation. Direct construction trusts already typed Python values under `msgspec` constructor semantics. `orionis.schemas.validator.Schema.validate()` and `validateAsync()` convert untrusted payloads and raise an Orionis `ValidationException` containing field-indexed failures.

## Requirements

- Python 3.14 or newer; schema compilation relies on deferred annotation evaluation.
- Explicit imports from `fields`, `constraints`, `metadata`, `rules`, `validator`, and `exceptions` for advanced features; the package root deliberately exports only `Schema`.
- A booted database connection for `Unique`, and network/file context for rules that perform those checks.

## Quick start

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

Validation: **Executed successfully** on CPython 3.14.6.

## Core concepts

### Schema and Field

`Schema` supplies compact typed storage and `toDict()`. `Field` is `typing.Annotated`, not a runtime descriptor: `Field[str, MinLength(2)]` preserves the underlying `str` annotation while attaching metadata. `Choice`, `Nullable`, `AnyOf`, `Constant`, `Alias`, and `Static` are readable aliases for standard typing forms.

### Structural constraints

`GreaterThan`, `GreaterThanOrEqual`, `LessThan`, `LessThanOrEqual`, `MultipleOf`, `Pattern`, `MinLength`, `MaxLength`, `TimezoneAware`, and `TimezoneNaive` compile into the low-level conversion descriptor. Conflicting, duplicate, impossible, or invalid combinations fail when the schema class is created.

### Application rules

Rules implement domain checks after conversion. They include strings, dates, numbers, cross-field comparisons, acceptance, passwords, files/images, network formats, URLs, JSON, UUID/ULID, MIME/size/dimensions, and database uniqueness. A plan walks nested schemas and containers and collects all failures instead of stopping at the first custom rule.

### Synchronous and asynchronous validation

`validate()` runs conversion and synchronous rule checks. `validateAsync()` also awaits native async rules and is the preferred path inside Orionis dependency injection. `Unique` uses the active connection/transaction asynchronously; its synchronous bridge may require an isolated connection when called inside an event loop.

### Documentation metadata

`Title`, `Description`, `Examples`, and `ExtraJsonSchema` feed JSON Schema/OpenAPI generation. `Extra` carries application-owned metadata. `Message` overrides type-mismatch text; many constraints/rules accept their own `message=` override.

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

## Public API

`from orionis.schemas import Schema` is the only root export. Advanced APIs are intentionally explicit:

- `orionis.schemas.fields`: `Field`, `Choice`, `Nullable`, `AnyOf`, `Constant`, `Alias`, `Static`.
- `orionis.schemas.constraints`: structural constraints plus all bundled rule classes.
- `orionis.schemas.metadata`: `Title`, `Description`, `Examples`, `ExtraJsonSchema`, `Extra`, `Message`.
- `orionis.schemas.validator.Schema`: static `validate(payload, schema)` and `validateAsync(payload, schema)` utility; alias it as `Validator` to avoid confusing it with the declaration base.
- `orionis.schemas.rule.Rule`: base for custom rules.
- `orionis.schemas.exceptions.ValidationException`: `failures`, first `failure`, grouped `errors`, summary `message`, and serializable `error()`.

## Common workflows

### Validate an HTTP/controller payload

Type-hint a container-invoked parameter with a concrete `Schema`. Orionis converts the appropriate request input and awaits validation before calling the handler. A failure becomes the framework's normal validation response.

### Validate manually

Use `Validator.validate` in synchronous code and `await Validator.validateAsync` in async code. Do not use direct schema construction as a substitute for converting untrusted dictionaries.

### Customize messages

Attach `Message("...")` for wrong-type errors and `message=` on a constraint/rule for its own failure. Errors retain dotted/indexed paths for nested fields and collections.

### Write a custom rule

Subclass `Rule`, define stable `__code__`/`__message__`, and implement `enforce`. For native async I/O, override `enforceAsync`; use async validation so it does not block the event loop.

## Examples

### Convert and validate an untrusted mapping

```python
from orionis.schemas.validator import Schema as Validator

profile = Validator.validate(
    {"name": "Grace", "age": 37, "newsletter": True},
    Profile,
)
assert isinstance(profile, Profile)
assert profile.newsletter is True
```

Validation: **Executed successfully** on CPython 3.14.6.

### Inspect grouped validation failures

```python
from orionis.schemas.exceptions import ValidationException

try:
    Validator.validate({"name": "x", "age": 12}, Profile)
except ValidationException as exception:
    assert set(exception.errors) == {"name", "age"}
    assert len(exception.failures) == 2
    payload = exception.error()
    assert payload["message"]
else:
    raise AssertionError("invalid profile was accepted")
```

Validation: **Executed successfully** on CPython 3.14.6; both field failures were collected.

### Define and run a custom rule

```python
from orionis.schemas import Schema
from orionis.schemas.fields import Field
from orionis.schemas.rule import Rule
from orionis.schemas.validator import Schema as Validator


class Even(Rule):
    __code__ = "even"
    __message__ = "Value must be even."

    def enforce(self, field: str, value: object, instance: object) -> bool:
        return isinstance(value, int) and value % 2 == 0


class Batch(Schema):
    size: Field[int, Even()]


assert Validator.validate({"size": 4}, Batch).size == 4
```

Validation: **Executed successfully** on CPython 3.14.6.

### Await validation in async code

```python
import asyncio
from orionis.schemas.validator import Schema as Validator


async def example() -> None:
    profile = await Validator.validateAsync({"name": "Lin", "age": 21}, Profile)
    assert profile.name == "Lin"


asyncio.run(example())
```

Validation: **Executed successfully** on CPython 3.14.6.

### Use schema parameters with container invocation

```python
from orionis.http import Response


async def store_profile(payload: Profile) -> Response:
    return Response.json({"profile": payload.toDict()}, status=201)
```

Validation: **Import and syntax validated** on CPython 3.14.6; automatic payload selection and validation require Orionis container/HTTP invocation.

## Configuration

The schemas package has no global configuration or environment variables. Every constraint and rule is declared on its field. I/O rules carry their own parameters—for example `Unique(table, column, connection=...)`—and consume already configured database/network services.

## Integration with Orionis

The container detects `Schema` parameters, selects route input, and calls `validateAsync`. The HTTP kernel renders `ValidationException` as structured validation errors. Realtime compiles schema parameter plans for remote methods, and MCP uses schemas for tool inputs, output JSON Schema, and invalid-parameter responses.

Schema documentation metadata is consumed by JSON Schema/OpenAPI-related compilers without making those concerns part of instance validation.

## Errors and edge cases

- Unknown fields, missing required fields, incompatible values, and structural bounds become `ValidationException` under `Validator`.
- Direct `msgspec.convert` raises `msgspec.ValidationError`, not the grouped Orionis exception.
- Direct construction does not run the full untrusted-payload validation pipeline.
- Rule ordering follows field metadata order; failures are accumulated across fields and nested containers.
- `Message` covers type mismatch, not every rule. Put `message=` on the exact constraint/rule being customized.
- `ActiveUrl` performs network resolution; `Unique` performs database I/O; file/image rules require an uploaded-file-like object.
- Conflicting metadata such as two `MinLength` values or mutually exclusive timezone constraints fails at class declaration.

## Performance and concurrency

Structural metadata and rule traversal plans are compiled at class creation and cached by schema type. Successful conversion uses a single optimized `msgspec.convert` call. Detailed field-by-field inspection is reserved for failure reporting.

Schema instances and metadata plans are compact; validation itself retains no global request state. Async rules preserve the caller's event loop and transaction when implemented natively. Avoid synchronous I/O rules in event-loop code and use `validateAsync` for predictable concurrency.

## Compatibility

Schema classes are `msgspec.Struct` subclasses and can be encoded by supported `msgspec` codecs. Public declaration relies on Python 3.14 deferred annotations. Constraint semantics follow Orionis' compiler; application code should import Orionis metadata rather than constructing `msgspec.Meta` directly when it needs consistent messages and documentation.

## Verification notes

- `tests/schemas`: **450 test methods passed** with the Orionis runner on CPython 3.14.6.
- Six bilingual documentation programs were compiled; five standalone programs were executed successfully.
- The container/HTTP handler example was import/syntax validated because automatic injection requires a live request scope.
- Evidence covered metaclass compilation, constraints/conflicts, all bundled rule families, nested failures, async validation, metadata, package boundaries, and integration with database-backed uniqueness.

