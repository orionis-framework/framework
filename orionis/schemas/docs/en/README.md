# Schemas and validation

## Overview

An Orionis `Schema` is a `msgspec.Struct` processed by `SchemaMeta`. Fields use ordinary Python annotations; `Annotated`—aliased as `Field`—attaches constraints, rules, documentation, and custom messages. The metaclass compiles structural constraints and prebuilds rule plans when the class is created, keeping successful validation paths small.

The package separates declaration from validation. Direct construction trusts already typed Python values under `msgspec` constructor semantics. `await orionis.schemas.validator.Schema.validate(payload, schema)` converts untrusted payloads and raises an Orionis `ValidationException` containing field-indexed failures. Validation has one entry point and is always asynchronous, including schemas without custom rules.

## Requirements

- Python 3.14 or newer; schema compilation relies on deferred annotation evaluation.
- Explicit imports from `fields`, `constraints`, `metadata`, `rules`, `validator`, and `exceptions` for advanced features; the package root deliberately exports only `Schema`.
- A booted database connection for `Unique`, and network/file context for rules that perform those checks.

## Module learning path

- [Constraints, metadata, and reference](constraints-and-reference.md)
- [Declaring schemas and converting data](declaring-schemas.md)
- [Validation, errors, and integration](validation-and-errors.md)

Continue with: [http](../../../http/docs/en/README.md) · [database](../../../database/docs/en/README.md) · [mcp](../../../mcp/docs/en/README.md).

Examples that require bootstrap, a request, or external services state that context. Verification for this reconstruction is distinct from historical notes; a production integration is not assumed to have been executed.

- [Application rules and validation with I/O](application-rules.md)

## Bounded execution and performance

Rule plans use a process-local LRU capped at 1,024 schema types. Evicted types can be collected; their plans are rebuilt on subsequent use. Recursive child-plan warming is guarded and concurrent compilation is serialized. This changes retention, not validation rules, errors or serialization.
