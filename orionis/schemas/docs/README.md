# orionis.schemas

> API reference derived from the current implementation.

## Table of contents

- Requirements
- Functional overview
- Module structure
- API reference
- Usage examples
- Design characteristics
- Performance and concurrency
- Compatibility notes
- Verification and limitations

## Requirements

Python 3.14 or newer, as declared by pyproject.toml.

## Functional overview

The orionis.schemas initializer exports 1 public symbols. This reference uses __all__, export routes, and current source files as evidence.

## Module structure

| Path | Responsibility |
| --- | --- |
| ../__init__.py | Defines package exports. |
| orionis.schemas/ | Implementations and subpackages for those exports. |

## API reference

| Symbol | Verified import | Source | Declaration | Observed behavior |
| --- | --- | --- | --- | --- |
| Schema | from orionis.schemas import Schema | [schema.py](../schema.py) | Schema | Define the base class for Orionis schema declarations. Notes ----- Inherit ``msgspec.Struct`` behavior and the ``SchemaMeta`` metaclass pipeline, which compiles validation metadata and stores Orionis custom metadata on the resulting class. |
| Schema.toDict | from orionis.schemas import Schema | [schema.py](../schema.py) | def toDict(self) -> dict[str, object] | Convert the schema instance into a dictionary. Returns ------- dict[str, object] Dictionary containing the schema fields and their values. |

## Usage examples

    from orionis.schemas import Schema

The import path matches the API table. Import status: executed successfully under Python 3.14.3.

## Design characteristics

The package uses an explicit public surface. Private names are excluded; declarations link to their concrete owner.

## Performance and concurrency

No uniform guarantee is declared at package level. Inspect each linked file for I/O, coroutines, caches, locks, and shared state.

## Compatibility notes

Declared minimum: Python 3.14. Validation used Python 3.14.3. Dependency bounds are in pyproject.toml.

## Verification and limitations

Python files were analysed and exports verified. Failures from dependencies, callbacks, I/O, or configuration may propagate and are not presented as exhaustive.
