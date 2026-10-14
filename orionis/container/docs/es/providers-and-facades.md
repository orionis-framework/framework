# Service Providers, facades y extensión

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

## Integración con Orionis

`Application` usa el contenedor como registro y ciclo de providers. Kernels abren scopes; dependencias de controladores, comandos, middleware, schemas, listeners y providers se resuelven por firmas. Casi toda fachada Orionis mapea a contrato/alias.

Providers diferidos reducen imports; disparos concurrentes serializan registro/boot y resoluciones esperan boot pendiente.

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

## Compatibilidad

El proyecto declara Python 3.14+. Es multiplataforma y depende de comportamiento estándar async/threading/introspection más tipos Orionis.

## Publicar un servicio propio

Este módulo puede guardarse como `app/providers/catalog_provider.py`. Define un contrato, una implementación y una facade en un solo archivo para mostrar la relación; en una aplicación grande puedes separarlos. `register` registra bindings de forma síncrona. `boot` puede resolver otros servicios y debe esperar `pin()`. Registra `CatalogProvider` con `app.withProviders(CatalogProvider)` antes de `create()` o permite su descubrimiento en `app/providers`.

Después de `await app.boot()` en el proceso de aplicación, `CatalogFacade.names()` es una llamada síncrona porque el provider fijó el singleton. Antes de pinning, una llamada de facade se resuelve mediante un dispatcher awaitable: no deduzcas si necesita `await` únicamente por la forma de la facade. El contrato de servicio es la referencia para saber si el resultado real es síncrono o asíncrono.

Para un provider deferred, hereda de `ServiceProvider` y `DeferrableProvider` e implementa `provides()` con exactamente los contratos o aliases que registras. Un servicio omitido en esa lista no puede activar el provider. No fijes una facade de estado de solicitud como singleton; una `ScopedFacade` lee una instancia ya registrada en el scope y no la construye automáticamente.

```python
from abc import ABC, abstractmethod
from orionis.container.providers import ServiceProvider
from orionis.container.facades import Facade

class ICatalog(ABC):
    @abstractmethod
    def names(self) -> list[str]:
        raise NotImplementedError

class MemoryCatalog(ICatalog):
    def names(self) -> list[str]:
        return ["book", "lamp"]

class CatalogFacade(Facade):
    @classmethod
    def getFacadeAccessor(cls) -> type:
        return ICatalog

class CatalogProvider(ServiceProvider):
    def register(self) -> None:
        self.app.singleton(ICatalog, MemoryCatalog)

    async def boot(self) -> None:
        await CatalogFacade.pin()
```

## Fuentes y siguientes pasos

[service_provider.py](../../providers/service_provider.py) · [deferrable_provider.py](../../providers/deferrable_provider.py) · [facade.py](../../facades/facade.py)

[Volver al índice del módulo](README.md).
