---
name: "Orionis Schemas and Validation"
description: "Use when defining or debugging Orionis validation schemas built on msgspec: Field aliases, constraint and document metadata, custom Rule classes, the multi-error FailureCollector, ValidationException and how the container auto-validates request payloads."
applyTo: "orionis/schemas/**,app/http/schemas/**"
---

# Schemas and validation

## Read the module docs first

`orionis/schemas/docs/README.md` (`.es.md`) is the manual: `Schema` +
`SchemaMeta`, the `fields.py` aliases, the 10 constraint dataclasses, the document
metadata, the 37 built-in rules with their exact signatures, `MetaCompiler`,
`FailureCollector`, `ValidationErrorParser`, `ValidationFailure` and
`ValidationException`. **Check it before assuming a rule or a constraint exists.**

This file only lists the invariants and traps.

## Declaration rules

Built on `msgspec.Struct` — **never Pydantic**.

```python
from orionis.schemas import Schema
from orionis.schemas.fields import Field
from orionis.schemas.constraints import MinLength
from orionis.schemas.rules import Email, StrongPassword

class LoginSchema(Schema):
    email: Field[str, Email()]
    password: Field[str, MinLength(8), StrongPassword()]
```

- Fields must be **annotations**, never assignments: `email: Field[...]`. Writing
  `email = Field[...]` makes msgspec ignore the field entirely (real bug, it
  silently reported only one error).
- There are **two classes named `Schema`**: the base for defining schemas
  (`orionis/schemas/schema.py`) and the static validator
  (`orionis/schemas/validator.py`). Real code imports the second as
  `from orionis.schemas.validator import Schema as Validator`.
- The `message=` keyword of the constraint dataclasses **is** honoured (it lands in
  `__orionis_constraints__` and the parser substitutes it). `Message` in
  `metadata.py` is the only way to customise a *type* error message.
- Metadata conflicts (duplicates, impossible ranges, unknown rules) raise **at
  class-definition time**, not at validation time.

## Custom rules

Subclass `Rule` and override **only** `enforce()`; `validate()` builds the
`ValidationFailure` from `__code__`/`__message__` and must not be touched.

```python
class Email(Rule):
    """Validate that the value is a syntactically valid email address."""

    __slots__ = ()
    __code__ = "email"
    __message__ = "The :attribute must be a valid email address."

    def enforce(self, value: object, instance: object) -> bool:  # noqa: ARG002
        """Return whether the value looks like an email address."""
        return isinstance(value, str) and _PATTERN.match(value) is not None
```

Every rule declares a class docstring and `__slots__ = ()`. Guard with `isinstance`:
a `Nullable[str]` field can hand you `None`. Precompile regexes at module level.

## Execution model (do not regress it)

- **The happy path is a single `msgspec.convert(payload, type=schema)`** in C
  (~1.75 µs end to end). Never add per-field Python work to that path.
- Only when the convert fails does `FailureCollector.collect()` run, re-converting
  field by field with a cached plan so it can report **every** error, recursing into
  nested schemas with dotted paths (`address.zip_code`).
- Custom rules run in the deferred `_enforce` step against a
  `SimpleNamespace(**converted_values)`. A rule is skipped when **its own** field
  failed conversion, but still runs when a sibling failed.
- `SchemaMeta` precompiles and caches the plan for every subclass at definition
  time; a struct that never went through `SchemaMeta` takes the cache-miss branch.
- `_collect_with_plan(plan, instance, prefix, failures)` is the single entry point.
  `RulesExecutor`/`_execute` were deleted as dead code — do not resurrect them.

## Wiring

- A parameter annotated with a `Schema` subclass makes the container validate the
  request body automatically (`is_schema` → `Schema.validate`). Controllers must
  never validate by hand.
- `ValidationException` exposes `.failures`, `.failure`, `.errors`
  (`{field: [messages]}`), `.message` and `.error()`. The HTTP layer turns it into
  422 JSON or a redirect back with flashed errors and input.
- A non-Mapping payload produces one failure with `field=""`.
- Rules that touch I/O (`Unique`, `ActiveUrl`) bridge to async with `Loop.runSync`.
  Inside a running loop that dispatches to a worker thread with its own event loop,
  so `Unique` opens a **disposable** `Connection` there; reusing the pooled one
  raises `InterfaceError: another operation is in progress`.

## Lint notes

- Imports used only inside schema annotations still evaluate at runtime (PEP 649 +
  metaclass) → file-level `# ruff: noqa: TC001`.
- `Choice["admin", "user"]` inside a class body triggers `UP037` + `F821`; declare
  the alias outside the class (`_Role = Choice["admin", "user"]`).
- A field or kwarg literally named `token=`/`password=`/`secret=` triggers
  `S105`/`S106` even in fixtures — rename it (`code`, `_CREDENTIAL`).
