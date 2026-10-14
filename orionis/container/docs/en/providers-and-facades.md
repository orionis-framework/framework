# Service Providers, facades, and extension

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

## Integration with Orionis

`Application` uses the container as its service registry and provider lifecycle. HTTP and console kernels open scopes; controller, command, middleware, schema, listener, and provider dependencies are resolved from signatures. Nearly every Orionis facade maps to a container contract or alias.

Deferred core providers reduce startup imports until a service is first requested. When concurrently triggered, registration/boot is serialized and dependent resolutions wait for pending provider boot.

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

## Compatibility

The project declares Python 3.14+. The module is platform independent and depends only on standard async/threading/introspection behavior plus Orionis types. Its annotation resolution assumes Python 3.14 semantics used by the project.

## Publish your own service

Save this module as `app/providers/catalog_provider.py`. It defines a contract, implementation, and facade in one file to show their relationship; larger applications can separate them. `register` creates bindings synchronously. `boot` may resolve other services and must await `pin()`. Register `CatalogProvider` using `app.withProviders(CatalogProvider)` before `create()`, or allow discovery under `app/providers`.

After `await app.boot()` in the application process, `CatalogFacade.names()` is synchronous because the provider pinned the singleton. Before pinning, a facade call resolves through an awaitable dispatcher: the facade's appearance alone does not determine whether `await` is needed. The service contract determines whether the actual result is synchronous or asynchronous.

For a deferred provider, inherit from both `ServiceProvider` and `DeferrableProvider` and implement `provides()` with exactly the contracts or aliases you register. An omitted service cannot trigger the provider. Do not pin request state as a singleton facade; a `ScopedFacade` reads an instance already registered in the scope and does not construct it automatically.

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

## Evidence and next steps

[service_provider.py](../../providers/service_provider.py) · [deferrable_provider.py](../../providers/deferrable_provider.py) · [facade.py](../../facades/facade.py)

[Return to the module index](README.md).
