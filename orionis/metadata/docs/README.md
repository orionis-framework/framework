# orionis.metadata

> `orionis.metadata` exposes the canonical identity, release, compatibility, and project links of the Orionis distribution.

## Overview

This package is a constants-only metadata surface. It lets framework code, console commands, packaging checks, and applications read the same project identity without parsing `pyproject.toml` at runtime.

The package root re-exports every public value from `orionis.metadata.framework`. Values are immutable strings except for `PYTHON_REQUIRES`, which is a tuple of integers.

## Requirements

- Python 3.14 or newer, as declared by `PYTHON_REQUIRES`.
- No application boot, container, environment variable, filesystem access, or network access is required to import the package.

## Quick start

```python
from orionis.metadata import NAME, PYTHON_REQUIRES, VERSION

assert NAME == "orionis"
assert PYTHON_REQUIRES == (3, 14)
major, minor, patch = (int(part) for part in VERSION.split("."))
print(NAME, (major, minor, patch))
```

Validation: **Executed successfully** on CPython 3.14.6.

## Core concepts

### One canonical runtime surface

`framework.py` owns ten public constants. `orionis.metadata.__init__` imports them by reference and lists exactly those names in `__all__`. Consumers can use package-level imports while tools that need the grouped namespace can import `framework`.

### Release metadata

`VERSION` is a three-segment numeric release string. `NAME`, `DESCRIPTION`, `AUTHOR`, and `AUTHOR_EMAIL` mirror the distribution manifest. The repository tests detect drift between these values and `pyproject.toml`.

### Compatibility metadata

`PYTHON_REQUIRES` stores the minimum interpreter as `(major, minor)`, making direct comparison with `sys.version_info` possible. It is intentionally not a packaging requirement string; the manifest derives the equivalent `>=major.minor` form.

### Project locations

`API`, `DOCS`, `FRAMEWORK`, and `SKELETON` are absolute HTTPS URLs for PyPI JSON data, documentation, and the two source repositories. The constants describe locations; importing the module never contacts them.

## Module structure

| Path | Responsibility |
|---|---|
| `framework.py` | Defines the ten canonical immutable metadata values. |
| `__init__.py` | Re-exports those values and declares the exact public API. |
| `icon.svg` | Package artwork; it is not imported by the Python API. |

## Public API

| Constant | Meaning |
|---|---|
| `NAME` | Distribution/import identity, `orionis`. |
| `VERSION` | Current three-part framework release. |
| `DESCRIPTION` | Single-line distribution summary. |
| `AUTHOR` / `AUTHOR_EMAIL` | Maintainer identity and contact. |
| `PYTHON_REQUIRES` | Minimum Python `(major, minor)` tuple. |
| `API` | PyPI JSON endpoint for the distribution. |
| `DOCS` | Documentation root. |
| `FRAMEWORK` | Main source repository. |
| `SKELETON` | Application skeleton repository. |

The exact current values are source-controlled in `framework.py`. Treat them as release data: read them freely, but update them only as part of the matching release or project-metadata change.

## Common workflows

### Display framework information

Import package-level constants to build an about screen, diagnostic header, or user-agent component. Do not copy version literals into downstream modules.

### Enforce the interpreter floor

Compare the leading elements of `sys.version_info` with `PYTHON_REQUIRES`. Packaging tools should continue using `project.requires-python` from the distribution metadata rather than importing code during installation.

### Link to project resources

Use `DOCS`, `FRAMEWORK`, or `SKELETON` when framework-owned output needs stable project links. `API` is an endpoint identifier, not a promise that a network request will succeed.

### Prepare a release

Keep `VERSION`, package name, description, author information, Python requirement, and project URLs synchronized with `pyproject.toml`. The metadata test suite checks that contract.

## Examples

### Inspect all supported exports

```python
import orionis.metadata as metadata

values = {name: getattr(metadata, name) for name in metadata.__all__}
assert set(values) == {
    "API", "AUTHOR", "AUTHOR_EMAIL", "DESCRIPTION", "DOCS",
    "FRAMEWORK", "NAME", "PYTHON_REQUIRES", "SKELETON", "VERSION",
}
assert all(isinstance(value, (str, tuple)) for value in values.values())
```

Validation: **Executed successfully** on CPython 3.14.6.

### Check interpreter compatibility

```python
import sys
from orionis.metadata import PYTHON_REQUIRES

running = sys.version_info[: len(PYTHON_REQUIRES)]
if running < PYTHON_REQUIRES:
    required = ".".join(map(str, PYTHON_REQUIRES))
    raise RuntimeError(f"Orionis requires Python {required}+")
```

Validation: **Executed successfully** on CPython 3.14.6.

### Parse the release for comparison

```python
from orionis.metadata import VERSION

release = tuple(int(segment) for segment in VERSION.split("."))
assert len(release) == 3
assert release > (0, 0, 0)
print(release)
```

Validation: **Executed successfully** on CPython 3.14.6.

### Build a PyPI endpoint without duplicating it

```python
from urllib.parse import urlparse
from orionis.metadata import API, NAME

assert API == f"https://pypi.org/pypi/{NAME}/json"
assert urlparse(API).scheme == "https"
```

Validation: **Executed successfully** on CPython 3.14.6; no network request was made.

## Configuration

The module has no runtime configuration and reads no environment variables. Its values are Python constants maintained with the project release. `pyproject.toml` is the packaging declaration; repository tests compare the overlapping fields but production imports do not parse that file.

## Integration with Orionis

The application version guard and console information commands consume these constants. Packaging metadata and runtime reporting therefore share the same identity and compatibility floor. Importing `orionis.metadata` is safe before an `Application` exists and does not touch the service container.

## Errors and edge cases

- `VERSION` is a plain release string, not a complete PEP 440 parser or range object.
- `PYTHON_REQUIRES` contains only major and minor; compare only the same prefix of `sys.version_info`.
- The URL constants are not checked for reachability at import time.
- Runtime assignment can rebind a module attribute because Python modules are mutable; consumers should treat exported constants as read-only.
- Installed wheels may not contain the repository's `pyproject.toml`; runtime use does not depend on its presence.

## Performance and concurrency

Import work is limited to binding strings, one tuple, and package re-exports. There is no I/O, locking, caching, mutable collection, async work, or per-request state. Concurrent reads are safe under normal Python module semantics.

## Compatibility

`PYTHON_REQUIRES == (3, 14)` is the authoritative runtime floor in this module and matches the project manifest during repository verification. The public API consists only of the ten names in `__all__`; adding or removing a constant is an API and release-tooling change.

## Verification notes

- `tests/metadata`: **38 test methods passed** with the Orionis runner on CPython 3.14.6.
- Five bilingual documentation programs were compiled and executed successfully.
- Tests verify exact exports, immutability shape, identifiers, URLs, version/contact formats, Python compatibility, and agreement with `pyproject.toml`.

