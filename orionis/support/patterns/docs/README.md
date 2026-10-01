# Orionis Patterns (`orionis.support.patterns`)

> Two lightweight, dependency-free metaclasses — `Final` (blocks subclassing) and `Singleton` (thread-safe and async-safe singleton) — used throughout the framework to enforce structural guarantees at class-definition time.
>
> 🇪🇸 Versión en español: [README.es.md](README.es.md)

`orionis.support.patterns` has no runtime services, providers, or
facades. It provides two independent metaclasses that other framework
classes opt into via `metaclass=Final` or `metaclass=Singleton` to get a
guarantee enforced by the type system itself: "this class cannot be
subclassed" or "this class only ever has one instance". Both metaclasses
are pure Python, stateless from the caller's perspective, and safe to
use in any project, not just within Orionis.

---

## Table of contents

1. [Requirements](#requirements)
2. [Module overview](#module-overview)
3. [API reference](#api-reference)
   - [`Final`](#final-orionissupportpatternsfinalmetafinal)
   - [`Singleton`](#singleton-orionissupportpatternssingletonmetasingleton)
4. [Usage examples](#usage-examples)
5. [Performance and concurrency considerations](#performance-and-concurrency-considerations)
6. [Design notes](#design-notes)
7. [Compatibility notes](#compatibility-notes)

---

## Requirements

No extra installation is required beyond the framework itself:

```bash
uv add orionis
```

- **Python:** 3.14 or newer (the same minimum as the rest of the framework).
- **Dependencies:** none beyond the Python standard library (`threading`,
  `asyncio`).

## Module overview

| Type | File | Kind | Purpose |
|---|---|---|---|
| `Final` | [final/meta.py](../final/meta.py) | Metaclass (`type` subclass) | Marks a class as non-inheritable; any attempt to subclass it raises `TypeError` at class-definition time. |
| `Singleton` | [singleton/meta.py](../singleton/meta.py) | Metaclass (`type` subclass) | Ensures a class has exactly one instance, with a thread-safe synchronous path (`__call__`) and an async-safe path (`__acall__`). |

Both are used by applying them as the `metaclass=` of a class, e.g.
`class Cookies(metaclass=Final): ...` (used by
`orionis.http.payload.estructures.cookies.Cookies`,
`headers.Headers`, and `query_params.QueryParams`) or
`class DotEnv(metaclass=Singleton): ...` (used by
`orionis.environment.core.dot_env.DotEnv`).

---

## API reference

### `Final` (`orionis.support.patterns.final.meta.Final`)

```python
class Final(type):
    def __new__(metacls, name, bases, namespace) -> type: ...
```

`Final` is a metaclass: you use it via `metaclass=Final` on a class
definition, you do not call it directly. Its `__new__` runs once, at
class-definition time:

| Behavior | Description |
|---|---|
| Marking | Every class created with `metaclass=Final` gets `__is_final__ = True` set directly on the new class object (via `type.__setattr__`, bypassing any custom `__setattr__`). |
| Enforcement | Before creating a new class, `Final.__new__` checks every base class's **own** `__dict__` (not inherited attributes) for `__is_final__ = True`. If any base is final, class creation raises `TypeError`. |
| Error message | `f"Cannot inherit from orionis final class '{base.__name__}'"`. |

There is no other public method — `Final` only participates in class
creation through `__new__`.

### `Singleton` (`orionis.support.patterns.singleton.meta.Singleton`)

```python
class Singleton(type):
    def __init__(cls, name, bases, namespace) -> None: ...
    def __call__(cls, *args, **kwargs) -> object: ...
    async def __acall__(cls, *args, **kwargs) -> object: ...
```

`Singleton` is a metaclass: apply it via `metaclass=Singleton`. Every
class using it gets its own singleton state — there is no shared
instance across unrelated `Singleton` classes.

| Member | Description |
|---|---|
| `__init__` | Runs once at class-definition time. Initializes `cls._singleton_instance` to an internal "not yet created" sentinel and stores a dedicated `threading.Lock` on the class. |
| `__call__` | `MyClass(*args, **kwargs)` — thread-safe synchronous constructor. Returns the existing instance if one was already created (fast path: one attribute read + identity check); otherwise acquires the class's dedicated lock and creates the instance under double-checked locking. |
| `__acall__` | `await MyClass.__acall__(*args, **kwargs)` — async-safe constructor, **invoked explicitly** (Python does not call `__acall__` automatically from `MyClass(...)`). Uses the class's `threading.Lock` to coordinate creation with synchronous calls. |

Both `__call__` and `__acall__` read/write the same underlying
`cls._singleton_instance` slot, so whichever path creates the instance
first "wins" and the other path will see it on its next check.

---

## Usage examples

### `Final`: preventing inheritance

```python
from orionis.support.patterns.final.meta import Final

class ImmutableHeaders(metaclass=Final):
    def __init__(self, data: dict[str, str]) -> None:
        self._data = dict(data)

    def get(self, key: str) -> str | None:
        return self._data.get(key)

headers = ImmutableHeaders({"content-type": "application/json"})
print(headers.get("content-type"))  # "application/json"

try:
    class CustomHeaders(ImmutableHeaders):
        pass
except TypeError as exc:
    print(exc)  # "Cannot inherit from orionis final class 'ImmutableHeaders'"
```

### `Singleton`: synchronous usage

```python
from orionis.support.patterns.singleton.meta import Singleton

class AppSettings(metaclass=Singleton):
    def __init__(self) -> None:
        self.debug = False

a = AppSettings()
b = AppSettings()
print(a is b)  # True: both variables reference the same instance

a.debug = True
print(b.debug)  # True: `a` and `b` are the same object
```

### `Singleton`: asynchronous usage

```python
import asyncio
from orionis.support.patterns.singleton.meta import Singleton

class ConnectionPool(metaclass=Singleton):
    def __init__(self) -> None:
        self.connections: list[str] = []

async def main() -> None:
    pool_a = await ConnectionPool.__acall__()
    pool_b = await ConnectionPool.__acall__()
    print(pool_a is pool_b)  # True

asyncio.run(main())
```

---

## Performance and concurrency considerations

- **`Final`**: the inheritance check only runs once, at class-definition
  time (`__new__`), and only iterates over the direct `bases` tuple of
  the class being created — it has zero runtime cost for regular
  attribute access or method calls on instances afterward. It uses
  `base.__dict__.get("__is_final__", False)` instead of `getattr`,
  which avoids a full MRO traversal since `__is_final__` is always set
  directly on the class object that owns it, never inherited.
- **`Singleton` paths (`__call__` and `__acall__`)**: after the first
  instance is created, calls use one attribute read and an identity
  check, without acquiring a lock. First-time construction rechecks the
  cached value while holding a lock stored on the class. Both APIs use
  that same lock, so concurrent sync and async callers cannot construct
  duplicate instances. Keeping lock state on each class also allows
  dynamically created singleton classes to be reclaimed when unused.
- Neither metaclass performs any I/O; both are pure, in-memory,
  CPU-bound operations.

## Design notes

- **Metaclasses as opt-in structural guarantees**: both `Final` and
  `Singleton` are applied via `metaclass=...` rather than inheritance
  from a base class, keeping the enforced behavior (non-inheritable /
  single-instance) orthogonal to the class's own inheritance hierarchy.
- **`__is_final__` stored per-class, not inherited**: `Final` reads
  `base.__dict__` directly (not `getattr`) specifically so the flag is
  never accidentally "seen" through inheritance — it is always set
  fresh on every class created with the metaclass.
- **Double-checked locking**: `Singleton.__call__`/`__acall__` first read
  the cached instance, then recheck it under the shared class lock before
  construction.
- **Explicit `__acall__` invocation**: Python's data model does not
  invoke `__acall__` automatically when you write `MyClass(...)` in an
  `async def` context; it must be awaited explicitly as
  `await MyClass.__acall__()`. This is a deliberate, explicit API rather
  than implicit "magic" dispatch based on the calling context.
- **`type.__setattr__` used explicitly**: both metaclasses write class
  attributes (`__is_final__`, `_singleton_instance`) via
  `type.__setattr__(cls, ...)` rather than plain attribute assignment,
  which bypasses any custom `__setattr__` a subclass of the metaclass
  (or of the target class) might define.

## Compatibility notes

- Requires **Python 3.14+**, consistent with the rest of the `orionis`
  framework (`requires-python = ">=3.14"` in `pyproject.toml`).
- No third-party dependencies; only uses `threading` from the standard
  library.
- No platform-specific behavior; both metaclasses rely only on the
  standard CPython type-creation protocol and `threading.Lock`.
- Used internally by `orionis.http.payload.estructures` (`Cookies`,
  `Headers`, `QueryParams`, via `Final`) and
  `orionis.environment.core.dot_env.DotEnv` (via `Singleton`), but
  neither metaclass depends on any other part of the framework.
