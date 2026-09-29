# Orionis Structures (`orionis.support.structures`)

> Recursive, reference-preserving deep-freeze/deep-thaw utility for nested `dict`/`list`/`tuple`/`MappingProxyType` structures.
>
> 🇪🇸 Versión en español: [README.es.md](README.es.md)

`orionis.support.structures` is a tiny, dependency-free utility module
built around a single class, `FreezeThaw`, that converts nested mutable
containers into fully immutable ones (and back). It is used internally
by the framework (for example `orionis.foundation.application.Application`)
to snapshot configuration trees as immutable data and to obtain safe,
independently-mutable working copies of them, but it has no dependency
on the rest of the framework and can be used standalone in any project.

---

## Table of contents

1. [Requirements](#requirements)
2. [Module overview](#module-overview)
3. [API reference](#api-reference)
   - [`FreezeThaw`](#freezethaw-orionissupportstructuresfreezerfreezethaw)
4. [Usage examples](#usage-examples)
5. [Performance and concurrency considerations](#performance-and-concurrency-considerations)
6. [Design notes](#design-notes)
7. [Compatibility notes](#compatibility-notes)

---

## Requirements

No extra installation is required beyond the framework itself:

```bash
pip install orionis
```

- **Python:** 3.14 or newer (the same minimum as the rest of the framework).
- **Dependencies:** none beyond the Python standard library
  (`types.MappingProxyType`, `typing.Any`).

## Module overview

| Type | File | Purpose |
|---|---|---|
| `FreezeThaw` | [freezer.py](../freezer.py) | Stateless utility class (all `@staticmethod`) that recursively converts `dict`/`list`/`tuple` structures into immutable equivalents (`freeze`) and `MappingProxyType`/`dict`/`list`/`tuple` structures back into mutable `dict`/`list` structures (`thaw`). |

`FreezeThaw` treats four types as "containers": `dict`, `list`, `tuple`,
and `MappingProxyType`. Everything else (numbers, strings, `None`,
custom objects, etc.) is treated as a scalar and returned unchanged,
by identity, without being copied or wrapped.

Mapping between mutable and immutable equivalents used by the module:

| Mutable | Immutable |
|---|---|
| `dict` | `MappingProxyType` |
| `list` | `tuple` |
| `tuple` | `tuple` (rebuilt so any mutable content nested inside it is also frozen) |

---

## API reference

### `FreezeThaw` (`orionis.support.structures.freezer.FreezeThaw`)

All members are `@staticmethod`; the class is never instantiated and
holds no state of its own.

| Method | Signature | Description |
|---|---|---|
| `_isContainer` | `_isContainer(obj: object) -> bool` | `True` if `obj` is a `dict`, `list`, `tuple`, or `MappingProxyType`; `False` otherwise. Internal classification helper (name-prefixed as private, but plain and side-effect-free, so it is also exercised directly by the test suite). |
| `freeze` | `freeze(obj: object) -> object` | Recursively converts a `dict`/`list`/`tuple` structure into an immutable equivalent (`MappingProxyType`/`tuple`, nested containers included). `MappingProxyType` instances and any non-container object are returned unchanged. Returns `object` because the result type depends on the input (`MappingProxyType`, `tuple`, or the original scalar). |
| `thaw` | `thaw(obj: object) -> object` | Recursively converts a `MappingProxyType`/`dict`/`list`/`tuple` structure into a fully mutable equivalent (`dict`/`list`, nested containers included). Any non-container object is returned unchanged. Returns `object` because the result type depends on the input (`dict`, `list`, or the original scalar). |

Both `freeze()` and `thaw()`:

- Return the original object **unchanged** (same identity) for
  non-container inputs, including `None`.
- Return a **new** empty immutable/mutable container for empty inputs
  (`{}`/`MappingProxyType({})` for dict-likes, `()`/`[]` otherwise) —
  there is a fast path that skips the traversal machinery entirely for
  empty containers.
- Preserve **shared references**: if the same nested object appears more
  than once inside the input (by `id()`), every occurrence is mapped to
  the *same* new frozen/thawed object rather than being duplicated —
  this also makes self-referential structures (a container that contains
  itself) safe to process instead of causing infinite recursion.
- Neither method raises exceptions for supported input types; there are
  no documented `Raises` sections because none of the container/scalar
  code paths raise on their own (mutating the *result* of `freeze()`,
  e.g. `frozen["a"] = 1`, raises the standard `TypeError` from
  `MappingProxyType`/`tuple`, but that is standard library behavior, not
  something `FreezeThaw` raises itself).

---

## Usage examples

### Freezing a configuration tree

```python
from types import MappingProxyType
from orionis.support.structures.freezer import FreezeThaw

config = {
    "app": {"name": "Orionis", "debug": False},
    "allowed_hosts": ["localhost", "127.0.0.1"],
}

frozen = FreezeThaw.freeze(config)

print(isinstance(frozen, MappingProxyType))        # True
print(isinstance(frozen["app"], MappingProxyType)) # True
print(isinstance(frozen["allowed_hosts"], tuple))  # True

try:
    frozen["app"]["debug"] = True
except TypeError as exc:
    print(f"cannot mutate frozen config: {exc}")
```

### Thawing back into a mutable working copy

```python
from orionis.support.structures.freezer import FreezeThaw

# `frozen` from the previous example
working_copy = FreezeThaw.thaw(frozen)

working_copy["app"]["debug"] = True
working_copy["allowed_hosts"].append("example.com")

print(working_copy["app"]["debug"])        # True
print(working_copy["allowed_hosts"])       # ["localhost", "127.0.0.1", "example.com"]
```

### Shared references are preserved, not duplicated

```python
from orionis.support.structures.freezer import FreezeThaw

shared = {"role": "admin"}
data = {"user_a": shared, "user_b": shared}

frozen = FreezeThaw.freeze(data)
print(frozen["user_a"] is frozen["user_b"])  # True: same MappingProxyType instance
```

### Scalars and already-immutable input pass through untouched

```python
from types import MappingProxyType
from orionis.support.structures.freezer import FreezeThaw

print(FreezeThaw.freeze(42) == 42)              # True (identity, no wrapping)
print(FreezeThaw.freeze(None) is None)          # True

already_frozen = MappingProxyType({"a": 1})
print(FreezeThaw.freeze(already_frozen) is already_frozen)  # True
```

---

## Performance and concurrency considerations

- Both `freeze()` and `thaw()` use an **iterative, stack-based traversal**
  (an explicit `list` used as a LIFO stack) instead of recursive
  function calls, so processing a deeply nested structure (e.g. a large,
  deeply nested configuration tree) does not risk hitting Python's
  recursion limit the way a naive recursive implementation would.
- Both methods use an `id()`-keyed cache (`dict[int, Any]`) to visit each
  distinct container object only once, giving `O(n)` time and memory
  relative to the total number of container nodes (plus scalars, which
  are visited but not cached). Shared/aliased sub-structures are only
  converted once and then reused by reference in every place they occur.
- `thaw()` additionally tracks a `fixups` list containing only the
  parent/key pairs whose value is itself a container, so the second
  "fix up references" pass costs `O(N_containers)` instead of rescanning
  every key/value pair again.
- `freeze()` fixes up references during a bottom-up pass over the cache
  in reverse insertion order (children before parents), which is
  guaranteed correct because the stack-based traversal always inserts a
  parent into the cache before any of its children.
- Empty containers (`{}`, `[]`, `()`, `MappingProxyType({})`) and
  non-container scalars take an `O(1)` fast path with no traversal at
  all.
- `FreezeThaw` has **no locks, no shared mutable module state, and no
  I/O** — the two module-level constants (`_CONTAINER_TYPES`,
  `_MUTABLE_TYPES`) are read-only tuples of types. Both `freeze()` and
  `thaw()` are plain, synchronous, CPU-bound functions and are safe to
  call concurrently from multiple threads or `asyncio` tasks as long as
  the **input** structure is not being mutated concurrently by another
  thread while it is being frozen/thawed.

## Design notes

- **Stateless utility class**: `FreezeThaw` only exposes `@staticmethod`s
  and is never meant to be instantiated; it exists purely to group two
  related, symmetrical operations (`freeze`/`thaw`) under one namespace.
- **Iterative DFS with an explicit stack**: chosen over recursion
  specifically to support arbitrarily deep structures (e.g. large nested
  configuration dictionaries) without hitting `RecursionError`.
- **Identity-based memoization (`id()` cache)**: both operations key
  their cache by `id(obj)` rather than value equality, which is what
  allows shared references to be preserved (not duplicated) and what
  makes self-referential containers safe to process instead of looping
  forever.
- **Type-symmetry, not perfect symmetry**: `freeze()` turns `dict` into
  `MappingProxyType` and `list`/`tuple` into `tuple`; `thaw()` turns
  `MappingProxyType`/`dict` into `dict` and `list`/`tuple` into `list`.
  A `tuple` frozen and then thawed becomes a `list`, not a `tuple` — the
  round trip preserves *values*, not the exact original container type
  for tuples.
- **Already-immutable input short-circuits**: `MappingProxyType` is
  deliberately excluded from `_MUTABLE_TYPES`, so `freeze()` returns it
  unchanged (by identity) instead of re-wrapping it — this is also why a
  `MappingProxyType` value nested inside a mutable `dict` is left as-is
  by `freeze()` rather than being walked further.

## Compatibility notes

- Requires **Python 3.14+**, consistent with the rest of the `orionis`
  framework (`requires-python = ">=3.14"` in `pyproject.toml`).
- No third-party dependencies; only uses `types.MappingProxyType` and
  `typing.Any` from the standard library.
- No platform-specific behavior; pure Python with no OS-level
  dependencies.
- Used internally by `orionis.foundation.application.Application` to
  freeze/thaw core configuration trees at boot time, but the module
  itself does not import or depend on any other part of the framework.
