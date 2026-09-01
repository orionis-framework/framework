---
name: "Orionis DI, Providers and Facades"
description: "Use when working with the Orionis service container, dependency injection, lifetimes and scopes, service providers (eager vs deferrable), facades and pin() semantics, the application lifecycle or bootstrap/config wiring."
applyTo: "orionis/container/**,orionis/foundation/**,orionis/support/facades/**,orionis/**/provider.py,orionis/**/*_provider.py,bootstrap/**,app/providers/**,config/**"
---

# Container, Providers and Facades

## Read the module docs first

| Topic | Manual |
|---|---|
| Container, `Binding`, `Lifetime`, `ScopeManager`, `Facade`/`FacadeMeta` | `orionis/container/docs/README.md` (`.es.md`) |
| Catalogue of the 16 facades + `DateTime` | `orionis/support/facades/docs/README.md` (`.es.md`) |
| Reflection used to resolve dependencies | `orionis/introspection/docs/README.md` |

`orionis/foundation/` has **no** `docs/` yet: for the application lifecycle and
config entities, read the code. Everything below is rules and gotchas, not an
API reference.

## Application lifecycle

1. `Application(...)` in `bootstrap/app.py` — singleton, extends `Container`.
2. `withRouting / withScheduler / withExceptionHandler / withProviders / withMiddleware`
   — declarative config, frozen with `FreezeThaw.freeze()` on boot.
3. `app.create()` — asserts Python version, loads `CORE_CONFIG` + `config/*.py`, sets
   timezone/locale via `DateTime._loadConfig`, self-registers `IApplication`, runs
   `register()` of every provider, stores deferred ones in `_deferred_providers`.
4. `Application.__onStartup()` — runs `boot()` of eager providers. **Only fires under
   the HTTP or CLI runtime**, never from a bare `import bootstrap.app`.
5. Runtime: `handleASGI` / `handleRSGI` (HTTP) or `handleCommand` (CLI).

## Container

- Singleton per subclass (`_instances` dict + `threading.RLock` double-check in
  `__new__`).
- Lifetimes: `TRANSIENT = 1`, `SINGLETON = 2`, `SCOPED = 3`.
- Registration: `bind`, `singleton`, `scoped`, `transient`,
  `instance(contract, obj, alias=None)`. Aliases are strings and are **global only**.
- Resolution is **async**: `make`, `build`, `invoke`, `call`.
  `make()` uses the singleton cache; `build()` always creates a new instance.
- `async with app.beginScope():` for `SCOPED`; resolving scoped without a scope raises
  `RuntimeError`.
- Cycles are detected via a `ContextVar` frozenset stack → `CircularDependencyException`.
- Creation of singletons, scoped services and deferred providers is guarded by
  `__creationLock(key)` (one `asyncio.Lock` per key, bound to the running loop) with
  double-checked locking and an anti-deadlock guard on the resolution stack.
- A parameter annotated with a subclass of `orionis.schemas.schema.Schema` makes the
  container validate the request body automatically.

## Hard DI rules

| Rule | Why |
|---|---|
| **Never** `from __future__ import annotations` in a class the container builds | Reflection treats string annotations as forward refs of type `str` and injects garbage |
| Import constructor types at **runtime** (not under `TYPE_CHECKING`), with file-level `# ruff: noqa: TC001` | Same reason |
| A constructor parameter typed with an **ABC** needs an explicit binding registered first | Otherwise `make()` falls back to `build()` and raises `TypeError: Argument 'concrete' must be a class type, got 'ABCMeta' instead.` |
| Concrete classes auto-resolve without a binding | The container recursively resolves their constructor |
| Inside code built during startup, inject the **contract**, never a facade | Facades are only safe after the `boot()` that pins them |

Private methods that are *not* reflected by the container may annotate with
`TYPE_CHECKING`-only imports (PEP 649 makes annotations lazy).

## Service providers

```python
from orionis.container.providers import ServiceProvider

class AppServiceProvider(ServiceProvider):

    def register(self) -> None:
        """Register application services."""
        self.app.singleton(IMyService, MyService)

    async def boot(self) -> None:
        """Bootstrap application services."""
        await MyFacade.pin()
```

- `register()` is sync and only declares bindings; `boot()` is async and does the wiring.
- `DeferrableProvider.provides()` only declares keys; the real deferred registry is built
  by `Application.create()`.
- The 15 core providers live in `orionis/foundation/core_providers.py`:
  `CacheProvider, CatchProvider, ConnectionManagerProvider, EncrypterProvider,
  HashProvider, LocalizationProvider, LoggerProvider, QueryBuilderProvider,
  ReactorProvider, RouterProvider, ScheduleProvider, SchemaProvider, StorageProvider,
  TestingProvider, ViewServiceProvider`.
- **If a facade is consumed without `await` from synchronous framework code, its provider
  must NOT be deferrable** — it has to be eager so the facade is pinned at startup
  (this is why `HashProvider` and `EncrypterProvider` are eager).

## Facades

`orionis/support/facades/` — each facade only overrides `getFacadeAccessor()`; the
parallel `.pyi` exists solely for editor autocompletion and is never executed.

16 facades: `Application, Cache, Catch, Crypt, DB, Hash, Lang, Log, Reactor, Route,
Schedule, Schema, Session, Storage, Test, View` — plus `DateTime`, which is **not** a
facade but a classmethod-only wrapper over `pendulum` and the single source of truth for
timezone/locale.

```python
# Unpinned: every attribute access returns a _FacadeDispatch
repo = Cache.store("redis")          # _FacadeDispatch, NOT the repository
repo = await Cache.store("redis")    # correct without pin (and pins as a side effect)

# Pinned (after await Facade.pin() or the provider boot): direct passthrough
Hash.make("secret")                  # synchronous, no await
```

- `_FacadeDispatch` implements `__await__`, `__aenter__` and `__aexit__`, so
  `async with Schema.create(...)` requires a pin but `await Schema.create(...)` does not.
- A **real classmethod** defined on the facade subclass (e.g. `DB.table()`) bypasses
  `FacadeMeta.__getattr__` entirely — that hook is only an attribute-not-found fallback.
  Do not delete such an override without grepping for callers that rely on the unpinned
  path.
- `_pinned_instance` is a class attribute shared process-wide. `Session` is pinned and
  unpinned per request inside `StartSessionMiddleware`; concurrent code must read
  `request.state.session` instead.

## Configuration

- Config entities: `orionis/foundation/config/<section>/entities/*.py`, dataclasses
  `frozen=True, kw_only=True` extending `BaseEntity`, validated in `__post_init__`,
  reading env via `default_factory=lambda: Env.get("VAR", default)`.
- `CORE_CONFIG` has 14 sections: `app, auth, cache, database, filesystems, hashing, http,
  logging, mail, queue, scheduler, session, testing, view`.
- The application overrides them in `config/*.py` with `Bootstrap*` classes.
- `app.config("path.to.key")` returns **`None`** for unknown keys — always provide a
  fallback in the consumer.

> Adding or removing a provider, a core command or a config entity field invalidates
> nothing automatically: delete `storage/framework/bootstrap` (or run
> `reactor optimize:clear`) or the app keeps booting with stale compiled metadata.
