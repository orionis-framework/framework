# orionis.container

> `orionis.container` proporciona el contenedor asíncrono de inyección de Orionis, lifetimes, scopes de solicitud, providers, invocación automática y despacho de fachadas.

## Descripción general

El contenedor asigna contratos o alias a implementaciones y crea grafos desde anotaciones de tipo. Admite instancias preparadas, servicios transient, singletons de proceso y servicios scoped locales al contexto. `build` construye una clase, `invoke` inyecta una función y `call` inyecta un método nombrado.

El código de aplicación suele interactuar mediante `Application`, que extiende el contenedor; autores del framework definen `ServiceProvider` y fachadas. Providers diferidos posponen imports/registro hasta solicitar un contrato. Kernels HTTP/console crean scopes para impedir fugas de dependencias locales.

## Requisitos

- Python 3.14 o posterior.
- Sin dependencia opcional ni servicio externo.
- Anotaciones runtime en parámetros inyectables.
- Un contexto `beginScope()` activo antes de resolver un binding `scoped`.
- Referencias adelantadas resolubles en el módulo del callable.

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

Validación: **Executed successfully** en CPython 3.14.6.

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

## Estructura del módulo

| Área | Responsabilidad |
|---|---|
| `container.py` | Registro, resolución, auto-wiring, invocación, providers diferidos y concurrencia. |
| `context/` | Ciclo de scope y `ContextVar`. |
| `entities/` | Bindings validados y planes de invocación. |
| `providers/` | Bases normal y diferible. |
| `facades/` | Despacho async, pinning, acceso scoped y metaclases. |
| `contracts/` | Interfaces. |
| `enums/`, `exceptions/` | `Lifetime` y error de ciclos. |

## API pública

### `Container`

Importa desde `orionis.container.container`; la raíz no reexporta API.

#### Registro

```text
container.instance(Contract, object, alias=None, override=False)
container.transient(Contract, Concrete, alias=None, override=False)
container.singleton(Contract, Concrete, alias=None, override=False)
container.scoped(Contract, Concrete, alias=None, override=False)
```

Todos devuelven `True`. Clases/instancias deben implementar contrato. `None` usa tipo concreto/runtime. Alias solo globales; una instancia dentro de scope no puede declararlo. `bound(key)` comprueba scope y registros globales.

#### Resolución

```text
await container.make(ContractOrAlias, *args, **kwargs)
await container.build(SomeClass, *args, **kwargs)
```

`make` respeta bindings/lifetimes; clase no vinculada se autoconstruye. Alias ausente lanza `ValueError`. `build` exige clase y da oportunidad a provider diferido.

#### Invocación

```text
await container.invoke(function, *args, **kwargs)
await container.call(instance, "method", *args, **kwargs)
```

Ambos inyectan parámetros anotados faltantes y esperan resultados async. `invoke` rechaza clases; `call` distingue atributo ausente/no callable.

#### Scopes

```text
async with container.beginScope() as scope:
    service = await container.make(ScopedContract)
```

`getCurrentScope()` devuelve manager o `None`. Un scope entra una vez. `scope.set/get/resolve` admiten valores/corrutinas; `resolve` lanza `KeyError` si falta.

### `ServiceProvider` y `DeferrableProvider`

Hereda `ServiceProvider`, implementa `register` síncrono y opcionalmente `boot` async. Registro define bindings; boot hace trabajo que necesita providers completos. El diferible implementa `provides()`.

### `Facade` y `ScopedFacade`

Implementa `getFacadeAccessor() -> str | type`. `resolve` exige aplicación iniciada, `pin` almacena instancia y `unpin` limpia. Antes de pin, llamadas producen dispatcher awaitable; providers fijan APIs síncronas. `ScopedFacade.scopedInstance()` exige scope con accessor.

### Tipos de soporte

`Lifetime` está en `orionis.container.enums`; `Binding` en `.entities`; `CircularDependencyException` en `.exceptions`; providers y `Facade` en sus subpaquetes.

## Flujos de trabajo comunes

### Vincular una interfaz

Elige lifetime, registra durante `provider.register` y anota el contrato en consumidores. Compatibilidad se valida inmediatamente.

### Aislar estado de request

Registra con `scoped`, abre `async with beginScope()` y resuelve dentro. Llamadas repetidas comparten; otro scope recibe otra instancia.

### Invocar un handler con DI

Pasa callable a `invoke` y valores que posee el llamador; el contenedor llena servicios. Usa `call` para método dinámico.

### Exponer por fachada

Define accessor, binding y fija durante `boot` para singleton. Usa `ScopedFacade` si cada request posee instancia distinta.

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

Validación: **Executed successfully** en CPython 3.14.6.

### Reutilizar servicio dentro de un scope

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

Validación: **Executed successfully** en CPython 3.14.6.

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

Validación: **Executed successfully** en CPython 3.14.6.

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

Validación: **Executed successfully** en CPython 3.14.6.

## Configuración

El contenedor no consume configuración ni variables. Bindings proceden de providers core/aplicación y registro runtime. Listas/metadata de providers pertenecen al bootstrap, no a sección `container`.

## Integración con Orionis

`Application` usa el contenedor como registro y ciclo de providers. Kernels abren scopes; dependencias de controladores, comandos, middleware, schemas, listeners y providers se resuelven por firmas. Casi toda fachada Orionis mapea a contrato/alias.

Providers diferidos reducen imports; disparos concurrentes serializan registro/boot y resoluciones esperan boot pendiente.

## Errores y casos límite

- Registro duplicado lanza `ValueError` salvo override.
- Relaciones incorrectas lanzan `TypeError`.
- Scoped sin scope, scope cerrado o reentrada lanzan `RuntimeError`.
- Ciclos lanzan `CircularDependencyException`; stack es local a tarea.
- Parámetros sin anotación/default requieren argumento explícito.
- Clase se autoconstruye; alias ausente no.
- Fachada antes de boot o scoped fuera de scope lanza `RuntimeError`.
- No cambies bindings globales concurrentemente durante requests.

## Rendimiento y concurrencia

Container es singleton por subclase mediante `threading.RLock`. Planes se almacenan. Primera construcción singleton/scoped/provider usa `asyncio.Lock` por clave para compartir resultado dentro de un loop.

Locks se reemplazan entre loops: serialización es por loop, no global cross-loop. Registro no está bloqueado. `ContextVar` aísla tareas aunque hijas heredan scope.

Fachadas fijadas evitan resolución repetida; scoped la evitan para preservar aislamiento.

## Compatibilidad

El proyecto declara Python 3.14+; se validó con CPython 3.14.6 en Windows. Es multiplataforma y depende de comportamiento estándar async/threading/introspection más tipos Orionis.

## Notas de verificación

Se inspeccionaron registro/resolución/invocación, scopes, bindings, planes, providers, metaclases, consumidores y `tests/container`. Las 253 pruebas pasaron mediante el runner Orionis en CPython 3.14.6. Los cinco programas se ejecutaron correctamente.
