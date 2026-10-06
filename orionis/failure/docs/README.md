# orionis.failure

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

The orionis.failure initializer exports 1 public symbols. This reference uses __all__, export routes, and current source files as evidence.

## Module structure

| Path | Responsibility |
| --- | --- |
| ../__init__.py | Defines package exports. |
| orionis.failure/ | Implementations and subpackages for those exports. |

## API reference

| Symbol | Verified import | Source | Declaration | Observed behavior |
| --- | --- | --- | --- | --- |
| Catch | from orionis.failure import Catch | [catch.py](../catch.py) | Catch | Exported public constant or alias. |
| Catch.exception | from orionis.failure import Catch | [catch.py](../catch.py) | async def exception(self, exception: BaseException, request: Request / TransportAdapter / None) -> Response / None | Handle an exception based on the current kernel context. Parameters ---------- exception : BaseException The exception instance to handle. request : Request / TransportAdapter / None, optional The HTTP request or transport adapter associated with the exception. Returns ------- None / Response This method performs side effects and may return a Response. Raises ------ RuntimeError If the application has no active scope or kernel context. Notes ----- Determines the context and delegates exception handling accordingly. |

## Usage examples

    from orionis.failure import Catch

The import path matches the API table. Import status: executed successfully under Python 3.14.3.

## Design characteristics

The package uses an explicit public surface. Private names are excluded; declarations link to their concrete owner.

## Performance and concurrency

No uniform guarantee is declared at package level. Inspect each linked file for I/O, coroutines, caches, locks, and shared state.

## Compatibility notes

Declared minimum: Python 3.14. Validation used Python 3.14.3. Dependency bounds are in pyproject.toml.

## Verification and limitations

Python files were analysed and exports verified. Failures from dependencies, callbacks, I/O, or configuration may propagate and are not presented as exhaustive.
