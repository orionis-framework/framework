# orionis.container

> `orionis.container` supplies Orionis's asynchronous dependency-injection container, service lifetimes, request scopes, providers, automatic invocation, and facade dispatch.

## Overview

The container maps contracts or aliases to implementations and creates object graphs from type annotations. It supports prebuilt instances, transient services, process-level singletons, and context-local scoped services. `build` constructs a class, `invoke` injects a function, and `call` injects a named instance method.

Application code usually interacts through `Application`, which extends the container, while framework authors define `ServiceProvider` classes and `Facade` entry points. Deferred providers postpone importing/registering services until a declared contract is requested. HTTP and console kernels create scopes so request/command-local dependencies cannot leak into one another.

## Requirements

- Python 3.14 or newer.
- No optional dependency or external service.
- Runtime type annotations on injectable constructor/function parameters.
- An active `beginScope()` context before resolving a `scoped` binding.
- Forward references must be import-resolvable in the callable's module context.

## Quick start

Register a contract and let constructor annotations build the graph:

```python
import asyncio
from abc import ABC, abstractmethod

from orionis.container.container import Container


class Greeter(ABC):
    @abstractmethod
    def greet(self, name: str) -> str:
        raise NotImplementedError


class EnglishGreeter(Greeter):
    def greet(self, name: str) -> str:
        return f"Hello, {name}!"


class WelcomeService:
    def __init__(self, greeter: Greeter) -> None:
        self.greeter = greeter


class DocsContainer(Container):
    pass


async def main() -> None:
    container = DocsContainer()
    container.singleton(Greeter, EnglishGreeter)
    service = await container.build(WelcomeService)
    print(service.greeter.greet("Orionis"))  # Hello, Orionis!


asyncio.run(main())
```

The unbound `WelcomeService` is auto-built; its annotated `Greeter` dependency resolves through the singleton binding.

Validation: **Executed successfully** on CPython 3.14.6.

## Core concepts

### Contract, concrete, alias, and binding

A binding relates a contract to a compatible concrete class and a `Lifetime`. The contract defaults to the concrete class when `abstract=None`. An optional non-empty alias resolves to that same contract. Registration refuses duplicates unless `override=True`.

### Service lifetimes

- `TRANSIENT`: construct on every resolution.
- `SINGLETON`: construct once per container instance and reuse globally.
- `SCOPED`: construct once in the active scope and discard when the scope closes.
- `instance`: publish an already initialized object globally, or into the active scope when called inside one.

### Automatic resolution and invocation

The container caches reflection plans, combines supplied positional/keyword values with annotated dependencies/defaults, recursively builds class parameters, and awaits returned awaitables. Orionis schema and HTTP request parameters receive specialized handling during callable injection.

### Scope propagation

`ScopeManager` places itself in a `ContextVar`. Child asyncio tasks inherit the context reference, but the manager marks itself closed and clears instances on exit, preventing inherited tasks from resolving stale scoped services afterward.

### Facades

A `Facade` class maps attribute access to a container accessor. Providers may `pin` a resolved singleton for direct calls. `ScopedFacade` never uses the global pinned cache; it reads the service already present in the active scope.

## Module structure

| Area | Responsibility |
|---|---|
| `container.py` | Registration, resolution, auto-wiring, invocation, deferred providers, concurrency guards. |
| `context/` | Async scope lifecycle and current-scope `ContextVar`. |
| `entities/` | Validated bindings and cached invocation plans. |
| `providers/` | Normal and deferrable service-provider bases. |
| `facades/` | Async dispatch, pinning, scoped facade access, metaclasses. |
| `contracts/` | Container, provider, deferrable provider, and facade interfaces. |
| `enums/`, `exceptions/` | `Lifetime` and circular-dependency error. |

## Public API

### `Container`

Import from `orionis.container.container`; the package root intentionally has no re-export surface.

#### Registration

```text
container.instance(Contract, object, alias=None, override=False)
container.transient(Contract, Concrete, alias=None, override=False)
container.singleton(Contract, Concrete, alias=None, override=False)
container.scoped(Contract, Concrete, alias=None, override=False)
```

All return `True`. Concrete classes/instances must implement the supplied contract. Passing `None` as contract uses the concrete/runtime type. Aliases are global only; an instance registered inside a scope cannot declare one. `bound(key)` checks current scope and global registrations.

#### Resolution

```text
await container.make(ContractOrAlias, *args, **kwargs)
await container.build(SomeClass, *args, **kwargs)
```

`make` honors bindings and lifetimes; an unbound class is auto-built. An unbound string alias raises `ValueError`. `build` always expects a class and auto-wires its constructor, after giving a deferred provider a chance to register it.

#### Invocation

```text
await container.invoke(function, *args, **kwargs)
await container.call(instance, "method", *args, **kwargs)
```

Both inject missing annotated parameters and await async results. `invoke` rejects classes; `call` distinguishes a missing attribute from a non-callable one.

#### Scopes

```text
async with container.beginScope() as scope:
    service = await container.make(ScopedContract)
```

`getCurrentScope()` returns the active `ScopeManager` or `None`. A scope may be entered only once. `scope.set`, `get`, and `resolve` support explicitly stored values or coroutines; `resolve` raises `KeyError` when absent.

### `ServiceProvider` and `DeferrableProvider`

Subclass `ServiceProvider`, implement synchronous `register`, and optionally async `boot`. Registration is for bindings; boot is for work that requires all providers to exist. A deferrable provider implements `provides()` to list contracts that trigger lazy registration/boot.

### `Facade` and `ScopedFacade`

Subclass and implement `getFacadeAccessor() -> str | type`. `resolve` requires a booted application, `pin` caches the current instance, and `unpin` clears it. Attribute calls before pinning produce an awaitable dispatcher; providers pin facades whose synchronous methods must be directly available. `ScopedFacade.scopedInstance()` requires an active scope containing its accessor.

### Supporting public types

`Lifetime` is exported from `orionis.container.enums`; `Binding` from `orionis.container.entities`; `CircularDependencyException` from `orionis.container.exceptions`; providers and `Facade` have their own subpackage exports.

## Common workflows

### Bind an interface to one implementation

Choose lifetime, call the corresponding registration method during a provider's `register`, then type-hint the contract in consumers. The container validates subclass compatibility immediately.

### Isolate request state

Register the service with `scoped`, open `async with beginScope()`, and resolve it within that block. Repeated calls share one instance; another scope gets another instance.

### Invoke a handler with DI

Pass the callable to `invoke`, supplying values the caller owns. The container fills remaining annotated service arguments. Use `call` when selecting a method name dynamically, as the console reactor does.

### Expose a service through a facade

Define the accessor, bind the service in a provider, and pin the facade during `boot` for singleton APIs. Use `ScopedFacade` when each request already owns a different instance.

## Examples

### Compare transient and singleton lifetimes

```python
import asyncio

from orionis.container.container import Container


class Service:
    pass


class LifetimeContainer(Container):
    pass


async def main() -> None:
    container = LifetimeContainer()
    container.transient(None, Service)
    first = await container.make(Service)
    second = await container.make(Service)
    print(first is second)  # False

    container.singleton(None, Service, override=True)
    first = await container.make(Service)
    second = await container.make(Service)
    print(first is second)  # True


asyncio.run(main())
```

Validation: **Executed successfully** on CPython 3.14.6.

### Reuse a scoped service only inside one scope

```python
import asyncio

from orionis.container.container import Container


class RequestState:
    pass


class ScopeContainer(Container):
    pass


async def main() -> None:
    container = ScopeContainer()
    container.scoped(None, RequestState)
    async with container.beginScope():
        first = await container.make(RequestState)
        second = await container.make(RequestState)
        print(first is second)  # True
    async with container.beginScope():
        third = await container.make(RequestState)
        print(first is third)   # False


asyncio.run(main())
```

Validation: **Executed successfully** on CPython 3.14.6.

### Inject a function parameter

```python
import asyncio

from orionis.container.container import Container


class Formatter:
    def format(self, value: int) -> str:
        return f"value={value}"


def render(value: int, formatter: Formatter) -> str:
    return formatter.format(value)


class InvokeContainer(Container):
    pass


async def main() -> None:
    container = InvokeContainer()
    container.singleton(None, Formatter)
    print(await container.invoke(render, 7))  # value=7


asyncio.run(main())
```

Validation: **Executed successfully** on CPython 3.14.6.

### Reject a circular dependency

```python
import asyncio

from orionis.container.container import Container
from orionis.container.exceptions import CircularDependencyException


class First:
    def __init__(self, second: "Second") -> None:
        self.second = second


class Second:
    def __init__(self, first: First) -> None:
        self.first = first


# Resolve the one forward reference after both classes exist.
First.__init__.__annotations__["second"] = Second


class CycleContainer(Container):
    pass


async def main() -> None:
    try:
        await CycleContainer().build(First)
    except CircularDependencyException:
        print("cycle detected")


asyncio.run(main())
```

Validation: **Executed successfully** on CPython 3.14.6.

## Configuration

The container consumes no application configuration or environment variables. Bindings are established by core/application providers and runtime registration. Provider lists and deferred-provider metadata belong to application bootstrap rather than a `container` config section.

## Integration with Orionis

`Application` uses the container as its service registry and provider lifecycle. HTTP and console kernels open scopes; controller, command, middleware, schema, listener, and provider dependencies are resolved from signatures. Nearly every Orionis facade maps to a container contract or alias.

Deferred core providers reduce startup imports until a service is first requested. When concurrently triggered, registration/boot is serialized and dependent resolutions wait for pending provider boot.

## Errors and edge cases

- Duplicate contract/alias registration raises `ValueError` unless `override=True`.
- Incorrect contract/concrete or contract/instance relationships raise `TypeError`.
- Scoped resolution without a scope, use of a closed scope, or repeated scope entry raises `RuntimeError`.
- Circular constructor graphs raise `CircularDependencyException`; the resolution stack is task-local.
- Missing annotations without defaults cannot be auto-resolved; explicit arguments can satisfy them.
- A class may be auto-built without registration, but a missing string alias cannot.
- A facade before application boot raises `RuntimeError`. A scoped facade outside its owning scope also raises `RuntimeError`.
- Registration dictionaries are mutable setup state; do not change global bindings concurrently during normal request handling.

## Performance and concurrency

Container construction is singleton-per-subclass via double-checked `threading.RLock`. Reflection/invocation plans are cached. Singleton, scoped, and deferred-provider first construction uses per-key `asyncio.Lock` instances so concurrent tasks on one loop share one result.

Creation locks are replaced when the same container is used from a different event loop; serialization is therefore per loop, not a cross-loop global guarantee. Registration itself is not locked. `ContextVar` scope and resolution stacks isolate asyncio task contexts, while child tasks inherit the active scope reference.

Pinned facades remove repeated container resolution for singleton services. Scoped facades intentionally avoid that optimization to preserve lifetime isolation.

## Compatibility

The project declares Python 3.14+; validation used CPython 3.14.6 on Windows. The module is platform independent and depends only on standard async/threading/introspection behavior plus Orionis types. Its annotation resolution assumes Python 3.14 semantics used by the project.

## Verification notes

Container registration/resolution/invocation, scopes, bindings, reflection plans, providers, facade metaclasses, application consumers, and `tests/container` were inspected. All 253 container tests passed through the Orionis runner on CPython 3.14.6. All five Quick start/Examples programs were executed successfully.
