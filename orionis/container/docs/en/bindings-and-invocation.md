# Registering and invoking services

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

## Evidence and next steps

[container.py](../../container.py) · [binding.py](../../entities/binding.py) · [invocation.py](../../entities/invocation.py)

[Return to the module index](README.md).
