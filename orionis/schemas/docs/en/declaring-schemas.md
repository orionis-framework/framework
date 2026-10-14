# Declaring schemas and converting data

The `Profile` example blocks run in order within the same module; the `Batch` and handler examples show separate cases. `Validator` aliases the validation utility, distinct from the declaration base.

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

### Structural constraints

`GreaterThan`, `GreaterThanOrEqual`, `LessThan`, `LessThanOrEqual`, `MultipleOf`, `Pattern`, `MinLength`, `MaxLength`, `TimezoneAware`, and `TimezoneNaive` compile into the low-level conversion descriptor. Conflicting, duplicate, impossible, or invalid combinations fail when the schema class is created.

### Application rules

Rules implement domain checks after conversion. They include strings, dates, numbers, cross-field comparisons, acceptance, passwords, files/images, network formats, URLs, JSON, UUID/ULID, MIME/size/dimensions, and database uniqueness. A plan walks nested schemas and containers and collects all failures instead of stopping at the first custom rule.

### Synchronous and asynchronous validation

`validate()` runs conversion and synchronous rule checks. `validateAsync()` also awaits native async rules and is the preferred path inside Orionis dependency injection. `Unique` uses the active connection/transaction asynchronously; its synchronous bridge may require an isolated connection when called inside an event loop.

### Documentation metadata

`Title`, `Description`, `Examples`, and `ExtraJsonSchema` feed JSON Schema/OpenAPI generation. `Extra` carries application-owned metadata. `Message` overrides type-mismatch text; many constraints/rules accept their own `message=` override.

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


### Await validation in async code

```python
import asyncio
from orionis.schemas.validator import Schema as Validator


async def example() -> None:
    profile = await Validator.validateAsync({"name": "Lin", "age": 21}, Profile)
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
