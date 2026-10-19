# Application rules and validation with I/O

Constraints describe structural bounds compiled at class declaration. A `Rule` checks an application condition after type conversion. Combine them using `Field[T, ...]`; `Field` aliases `typing.Annotated`, not a function accepting `default=`.

The 47 bundled validations comprise 37 executable rules and 10 compiled structural constraints. All executable rules expose the same mandatory asynchronous `enforce` method; structural constraints remain declaration metadata, not a second execution API.

## Choose a bundled rule

| Need | Rules and relevant parameters |
|---|---|
| Text | `Alpha(ascii_only=False)`, `Ascii`, `Lowercase`, `Uppercase`, `Encoding(encoding="utf-8")`. |
| Prefixes and suffixes | `StartsWith(*prefixes)`, `EndsWith(*suffixes)`, `DoesntStartWith(*prefixes)`, `DoesntEndWith(*suffixes)`. |
| Formats | `Email`, `Json`, `IpAddress(version=4)`, `MacAddress`, `Uuid(version=None)`, `Ulid`. Use `IpAddress(version=None)` to permit IPv4 or IPv6. |
| Size | `Between(minimum, maximum)`, `Size(size)`, `MaxDigits(maximum)`, `DecimalPlaces(minimum, maximum=None)`, `Integer`. |
| Dates | `DateFormat(*formats)`, `After(reference=None)`, `AfterOrEqual`, `Before`, `BeforeOrEqual`. Temporal comparisons share normalization; check the date type declared by your schema. |
| Related fields | `ConfirmPassword(other_field="password")`, `GreaterThanOrEqualField(other_field)`, `LessThanOrEqualField(other_field)`. Put `ConfirmPassword` on the confirmation. |
| Values and secrets | `Accepted`, `Different(*values)`, `StrongPassword`. `Different` compares configured values, not another field. |
| Files | `File`, `Image`, `MimeTypes(*mime_types)`, `Dimensions(...)`. They require a compatible file object; a client-provided path is not an upload. |
| External services | `ActiveUrl`, `Unique(table, column, *, ignore=None, ignore_column="id", connection=None)`. |

All accept the keyword option `message=`. `Between` and `Size` measure numeric magnitude, text/collection length, and upload size in kilobytes. `Dimensions` accepts `width`, `height`, `min_width`, `max_width`, `min_height`, `max_height`, `ratio`, `min_ratio`, and `max_ratio`; ratios may be numbers or strings such as `"3/2"`. Image inspection reads headers; it does not convert or sanitize a file. Rules that read upload contents offload the synchronous file reader so disk-backed uploads do not block the event loop.

`StrongPassword` requires at least eight characters, an ASCII uppercase letter, an ASCII lowercase letter, and a digit. It does not require a symbol or check breached passwords. Validation does not replace [hashing](../../../hashing/docs/en/README.md).

## Combine registration and confirmation

The complete example below validates registration with explicit acceptance and confirmation. Password policy applies to the original value, and comparison applies to its confirmation. This example neither persists passwords nor authenticates users.

## Validation that queries other services

`ActiveUrl` checks hostname DNS resolution, not whether an HTTP resource exists or is safe to download. `await Validator.validate(...)` uses loop-based resolution without blocking the caller's event loop. Apply a resource-access policy independent of format validation.

`Unique` needs a ready Database service. Validation awaits its native I/O and preserves the active connection/transaction. Validation does not guarantee uniqueness against races; also define a database uniqueness constraint and handle persistence conflicts. Never derive `table`, `column`, `ignore_column`, or the connection directly from untrusted input.

## Write a custom rule

Inherit from `Rule`, set `__code__` and `__message__`, and implement `async def enforce(field, value, instance) -> bool`, including for pure predicates. Returning false creates a failure; `instance` allows sibling-field checks. `Rule.validate` always awaits `enforce`; there is no alternate enforcement method or synchronous fallback. Declaring a synchronous override raises `TypeError` when the rule class is created. Use native `await` for I/O, and do not hide blocking I/O inside `enforce`. Short pure checks remain on the caller's thread without worker offloading. Keep rules free from mutable per-request state: schemas and their plans are reused.

```python
from orionis.schemas.rule import Rule

class Even(Rule):
    __code__ = "even"
    __message__ = "Value must be even."

    async def enforce(self, field: str, value: object, instance: object) -> bool:
        return isinstance(value, int) and value % 2 == 0
```

Combine `Even()` with `Field[int, Even()]`. Invalid options or incompatible constraints fail at schema declaration; fix the declaration instead of converting a programming error into a user failure.

Run the validation snippet below inside an async function or an async-aware shell.

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

registration = await Validator.validate({
    "email": "ada@example.com",
    "password": "Example42",
    "password_confirmation": "Example42",
    "accepted_terms": True,
}, Registration)
assert registration.email == "ada@example.com"
```

Sources: [Rule](../../rule.py) · [Rules](../../rules/__init__.py) · [Validator](../../validator.py).

[Index](README.md).
