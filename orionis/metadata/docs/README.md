# orionis.metadata

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

The orionis.metadata initializer exports 10 public symbols. This reference uses __all__, export routes, and current source files as evidence.

## Module structure

| Path | Responsibility |
| --- | --- |
| ../__init__.py | Defines package exports. |
| orionis.metadata/ | Implementations and subpackages for those exports. |

## API reference

| Symbol | Verified import | Source | Declaration | Observed behavior |
| --- | --- | --- | --- | --- |
| API | from orionis.metadata import API | [framework.py](../framework.py) | exported constant or alias | Exported public constant or alias. |
| AUTHOR | from orionis.metadata import AUTHOR | [framework.py](../framework.py) | exported constant or alias | Exported public constant or alias. |
| AUTHOR_EMAIL | from orionis.metadata import AUTHOR_EMAIL | [framework.py](../framework.py) | exported constant or alias | Exported public constant or alias. |
| DESCRIPTION | from orionis.metadata import DESCRIPTION | [framework.py](../framework.py) | exported constant or alias | Exported public constant or alias. |
| DOCS | from orionis.metadata import DOCS | [framework.py](../framework.py) | exported constant or alias | Exported public constant or alias. |
| FRAMEWORK | from orionis.metadata import FRAMEWORK | [framework.py](../framework.py) | exported constant or alias | Exported public constant or alias. |
| NAME | from orionis.metadata import NAME | [framework.py](../framework.py) | exported constant or alias | Exported public constant or alias. |
| PYTHON_REQUIRES | from orionis.metadata import PYTHON_REQUIRES | [framework.py](../framework.py) | exported constant or alias | Exported public constant or alias. |
| SKELETON | from orionis.metadata import SKELETON | [framework.py](../framework.py) | exported constant or alias | Exported public constant or alias. |
| VERSION | from orionis.metadata import VERSION | [framework.py](../framework.py) | exported constant or alias | Exported public constant or alias. |

## Usage examples

    from orionis.metadata import API

The import path matches the API table. Import status: executed successfully under Python 3.14.3.

## Design characteristics

The package uses an explicit public surface. Private names are excluded; declarations link to their concrete owner.

## Performance and concurrency

No uniform guarantee is declared at package level. Inspect each linked file for I/O, coroutines, caches, locks, and shared state.

## Compatibility notes

Declared minimum: Python 3.14. Validation used Python 3.14.3. Dependency bounds are in pyproject.toml.

## Verification and limitations

Python files were analysed and exports verified. Failures from dependencies, callbacks, I/O, or configuration may propagate and are not presented as exhaustive.
