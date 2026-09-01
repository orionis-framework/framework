# orionis.container

> Async-first service container: bindings, lifetimes, scopes, autowiring, service providers and facades.

## Table of contents

- [Functional description](#functional-description)
  - [Where it fits](#where-it-fits)
  - [Resolution pipeline](#resolution-pipeline)
  - [Argument resolution order](#argument-resolution-order)
  - [File map](#file-map)
  - [Design decisions](#design-decisions)
- [API reference](#api-reference)
  - [`Container`](#container)
    - [`Container.instance()`](#containerinstance)
    - [`Container.transient()`](#containertransient)
    - [`Container.singleton()`](#containersingleton)
    - [`Container.scoped()`](#containerscoped)
    - [`Container.bound()`](#containerbound)
    - [`Container.beginScope()`](#containerbeginscope)
    - [`Container.getCurrentScope()`](#containergetcurrentscope)
    - [`Container.make()`](#containermake)
    - [`Container.build()`](#containerbuild)
    - [`Container.invoke()`](#containerinvoke)
    - [`Container.call()`](#containercall)
  - [`IContainer`](#icontainer)
  - [`Lifetime`](#lifetime)
  - [`Binding`](#binding)
  - [`ScopeManager`](#scopemanager)
  - [`ScopedContext`](#scopedcontext)
  - [`CircularDependencyException`](#circulardependencyexception)
  - [`ServiceProvider`](#serviceprovider)
  - [`DeferrableProvider`](#deferrableprovider)
  - [`IServiceProvider`](#iserviceprovider)
  - [`IDeferrableProvider`](#ideferrableprovider)
  - [`Facade`](#facade)
  - [`FacadeMeta`](#facademeta)
  - [`IFacade`](#ifacade)
  - [Package exports](#package-exports)
- [Usage examples](#usage-examples)
  - [Registering and resolving services](#registering-and-resolving-services)
  - [Working with scopes](#working-with-scopes)
  - [Handling resolution errors](#handling-resolution-errors)
  - [Building a service provider](#building-a-service-provider)
  - [Proxying a service through a facade](#proxying-a-service-through-a-facade)
  - [Inspecting bindings and scopes](#inspecting-bindings-and-scopes)
  - [Resolving concurrently](#resolving-concurrently)
- [Performance and concurrency considerations](#performance-and-concurrency-considerations)
- [Compatibility notes](#compatibility-notes)

---

## Functional description

`orionis.container` is the dependency-injection engine of the framework. It maps
contracts (abstract classes or string aliases) to concrete implementations, decides
how long each resolved object lives, and constructs objects by reading their
constructor signatures through reflection so callers never wire dependencies by hand.

### Where it fits

- `orionis.foundation.application.Application` extends `Container` and adds the
  bootstrap layer. The verified MRO is
  `Application -> Container -> IApplication -> IContainer -> ABC -> object`, so the
  real container of a running application *is* the `Application` singleton.
- `orionis.introspection` supplies `ReflectionConcrete` and `ReflectionCallable`,
  which produce the `Signature`/`Argument` metadata used to inject constructor and
  callable parameters.
- `orionis.schemas.validator.Schema` and `orionis.http.request.Request` are imported
  at module level by `container.py`: a parameter annotated with a `msgspec.Struct`
  subclass is resolved by validating the current request body.
- `orionis.support.entities.base.BaseEntity` is the base of the `Binding` dataclass.
- `orionis.foundation.contracts.application.IApplication` is imported at runtime by
  `ServiceProvider` to type its constructor argument.

### Resolution pipeline

`make(key)` executes the following steps, in this order:

1. If `key` is not a string and the singleton cache already holds it, the cached
   object is returned immediately.
2. `key` is normalised to an abstract type. A string is looked up in the alias table;
   if it is missing, the deferred provider registry is consulted, the matching
   provider is imported, built, `register()`-ed and `boot()`-ed, and the alias table is
   read again. A still-unknown alias raises `ValueError`.
3. The singleton cache is checked again with the resolved abstract type.
4. If a scope is active and already holds the abstract type, the scoped instance is
   returned.
5. The binding table is consulted. If there is no binding, the deferred registry is
   consulted once more. If there is still no binding and the key is a class, the
   container falls back to `build()`; otherwise it raises `ValueError`.
6. The binding is resolved according to its `Lifetime`: `SINGLETON` caches the
   instance on the contract, `TRANSIENT` always builds a new one, and `SCOPED`
   stores it in the active scope (raising `RuntimeError` when no scope is open).

`build()` never consults the singleton cache: it always constructs a new object.

### Argument resolution order

`Container` inspects the target signature once and then resolves every parameter in
declaration order. Parameters named `self`, `cls`, `args` and `kwargs`, plus `*args`
and `**kwargs`, are skipped by the reflection layer.

For positional-or-keyword parameters:

1. The parameter is annotated with a `msgspec.Struct` subclass → the value is produced
   by validating the request body.
2. The annotated type is bound in the container **and** the parameter name was not
   supplied as a keyword → resolved with `make()`.
3. A caller-supplied positional argument is still available → consumed.
4. A caller-supplied keyword argument matches the name → consumed.
5. Otherwise the argument is resolved on its own: a declared default value wins,
   otherwise `make()` is used. Unresolved parameters whose type lives in `builtins`
   or `typing` raise `TypeError`.

For keyword-only parameters:

1. Schema parameters, as above.
2. A caller-supplied keyword argument matches the name → consumed.
3. The annotated type is bound in the container → resolved with `make()`.
4. Otherwise the argument is resolved on its own, as in step 5 above.

Positional arguments the signature did not consume are appended, and unused keyword
arguments are merged into the final call.

### File map

| Path | Contents |
|---|---|
| `container.py` | `Container`, the concrete engine. |
| `contracts/container.py` | `IContainer` — 11 abstract methods. |
| `contracts/service_provider.py` | `IServiceProvider` — `register()` / `boot()`. |
| `contracts/deferrable_provider.py` | `IDeferrableProvider` — `provides()`. |
| `contracts/facade.py` | `IFacade` — `getFacadeAccessor()` / `resolve()` / `pin()` / `unpin()`. |
| `context/scope.py` | `ScopedContext` plus the module-level `get_current_scope` / `set_current_scope` / `reset_scope` shortcuts. |
| `context/manager.py` | `ScopeManager`, the async context manager backing scoped lifetimes. |
| `entities/binding.py` | `Binding`, the frozen record describing one registration. |
| `enums/lifetimes.py` | `Lifetime` — `TRANSIENT`, `SINGLETON`, `SCOPED`. |
| `exceptions/container.py` | `CircularDependencyException`. |
| `facades/facade.py` | `Facade`, the static-proxy base class. |
| `facades/meta.py` | `FacadeMeta` and the private `_FacadeDispatch`. |
| `providers/service_provider.py` | `ServiceProvider` base class. |
| `providers/deferrable_provider.py` | `DeferrableProvider` marker base class. |

### Design decisions

- **Singleton per class.** `Container.__new__` stores one instance per class in the
  `_instances` class dictionary using double-checked locking over a
  `threading.RLock`. Subclasses that do not redeclare `_instances` share that single
  dictionary, keyed by class object, so each subclass still gets its own instance.
- **Idempotent `__init__`.** Initialisation is guarded by the presence of
  `_Container__initialized` in `self.__dict__`, so constructing the singleton again
  never wipes existing registrations.
- **Async resolution API.** `make`, `build`, `invoke` and `call` are coroutines
  because provider `boot()` hooks and schema validation may await.
- **`contextvars` for scopes and cycle detection.** Both the active scope and the
  in-flight resolution stack live in `ContextVar`s, so concurrent asyncio tasks never
  observe each other's state.
- **One-shot work is serialised per key.** Building a singleton, filling a scope entry
  and bootstrapping a deferred provider all span several `await` points, so each of
  them runs under an `asyncio.Lock` keyed by contract (or by provider key). Concurrent
  tasks share the single construction instead of duplicating it.
- **Frozen `Binding`.** Registrations are described by an immutable, hashable
  dataclass, which makes them safe to share between the binding table and callers.
- **Lazy facade dispatch.** `FacadeMeta.__getattr__` returns a cached plain function;
  the container is only touched when the resulting `_FacadeDispatch` object is awaited
  or entered, which keeps transient bindings honest.
- **No `__slots__`.** `Container`, `ScopeManager` and `Binding` all keep a `__dict__`;
  only `_FacadeDispatch` declares `__slots__`.

---

## API reference

### `Container`

```python
class Container(IContainer):
    _instances: ClassVar[dict] = {}
    _lock: ClassVar[threading.RLock] = threading.RLock()

    def __new__(cls, *args, **kwargs) -> Self: ...
    def __init__(self) -> None: ...
```

Concrete implementation of `IContainer`, located in
`orionis.container.container`. Its class docstring states the concurrency contract
reproduced in [Performance and concurrency
considerations](#performance-and-concurrency-considerations).

**Class attributes**

| Name | Type | Meaning |
|---|---|---|
| `_instances` | `ClassVar[dict]` | Singleton registry keyed by class object. Shared by every subclass that does not redeclare it. |
| `_lock` | `ClassVar[threading.RLock]` | Guards singleton creation inside `__new__`. |

**Instance state created by `__init__`**

| Name | Type | Meaning |
|---|---|---|
| `_deferred_providers` | `dict[str, dict[str, str]]` | Maps a requested key to `{"module": ..., "class": ...}`. Populated by `Application.create()`, not by this module. |
| `__singleton_cache` | `dict[str, Any]` | Resolved singleton instances, keyed by contract. |
| `__aliases` | `dict[str, type]` | Alias string → abstract type. |
| `__bindings` | `dict[Any, Binding]` | Abstract type → `Binding`. |
| `__cache_resolve_deferred_providers` | `set[Any]` | Keys whose deferred provider already ran. |
| `__creation_locks` | `dict[Any, tuple[AbstractEventLoop, asyncio.Lock]]` | Per-key creation lock together with the loop that owns it. |

**Side effects.** Constructing any `Container` subclass mutates the shared
`_instances` dictionary. Registration methods mutate the instance dictionaries listed
above. Resolution may import modules (deferred providers) and read the current HTTP
request (schema arguments).

#### `Container.instance()`

```python
def instance(
    self,
    abstract: type[Any] | None,
    instance: object,
    *,
    alias: str | None = None,
    override: bool = False,
) -> bool: ...
```

Registers an already-built object.

- `abstract` — contract to associate with the object, or `None` to use
  `type(instance)`.
- `instance` — the initialised object. Passing a class raises `TypeError`.
- `alias` — optional alias. It is stripped and must be a non-empty string.
- `override` — allow replacing an existing registration.
- **Returns** `True` when the registration succeeded.

Behaviour depends on whether a scope is active:

- **Inside a scope**, the object is stored in that scope. Supplying an `alias` raises
  `ValueError("Alias registration is only allowed globally.")`.
- **Outside a scope**, a `Binding` with `Lifetime.SINGLETON` is stored and the object
  is placed in the singleton cache; the alias, if any, is added to the alias table.

**Raises**

- `TypeError` — `instance` is a class; `abstract` is not a class; `instance` is not an
  instance of `abstract`; `alias` is not a string.
- `ValueError` — `alias` is empty after stripping; the contract or alias is already
  registered and `override` is `False`; an alias was supplied inside a scope.

#### `Container.transient()`

```python
def transient(
    self,
    abstract: type[Any] | None,
    concrete: type[Any],
    *,
    alias: str | None = None,
    override: bool = False,
) -> bool: ...
```

Registers `concrete` with `Lifetime.TRANSIENT`; every resolution builds a new object.
When `abstract` is `None`, `concrete` is bound to itself.

**Raises**

- `TypeError` — `abstract` or `concrete` is not a class; `concrete` is not a subclass
  of `abstract`; `alias` is not a string.
- `ValueError` — empty alias, or duplicate contract/alias without `override`.

#### `Container.singleton()`

```python
def singleton(
    self,
    abstract: type[Any] | None,
    concrete: type[Any],
    *,
    alias: str | None = None,
    override: bool = False,
) -> bool: ...
```

Same validation as `transient()`, with `Lifetime.SINGLETON`. The instance is created on
first `make()` and cached against the contract from then on.

#### `Container.scoped()`

```python
def scoped(
    self,
    abstract: type[Any] | None,
    concrete: type[Any],
    *,
    alias: str | None = None,
    override: bool = False,
) -> bool: ...
```

Same validation as `transient()`, with `Lifetime.SCOPED`. Resolving the binding without
an active scope raises `RuntimeError`.

#### `Container.bound()`

```python
def bound(
    self,
    key: type[Any] | str,
) -> bool: ...
```

Reports whether `key` can be resolved. A string is translated through the alias table
first and returns `False` when unknown. The lookup checks the active scope, then the
binding table, then the singleton cache. `bound()` never triggers deferred providers.

#### `Container.beginScope()`

```python
def beginScope(self) -> ScopeManager: ...
```

Returns a brand-new `ScopeManager`. The scope only becomes active once the manager is
entered with `async with`.

#### `Container.getCurrentScope()`

```python
def getCurrentScope(self) -> dict[Any, Any] | None: ...
```

Returns the currently active scope object, or `None`. The value comes from the
`ContextVar` in `orionis.container.context.scope`, so it is per-task.

#### `Container.make()`

```python
async def make(
    self,
    key: type[Any] | str,
    *args: tuple[Any, ...],
    **kwargs: dict[str, Any],
) -> Any: ...
```

Resolves a service following the [resolution pipeline](#resolution-pipeline).
`*args` and `**kwargs` are forwarded to the constructor when the object has to be
built.

When several tasks of the same event loop resolve the same uncached `SINGLETON` or
`SCOPED` binding at once, only one construction runs and every caller receives that
instance.

**Raises**

- `ValueError` — an unknown string key, or a non-class key with no binding.
- `RuntimeError` — a `SCOPED` binding resolved with no active scope.
- `CircularDependencyException` — the dependency graph contains a cycle.
- `TypeError` — a constructor parameter cannot be resolved.

#### `Container.build()`

```python
async def build(
    self,
    type_: Callable[..., Any],
    *args: tuple[Any, ...],
    **kwargs: dict[str, Any],
) -> Any: ...
```

Instantiates `type_` with autowired dependencies, ignoring the singleton cache. When
`type_` is not already bound, the deferred provider registry is consulted first.

**Raises**

- `TypeError` — `type_` is not a class, or a constructor parameter cannot be resolved.
- `CircularDependencyException` — the dependency graph contains a cycle.

#### `Container.invoke()`

```python
async def invoke(
    self,
    fn: Callable[..., Any],
    *args: tuple[Any, ...],
    **kwargs: dict[str, Any],
) -> Any: ...
```

Calls `fn` with autowired arguments and returns its result. Coroutine functions are
awaited; synchronous callables are called directly.

**Raises**

- `TypeError` — `fn` is not callable or is a class.

#### `Container.call()`

```python
async def call(
    self,
    instance: object,
    method_name: str,
    *args: tuple,
    **kwargs: dict,
) -> Any: ...
```

Looks `method_name` up on `instance` and invokes it with autowired arguments.

**Raises**

- `AttributeError` — the attribute does not exist on the instance.
- `TypeError` — the attribute exists but is not callable.

### `IContainer`

Abstract base class in `orionis.container.contracts.container`. It declares exactly
these abstract methods:

`instance`, `transient`, `singleton`, `scoped`, `bound`, `beginScope`,
`getCurrentScope`, `make`, `build`, `invoke`, `call`.

`make`, `build`, `invoke` and `call` are declared `async def`. The module uses
`from __future__ import annotations`, so its annotations are strings at runtime while
the implementation's are real objects; only parameter names are directly comparable.

### `Lifetime`

```python
class Lifetime(Enum):
    TRANSIENT = auto()
    SINGLETON = auto()
    SCOPED = auto()
```

`enum.Enum` with three members. Verified values: `TRANSIENT = 1`, `SINGLETON = 2`,
`SCOPED = 3`.

### `Binding`

```python
@dataclass(frozen=True, kw_only=True)
class Binding(BaseEntity):
    contract: type | None = None
    concrete: type | None = None
    instance: object | None = None
    lifetime: Lifetime = Lifetime.TRANSIENT
    alias: str | None = None
```

Immutable, hashable, keyword-only record describing one registration. It inherits
`toDict()` and `getFields()` from `BaseEntity`; `toDict()` converts the `lifetime`
member to its integer value.

`__post_init__` raises `TypeError` when `lifetime` is not a `Lifetime` member.

`Container` populates `contract`, `concrete`, `lifetime` and `alias`. It stores
already-built objects in its internal singleton cache rather than in the `instance`
field, so bindings created by the container leave `instance` set to `None`.

### `ScopeManager`

```python
class ScopeManager:
    def __init__(self) -> None: ...
    def __getitem__(self, key: object) -> object | None: ...
    def __setitem__(self, key: object, value: object) -> None: ...
    def __contains__(self, key: object) -> bool: ...
    def clear(self) -> None: ...
    async def __aenter__(self) -> Self: ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None: ...
    async def get(self, key: object) -> Any | None: ...
    def set(self, key: object, value: Any) -> None: ...
    async def resolve(self, key: object) -> Any: ...
```

Dictionary-like container for scoped instances, in
`orionis.container.context.manager`.

- `__getitem__` returns `None` for missing keys instead of raising.
- `__aenter__` publishes the manager as the active scope and stores the reset token on
  `self._token`; that attribute only exists after entering, so calling `__aexit__`
  first raises `AttributeError`.
- `__aexit__` clears every stored instance and resets the scope `ContextVar`. It always
  cleans up, including when the block raised.
- `get()` awaits stored coroutines and `asyncio.Task`s, replacing the stored value with
  the resolved result so later calls are cheap. It returns `None` both for a missing
  key and for a key explicitly storing `None`.
- `resolve()` delegates to `get()` and raises `KeyError` when the result is `None`,
  which includes the case of a value that really is `None`.

### `ScopedContext`

```python
class ScopedContext:
    _active_scope: contextvars.ContextVar[object | None] = contextvars.ContextVar(
        "x-orionis-container-context-scope",
        default=None,
    )

    @classmethod
    def getCurrentScope(cls) -> object | None: ...
    @classmethod
    def setCurrentScope(cls, scope: object) -> contextvars.Token: ...
    @classmethod
    def reset(cls, token: contextvars.Token) -> None: ...
```

Thin wrapper over a single `ContextVar` named
`"x-orionis-container-context-scope"`, defaulting to `None`.

The module also exposes three shortcuts bound directly to the `ContextVar` methods:

```python
get_current_scope = ScopedContext._active_scope.get
set_current_scope = ScopedContext._active_scope.set
reset_scope       = ScopedContext._active_scope.reset
```

`Container` uses `get_current_scope` internally.

### `CircularDependencyException`

```python
class CircularDependencyException(Exception): ...
```

Raised by `Container` while autowiring when a type is already present in the
per-task resolution stack. The message names the offending type, for example
`Circular dependency detected while resolving argument '__main__.NodeB'.`

### `ServiceProvider`

```python
class ServiceProvider(IServiceProvider):
    def __init__(self, app: IApplication) -> None: ...
    def register(self) -> None: ...
    async def boot(self) -> None: ...
```

Base class for providers. The constructor stores the container as `self.app`. Both
lifecycle hooks are empty in the base class, so subclasses override only what they
need: `register()` is synchronous and is meant for bindings; `boot()` is a coroutine
and runs after registration.

### `DeferrableProvider`

```python
class DeferrableProvider(IDeferrableProvider):
    @classmethod
    def provides(cls) -> list[type | str]: ...
```

Marker base class for providers that should be registered on demand. The base
`provides()` raises `NotImplementedError("Subclasses must implement the provides
method.")`.

`provides()` only declares which types or aliases the provider owns. The registry that
`Container.__resolveDeferredProvider` reads — `_deferred_providers`, mapping a key to
`{"module": ..., "class": ...}` — is populated by
`orionis.foundation.application.Application.create()`, not by this class.

### `IServiceProvider`

Abstract base class declaring exactly `register` (synchronous) and `boot`
(a coroutine).

### `IDeferrableProvider`

Abstract base class declaring exactly the `provides` classmethod.

### `Facade`

```python
class Facade(metaclass=FacadeMeta):
    _application: IApplication | None = None
    _pinned_instance: Any = None

    @classmethod
    def getFacadeAccessor(cls) -> str: ...
    @classmethod
    async def resolve(cls, *args: object, **kwargs: object) -> object: ...
    @classmethod
    async def pin(cls) -> None: ...
    @classmethod
    def unpin(cls) -> None: ...
```

Static-proxy base class.

- `getFacadeAccessor()` must be overridden; the base implementation raises
  `NotImplementedError` with the message `Class <Name> must define
  getFacadeAccessor()`.
- `resolve()` creates `orionis.foundation.application.Application()` lazily when
  `_application` is `None`, raises `RuntimeError("Application not booted. Boot your app
  first.")` when the application reports `isBooted` as false, and otherwise returns
  `await application.make(cls.getFacadeAccessor(), *args, **kwargs)`.
- `pin()` stores the resolved instance on `_pinned_instance`.
- `unpin()` sets `_pinned_instance` back to `None`.

`_application` and `_pinned_instance` are **class attributes**, so they are shared by
every caller of that facade class inside the process.

### `FacadeMeta`

```python
class FacadeMeta(type):
    def __getattr__(cls, name: str) -> object: ...
```

Metaclass driving attribute access on facade classes. Python only calls `__getattr__`
when normal lookup fails, so real methods and class attributes declared on a facade
subclass bypass it entirely.

- When `cls._pinned_instance` is not `None`, the attribute is taken straight from the
  pinned object; a missing name raises `AttributeError` as usual.
- Otherwise a plain synchronous `dispatcher` function is returned. Dispatchers are
  memoised in the module-level `_dispatcher_cache` dictionary keyed by
  `(cls, name)`, so repeated access returns the identical object.

Calling a dispatcher builds a `_FacadeDispatch`:

```python
class _FacadeDispatch:
    __slots__ = ("_args", "_cls", "_context", "_kwargs", "_name")

    def __await__(self) -> Generator[object, None, object]: ...
    async def __aenter__(self) -> object: ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool: ...
```

`_FacadeDispatch` is private. Building it never touches the container; resolution
happens when the object is awaited or entered:

- Awaiting resolves the service, reads the attribute, calls it when it is callable, and
  awaits the result when it is awaitable. A non-callable attribute is returned as-is,
  which is why `await SomeFacade.attribute()` yields the plain value.
- `async with` resolves the service, calls the attribute, and delegates to the returned
  object's `__aenter__` / `__aexit__`. `__aexit__` requires a previous `__aenter__`.

### `IFacade`

Abstract base class declaring exactly `getFacadeAccessor`, `resolve`, `pin` and
`unpin`, all as classmethods; `resolve` and `pin` are coroutines.

### Package exports

`orionis/container/__init__.py` and `orionis/container/context/__init__.py` are empty;
import from the concrete modules. The remaining subpackages re-export one public name
each:

| Module | `__all__` |
|---|---|
| `orionis.container.contracts` | `IFacade` |
| `orionis.container.entities` | `Binding` |
| `orionis.container.enums` | `Lifetime` |
| `orionis.container.exceptions` | `CircularDependencyException` |
| `orionis.container.facades` | `Facade` |
| `orionis.container.providers` | `DeferrableProvider`, `ServiceProvider` |

---

## Usage examples

Every snippet below is a complete, runnable script. The printed output was captured by
executing them.

### Registering and resolving services

```python
import asyncio

from orionis.container.container import Container


class IClock:
    """Contract implemented by every clock service."""


class SystemClock(IClock):
    """Clock returning a fixed timestamp."""

    def now(self) -> str:
        return "2026-09-01T00:00:00Z"


class Reporter:
    """Service whose constructor declares an IClock dependency."""

    def __init__(self, clock: IClock) -> None:
        self.clock = clock


async def main() -> None:
    container = Container()

    container.singleton(IClock, SystemClock, alias="clock")
    container.transient(None, Reporter)

    clock = await container.make(IClock)
    print(type(clock).__name__, clock.now())

    # An alias resolves to exactly the same singleton instance.
    print("alias hits the singleton:", await container.make("clock") is clock)

    # Reporter is transient and its IClock argument is injected automatically.
    reporter = await container.make(Reporter)
    print("injected dependency:", type(reporter.clock).__name__)
    print("transient reuse:", await container.make(Reporter) is reporter)

    # build() always constructs a new object, even for singleton bindings.
    print("build returns a new object:", await container.build(SystemClock) is not clock)

    print("bound(IClock):", container.bound(IClock))
    print("bound('clock'):", container.bound("clock"))
    print("bound('missing'):", container.bound("missing"))


asyncio.run(main())
```

```text
SystemClock 2026-09-01T00:00:00Z
alias hits the singleton: True
injected dependency: SystemClock
transient reuse: False
build returns a new object: True
bound(IClock): True
bound('clock'): True
bound('missing'): False
```

### Working with scopes

```python
import asyncio

from orionis.container.container import Container


class RequestState:
    """Service that must live for exactly one scope."""


async def main() -> None:
    container = Container()
    container.scoped(None, RequestState)

    print("scope before:", container.getCurrentScope())

    async with container.beginScope() as scope:
        first = await container.make(RequestState)
        second = await container.make(RequestState)
        print("same instance inside the scope:", first is second)
        print("scope is active:", container.getCurrentScope() is scope)

        # Instances registered while a scope is active land in that scope.
        container.instance(None, "request-id-42")
        print("scoped instance:", await container.make(str))

    print("scope after:", container.getCurrentScope())

    async with container.beginScope():
        third = await container.make(RequestState)
        print("new scope, new instance:", third is first)


asyncio.run(main())
```

```text
scope before: None
same instance inside the scope: True
scope is active: True
scoped instance: request-id-42
scope after: None
new scope, new instance: False
```

### Handling resolution errors

```python
import asyncio

from orionis.container.container import Container
from orionis.container.exceptions.container import CircularDependencyException


class RequestState:
    """Scoped service used to trigger the missing-scope error."""


class NodeA:
    """First node of the dependency cycle."""


class NodeB:
    """Second node of the dependency cycle."""

    def __init__(self, a: NodeA) -> None:
        self.a = a


def _node_a_init(self, b: NodeB) -> None:
    self.b = b


# Closing the cycle after both classes exist keeps the annotations resolvable.
NodeA.__init__ = _node_a_init


class NeedsPort:
    """Service asking for a builtin type the container cannot invent."""

    def __init__(self, port: int) -> None:
        self.port = port


class IClockLike:
    """Contract that RequestState does not implement."""


async def main() -> None:
    container = Container()

    try:
        await container.make("missing-service")
    except ValueError as exc:
        print(f"ValueError: {exc}")

    container.scoped(None, RequestState)
    try:
        await container.make(RequestState)
    except RuntimeError as exc:
        print(f"RuntimeError: {exc}")

    try:
        await container.build(NodeB)
    except CircularDependencyException as exc:
        print(f"CircularDependencyException: {exc}")

    try:
        await container.build(NeedsPort)
    except TypeError as exc:
        print(f"TypeError: {exc}")

    try:
        container.transient(IClockLike, RequestState)
    except TypeError as exc:
        print(f"TypeError: {exc}")

    try:
        container.transient(None, RequestState, alias="   ")
    except ValueError as exc:
        print(f"ValueError: {exc}")


asyncio.run(main())
```

```text
ValueError: Service 'missing-service' is not registered.
RuntimeError: No active scope for scoped service. Use 'beginScope()' to create a scope.
CircularDependencyException: Circular dependency detected while resolving argument '__main__.NodeB'.
TypeError: Cannot auto-resolve built-in type 'int' for parameter 'port'. Provide a default value.
TypeError: RequestState must implement IClockLike
ValueError: Alias cannot be empty.
```

### Building a service provider

```python
import asyncio

from orionis.container.container import Container
from orionis.container.providers.deferrable_provider import DeferrableProvider
from orionis.container.providers.service_provider import ServiceProvider


class IMailer:
    """Contract for the mail transport."""


class SmtpMailer(IMailer):
    """Concrete mail transport."""

    def send(self, to: str) -> str:
        return f"sent to {to}"


class MailProvider(ServiceProvider):
    """Register and boot the mail transport."""

    def register(self) -> None:
        self.app.singleton(IMailer, SmtpMailer, alias="mailer")

    async def boot(self) -> None:
        mailer = await self.app.make(IMailer)
        print("booted with:", type(mailer).__name__)


class DeferredMailProvider(MailProvider, DeferrableProvider):
    """Same provider, but registered only when its services are requested."""

    @classmethod
    def provides(cls) -> list[type | str]:
        return [IMailer, "mailer"]


async def main() -> None:
    container = Container()

    provider = MailProvider(container)
    provider.register()
    await provider.boot()

    print("bound('mailer'):", container.bound("mailer"))
    mailer = await container.make("mailer")
    print(mailer.send("ops@example.com"))

    print("declared services:", DeferredMailProvider.provides())

    try:
        DeferrableProvider.provides()
    except NotImplementedError as exc:
        print(f"NotImplementedError: {exc}")


asyncio.run(main())
```

```text
booted with: SmtpMailer
bound('mailer'): True
sent to ops@example.com
declared services: [<class '__main__.IMailer'>, 'mailer']
NotImplementedError: Subclasses must implement the provides method.
```

### Proxying a service through a facade

```python
import asyncio

from orionis.container.container import Container
from orionis.container.facades.facade import Facade


class Cache:
    """Service reachable through the facade."""

    driver = "memory"

    def get(self, key: str) -> str:
        return f"value:{key}"


class CacheFacade(Facade):
    """Static proxy for the cache service."""

    @classmethod
    def getFacadeAccessor(cls) -> str:
        return "cache"


class BootedApplication(Container):
    """Container double reporting itself as booted."""

    isBooted = True


async def main() -> None:
    app = BootedApplication()
    app.singleton(None, Cache, alias="cache")

    # Facade.resolve() reads the shared application from the class attribute.
    CacheFacade._application = app

    # Without a pinned instance every attribute access returns a dispatcher
    # that only touches the container once it is awaited.
    dispatcher = CacheFacade.get
    print("dispatcher is cached:", dispatcher is CacheFacade.get)
    print("await a method:", await CacheFacade.get("users"))
    print("await an attribute:", await CacheFacade.driver())

    # After pin() the facade forwards attribute access directly.
    await CacheFacade.pin()
    print("pinned method call:", CacheFacade.get("users"))
    print("pinned attribute:", CacheFacade.driver)

    CacheFacade.unpin()
    print("pinned instance cleared:", CacheFacade._pinned_instance)

    try:
        Facade.getFacadeAccessor()
    except NotImplementedError as exc:
        print(f"NotImplementedError: {exc}")


asyncio.run(main())
```

```text
dispatcher is cached: True
await a method: value:users
await an attribute: memory
pinned method call: value:users
pinned attribute: memory
pinned instance cleared: None
NotImplementedError: Class Facade must define getFacadeAccessor()
```

### Inspecting bindings and scopes

```python
import asyncio

from orionis.container.context.manager import ScopeManager
from orionis.container.context.scope import ScopedContext
from orionis.container.entities.binding import Binding
from orionis.container.enums.lifetimes import Lifetime


class IClock:
    """Contract stored in the binding."""


class SystemClock(IClock):
    """Implementation stored in the binding."""


def describe_binding() -> None:
    binding = Binding(
        contract=IClock,
        concrete=SystemClock,
        lifetime=Lifetime.SINGLETON,
        alias="clock",
    )
    print("lifetime:", binding.lifetime)
    print("serialised:", binding.toDict())
    print("fields:", [field["name"] for field in binding.getFields()])

    try:
        Binding(lifetime="singleton")
    except TypeError as exc:
        print(f"TypeError: {exc}")


async def describe_scope_manager() -> None:
    manager = ScopeManager()
    manager.set("config", {"debug": True})
    print("subscript:", manager["config"])
    print("membership:", "config" in manager)
    print("await get:", await manager.get("config"))
    print("missing get:", await manager.get("absent"))

    try:
        await manager.resolve("absent")
    except KeyError as exc:
        print(f"KeyError: {exc}")

    manager.clear()
    print("after clear:", "config" in manager, manager["config"])


def describe_scoped_context() -> None:
    print("initial scope:", ScopedContext.getCurrentScope())
    token = ScopedContext.setCurrentScope("outer")
    print("after set:", ScopedContext.getCurrentScope())
    ScopedContext.reset(token)
    print("after reset:", ScopedContext.getCurrentScope())


describe_binding()
asyncio.run(describe_scope_manager())
describe_scoped_context()
```

```text
lifetime: Lifetime.SINGLETON
serialised: {'contract': <class '__main__.IClock'>, 'concrete': <class '__main__.SystemClock'>, 'instance': None, 'lifetime': 2, 'alias': 'clock'}
fields: ['contract', 'concrete', 'instance', 'lifetime', 'alias']
TypeError: The 'lifetime' attribute must be an instance of 'Lifetime', but received type 'str'.
subscript: {'debug': True}
membership: True
await get: {'debug': True}
missing get: None
KeyError: "Instance for key 'absent' not found in scope"
after clear: False None
initial scope: None
after set: outer
after reset: None
```

### Resolving concurrently

```python
import asyncio

from orionis.container.container import Container


class Config:
    """Singleton whose construction suspends before returning."""

    constructions = 0

    def __init__(self) -> None:
        Config.constructions += 1


class Report:
    """Service depending on a type published by a deferred provider."""

    def __init__(self, config: Config) -> None:
        self.config = config


class ConfigProvider:
    """Deferred provider that suspends while booting."""

    container: Container | None = None
    registrations = 0

    def register(self) -> None:
        ConfigProvider.registrations += 1
        ConfigProvider.container.singleton(None, Config)

    async def boot(self) -> None:
        await asyncio.sleep(0)


CONFIG_KEY = f"{Config.__module__}.{Config.__name__}"


async def main() -> None:
    container = Container()
    ConfigProvider.container = container

    # The bootstrap layer normally fills this registry; here it is explicit.
    container._deferred_providers = {
        CONFIG_KEY: {"module": __name__, "class": "ConfigProvider"},
    }

    reports = await asyncio.gather(*(container.build(Report)
                                     for _ in range(8)))

    print("reports built:", len(reports))
    print("provider registrations:", ConfigProvider.registrations)
    print("Config constructions:", Config.constructions)
    print("shared singleton:", len({id(r.config) for r in reports}))


asyncio.run(main())
```

```text
reports built: 8
provider registrations: 1
Config constructions: 1
shared singleton: 1
```

---

## Performance and concurrency considerations

- **Singleton creation is locked.** `Container.__new__` reads `_instances` without the
  lock first and only acquires the `threading.RLock` on a miss, re-checking inside the
  critical section. Verified: 32 threads constructing the same subclass simultaneously
  observe one single instance.
- **One-shot construction is serialised per key inside a loop.** `SINGLETON` and
  `SCOPED` creations and deferred-provider bootstraps run under an `asyncio.Lock`
  obtained from `__creationLock`, with the cache re-checked after acquiring it.
  Verified: eight tasks resolving the same uncached singleton (whose construction
  suspends) produce one instance and one constructor call; the same holds for a scoped
  service inside one scope, and a deferred provider registers exactly once.
- **Locks are bound to the loop that created them.** `__creation_locks` stores the
  running loop next to each lock and replaces the entry when a different loop asks for
  the same key, so a lock is never awaited from a foreign loop. Two loops driving the
  same container therefore serialise independently, not against each other.
- **The fast paths never take a lock.** A cache hit, a scope hit, a transient binding
  and a key that is not deferred all return before any lock is requested.
- **Nested construction does not deadlock.** Each contract owns its own lock, and a
  concrete type already present on the resolution stack skips the lock entirely, so a
  dependency cycle still surfaces as `CircularDependencyException` instead of blocking.
- **Registration is not locked.** Apart from `__new__`, the module declares no
  synchronisation for `_deferred_providers`, the binding table, the alias table or the
  singleton cache: they are plain dictionaries mutated in place, so registration is
  expected to happen during bootstrap rather than concurrently from several OS threads.
- **Task isolation comes from `contextvars`.** The active scope
  (`"x-orionis-container-context-scope"`) and the circular-dependency stack
  (`"x-orionis-resolution-stack"`) are both `ContextVar`s, so concurrent asyncio tasks
  never share that state. The cycle stack is pushed with a token and restored in a
  `finally` block, so a failed resolution leaves no residue.
- **`make()` has a fast path.** A non-string key already present in the singleton cache
  returns before any alias, deferred-provider or scope lookup runs.
- **Deferred providers run once per key.** Resolved keys are recorded in a set, and the
  registry is checked before that set so that non-deferred types exit after a single
  dictionary lookup.
- **Reflection is cached upstream.** Signature inspection is delegated to
  `orionis.introspection`, whose `_get_signature` and `_get_resolved_signature` helpers
  are wrapped in `functools.lru_cache(maxsize=1024)` keyed by the target object.
- **Facade dispatchers are cached forever.** `_dispatcher_cache` is a module-level
  dictionary keyed by `(facade_class, attribute_name)` with no eviction, so each entry
  keeps a strong reference to the facade class for the lifetime of the process.
- **Pinning removes a resolution per call.** While `_pinned_instance` is set, attribute
  access is a direct `getattr` on the cached object; unpinned access defers to the
  container on every await.
- **`ScopeManager.get()` memoises awaited values.** A stored coroutine is promoted to an
  `asyncio.Task`, awaited once, and replaced by its result.

---

## Compatibility notes

- **Python:** `requires-python = ">=3.14"` in `pyproject.toml`. The module uses
  `typing.Self`, `X | Y` unions and PEP 649 deferred annotation evaluation.
- **Runtime dependencies:** the standard library only (`contextvars`, `importlib`,
  `inspect`, `threading`, `collections`, `abc`, `dataclasses`, `enum`, `asyncio`), plus
  the sibling Orionis modules `orionis.introspection`, `orionis.schemas`,
  `orionis.http` and `orionis.support.entities`. Nothing extra to install beyond
  `pip install orionis`.
- **Import cost:** `container.py` imports `orionis.http.request.Request` and
  `orionis.schemas.validator.Schema` at module level, so importing the container pulls
  those layers in as well.
- **Do not use `from __future__ import annotations` in classes the container builds.**
  With that import, constructor annotations stay strings and the reflection layer
  treats them as forward references of type `str`; the container then injects a `str`
  instead of the intended dependency. Verified: a service annotated
  `def __init__(self, repo: Repo)` inside a module using the future import receives a
  `str`. Modules relying on PEP 649 (the default in 3.14) inject correctly.
- **`Application` is the real container.** `orionis.foundation.application.Application`
  subclasses `Container`, so the framework singleton returned by `Application()` owns
  the bindings used at runtime, and `Facade.resolve()` reaches it automatically.
- **Contract modules use string annotations.** `contracts/container.py`,
  `contracts/service_provider.py` and `contracts/deferrable_provider.py` declare
  `from __future__ import annotations`; comparing them against implementations should
  be done on parameter names, not on resolved annotation objects.
