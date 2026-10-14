# Registrar e invocar servicios

## Inicio rápido

Registra un contrato y deja que las anotaciones construyan el grafo:

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

`WelcomeService` se autoconstruye y su dependencia `Greeter` resuelve el singleton.

## Conceptos principales

### Contrato, concreto, alias y binding

Un binding relaciona contrato con clase compatible y `Lifetime`. El contrato usa la clase concreta si `abstract=None`. Un alias no vacío resuelve el mismo contrato. Duplicados se rechazan salvo `override=True`.

### Lifetimes

- `TRANSIENT`: construye en cada resolución.
- `SINGLETON`: construye una vez por contenedor y reutiliza globalmente.
- `SCOPED`: construye una vez en el scope activo y descarta al cerrar.
- `instance`: publica objeto preparado globalmente o en el scope activo.

### Resolución e invocación automática

El contenedor almacena planes de reflexión, combina valores aportados con dependencias/defaults, construye parámetros recursivamente y espera awaitables. Esquemas Orionis y requests HTTP reciben tratamiento especializado.

### Propagación de scopes

`ScopeManager` se coloca en un `ContextVar`. Tareas hijas heredan referencia, pero al salir se marca cerrado y limpia instancias, impidiendo resolver servicios obsoletos.

### Fachadas

Una `Facade` asigna accesos a un accessor del contenedor. Providers pueden fijar un singleton. `ScopedFacade` no usa caché global: lee el servicio del scope activo.

## Ejemplos

### Comparar transient y singleton

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

### Inyectar parámetro de función

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

### Rechazar dependencia circular

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

## Fuentes y siguientes pasos

[container.py](../../container.py) · [binding.py](../../entities/binding.py) · [invocation.py](../../entities/invocation.py)

[Volver al índice del módulo](README.md).
