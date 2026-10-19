# Declaring schemas and converting data

The `Profile` example blocks run in order within the same module; the `Batch` and handler examples show separate cases. `Validator` aliases the validation utility, distinct from the declaration base.

Validation snippets run inside an async function or an async-aware shell. The standalone runner example below shows how to enter async code from a synchronous application.

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

## Core concepts

### Schema and Field

`Schema` supplies compact typed storage and `toDict()`. `Field` is `typing.Annotated`, not a runtime descriptor: `Field[str, MinLength(2)]` preserves the underlying `str` annotation while attaching metadata. `Choice`, `Nullable`, `AnyOf`, `Constant`, `Alias`, and `Static` are readable aliases for standard typing forms.

`toDict()` recursively converts nested `Schema` and plain `msgspec.Struct` instances into dictionaries, including instances inside dictionary values, lists, and tuples. Python field names, dictionary keys, and list/tuple types are preserved; other leaf values such as `datetime` and `Decimal` objects remain unchanged. The conversion does not mutate the source instance or its containers.

### Structural constraints

`GreaterThan`, `GreaterThanOrEqual`, `LessThan`, `LessThanOrEqual`, `MultipleOf`, `Pattern`, `MinLength`, `MaxLength`, `TimezoneAware`, and `TimezoneNaive` compile into the low-level conversion descriptor. Conflicting, duplicate, impossible, or invalid combinations fail when the schema class is created.

### Application rules

Rules implement domain checks after conversion. They include strings, dates, numbers, cross-field comparisons, acceptance, passwords, files/images, network formats, URLs, JSON, UUID/ULID, MIME/size/dimensions, and database uniqueness. A plan walks nested schemas and containers and collects all failures instead of stopping at the first custom rule.

### Always-asynchronous validation

`await Validator.validate(payload, schema)` converts the payload and completes every applicable rule before returning. There is no synchronous validation entry point. Every executable rule implements `async def enforce`, and validation always awaits it. Short pure checks stay on the caller's thread; native I/O uses the caller's event loop. `Unique` preserves the active connection and transaction.

### Documentation metadata

`Title`, `Description`, `Examples`, and `ExtraJsonSchema` feed JSON Schema/OpenAPI generation. `Extra` carries application-owned metadata. `Message` overrides type-mismatch text; many constraints/rules accept their own `message=` override.

## Common workflows

### Validate an HTTP/controller payload

Type-hint a container-invoked parameter with a concrete `Schema`. Orionis converts the appropriate request input and awaits validation before calling the handler. A failure becomes the framework's normal validation response.

### Validate manually

Always use `await Validator.validate`. At a synchronous application's outer boundary, run an async entry point with `asyncio.run(main())`; do not start another loop inside an active one. Do not use direct schema construction as a substitute for converting untrusted dictionaries.

### Customize messages

Attach `Message("...")` for wrong-type errors and `message=` on a constraint/rule for its own failure. Errors retain dotted/indexed paths for nested fields and collections.

### Write a custom rule

Subclass `Rule`, define stable `__code__`/`__message__`, and implement `async def enforce` for both pure checks and native asynchronous I/O. The inherited `validate` always awaits that method. Synchronous overrides are rejected at class declaration.

## Examples

### Convert and validate an untrusted mapping

```python
from orionis.schemas.validator import Schema as Validator

profile = await Validator.validate(
    {"name": "Grace", "age": 37, "newsletter": True},
    Profile,
)
assert isinstance(profile, Profile)
assert profile.newsletter is True
```


### Inspect grouped validation failures

```python
from orionis.schemas.exceptions import ValidationException

try:
    await Validator.validate({"name": "x", "age": 12}, Profile)
except ValidationException as exception:
    assert set(exception.errors) == {"name", "age"}
    assert len(exception.failures) == 2
    payload = exception.error()
    assert payload["message"]
else:
    raise AssertionError("invalid profile was accepted")
```


### Define and run a custom rule

```python
from orionis.schemas import Schema
from orionis.schemas.fields import Field
from orionis.schemas.rule import Rule
from orionis.schemas.validator import Schema as Validator


class Even(Rule):
    __code__ = "even"
    __message__ = "Value must be even."

    async def enforce(self, field: str, value: object, instance: object) -> bool:
        return isinstance(value, int) and value % 2 == 0


class Batch(Schema):
    size: Field[int, Even()]


assert (await Validator.validate({"size": 4}, Batch)).size == 4
```


### Await validation in async code

```python
import asyncio
from orionis.schemas.validator import Schema as Validator


async def example() -> None:
    profile = await Validator.validate({"name": "Lin", "age": 21}, Profile)
    assert profile.name == "Lin"


asyncio.run(example())
```


### Use schema parameters with container invocation

```python
from orionis.http import JSONResponse, Response


async def store_profile(payload: Profile) -> Response:
    return JSONResponse({"profile": payload.toDict()}, status_code=201)
```

## Configuration

The schemas package has no global configuration or environment variables. Every constraint and rule is declared on its field. I/O rules carry their own parameters—for example `Unique(table, column, connection=...)`—and consume already configured database/network services.

## Evidence and next steps

[schema.py](../../schema.py) · [compiler.py](../../compiler.py) · [validator.py](../../validator.py) · [fields.py](../../fields.py)

[Return to the module index](README.md).
