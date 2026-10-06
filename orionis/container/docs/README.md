# orionis.container

> Resolve services and callable dependencies, manage container scopes and deferred providers, and expose global or scope-local facades.

## Table of contents

- [Requirements](#requirements)
- [Functional overview](#functional-overview)
- [Module structure](#module-structure)
- [API reference](#api-reference)
- [Usage examples](#usage-examples)
- [Design characteristics](#design-characteristics)
- [Performance and concurrency](#performance-and-concurrency)
- [Compatibility notes](#compatibility-notes)
- [Verification and limitations](#verification-and-limitations)

## Requirements

The project declares Python **>=3.14** in [pyproject.toml](../../../pyproject.toml).
Bare `Container` registration, construction, invocation, and scopes do not need
an application bootstrap. There is no container-specific installation extra.
Reflection and schema injection use the framework's core `msgspec` dependency.

Additional preparation depends on the API used:

| Operation | Required preparation and evidence |
| --- | --- |
| Global `Facade.resolve` / `pin` / unpinned dispatch | A cached or lazily obtained `Application` whose `isBooted` is true, plus a resolvable accessor. See [facade.py](../facades/facade.py). `Application.create()` sets that flag after registration; `await Application.boot()` also completes eager provider boot. Do not equate the flag with every service having been booted. |
| `ScopedFacade` | A currently active `ScopeManager` with the exact accessor key already holding a non-`None` service. No application boot or global pin is performed. |
| Implicit schema parameter | A resolvable concrete `Request` whose `data()` provides the payload; the container awaits `Schema.validateAsync`. Supplying the parameter explicitly bypasses this path. |
| Deferred provider | Application registration populates provider metadata. Declare providers through the actual [Application.withProviders](../../foundation/application.py) API and `DeferrableProvider.provides`; a bare Container starts with an empty registry. |

External database, cache, or network services are requirements of injected
services, not requirements introduced by this module. This manual does not
authorize starting them or executing the checkout bootstrap for verification.

## Functional overview

`orionis.container` maps contract classes and string aliases to object
instances or concrete classes, applies transient/singleton/scoped lifetimes,
and injects dependencies into construction and callable execution. It also
coordinates deferred providers and supplies global and scope-local proxies.

### Direct integrations

The controlling implementation is [Container](../container.py).
[Application](../../foundation/application.py) inherits it and prepares provider
metadata. [InvocationPlan](../entities/invocation.py) obtains parameter metadata
from [introspection](../../introspection/dependencies/reflection.py); schema
parameters read [Request](../../http/request.py) and use the asynchronous
[validator](../../schemas/validator.py). [Binding](../entities/binding.py)
inherits [BaseEntity](../../support/entities/base.py).

[KernelHTTP](../../http/kernel.py) warms function/controller plans without
building controllers. The real [Session facade](../../support/facades/session.py)
inherits `ScopedFacade`. These are integration boundaries, not additional API
catalogues for those modules.

### Scope and execution boundaries

Container instances are singleton **per subclass**; application singletons and
service singletons are different caches. A new call to `Container()` does not
create an empty registry. `make`, `build`, `invoke`, and `call` are asynchronous,
but constructors and synchronous handlers run directly on the executing thread.

Scopes and resolution stacks use `ContextVar`. Child tasks inherit the scope
object by reference, including its mutable registry and active flag. A scope
binding is context-local; the object is not copied per task or per container.
The immutable resolution/provider stacks are restored with tokens, not cleared
globally. Closing a scope does not cancel, await, or close stored resources.

## Module structure

All 23 Python files, including initializers, were inspected. There are no
non-Python runtime resources under this module outside its documentation.

| Files | Implemented responsibility and public surface |
| --- | --- |
| [container.py](../container.py) | `Container`: registrations, lifetime resolution, deferred provider coordination, injection and dispatch. |
| [context/manager.py](../context/manager.py), [context/scope.py](../context/scope.py), [context/__init__.py](../context/__init__.py) | `ScopeManager`, `ScopedContext`, `get_current_scope`, `set_current_scope`, `reset_scope`; empty package initializer. |
| [contracts/container.py](../contracts/container.py), [contracts/facade.py](../contracts/facade.py), [contracts/service_provider.py](../contracts/service_provider.py), [contracts/deferrable_provider.py](../contracts/deferrable_provider.py), [contracts/__init__.py](../contracts/__init__.py) | `IContainer`, `IFacade`, `IServiceProvider`, `IDeferrableProvider`; only IFacade is reexported here. |
| [entities/binding.py](../entities/binding.py), [entities/invocation.py](../entities/invocation.py), [entities/__init__.py](../entities/__init__.py) | `Binding`, `InvocationPlan`, `callable_plan`, `constructor_plan`, `warm_controller_plan`; the package exports Binding only. |
| [enums/lifetimes.py](../enums/lifetimes.py), [enums/__init__.py](../enums/__init__.py) | `Lifetime`, reexported by the enum package. |
| [exceptions/container.py](../exceptions/container.py), [exceptions/__init__.py](../exceptions/__init__.py) | `CircularDependencyException`, reexported by the exception package. |
| [facades/facade.py](../facades/facade.py), [facades/meta.py](../facades/meta.py), [facades/__init__.py](../facades/__init__.py) | `Facade`, `ScopedFacade`, `FacadeMeta`, `ScopedFacadeMeta`, private `_FacadeDispatch`; the package exports Facade only. |
| [providers/service_provider.py](../providers/service_provider.py), [providers/deferrable_provider.py](../providers/deferrable_provider.py), [providers/__init__.py](../providers/__init__.py) | `ServiceProvider`, `DeferrableProvider`, both reexported. |
| [__init__.py](../__init__.py) | Empty root initializer: no root-level Container, Facade, or contract reexport. |

## API reference

The following groups describe behavior and constraints. The [literal
declarations](#literal-declarations) preserve source headers, decorators,
annotations, default expressions, fields, aliases, and exports. Those headers
have no bodies and are **reference fragments, not executable scripts**.
Generated and inherited operations are identified separately below.

### Imports and exports

Use `orionis.container.container.Container`, not an assumed root export.
`ScopeManager` and `ScopedContext` come from their defining context modules.
All four contracts can be imported from their defining files; only `IFacade`
is available from `orionis.container.contracts`. `ScopedFacade` and both
metaclasses likewise require defining-module imports. See each initializer
in the [structure table](#module-structure) and its literal `__all__`.

`InvocationPlan` and its three public functions are integration auxiliaries,
not exports of `orionis.container.entities`. Standard-library/third-party
imports and the `T` typing helper in context/manager.py are not independent
container API. Private stores, stacks, `_callable_plan`, and `_FacadeDispatch`
are explained only as needed to describe public behavior.

### Container identity and registration

Source/import: [orionis.container.container.Container](../container.py),
implementing `IContainer`. `__new__(cls, *args: object, **kwargs: object)` uses
a shared class-keyed `_instances` dictionary and a `threading.RLock` with
double checking. `__init__` initializes internal dictionaries once, guarded
by `_Container__initialized` in its instance dictionary. There is no public
container reset, unbind, or disposal API.

| Method | Parameters, result, mutation and explicit errors |
| --- | --- |
| `instance` | `abstract` is a contract class or None to use `type(instance)`; `instance` must be an initialized non-class object. Validate `isinstance` against a supplied contract. Return True. Outside a scope, store a SINGLETON binding plus the object in the global cache. Inside a scope, publish under the contract key without changing global bindings; non-None alias is forbidden there. |
| `transient` | Register `abstract` -> `concrete` with TRANSIENT lifetime; None abstract uses the concrete class. Return True. |
| `singleton` | Same registration with SINGLETON lifetime; first construction is cached under the contract. Return True. |
| `scoped` | Same registration with SCOPED lifetime; registration itself is global, even inside an active scope. Return True. |
| `bound` | Accept a type or alias, return whether its contract is present in the current scope, bindings, or singleton cache. Unknown alias returns False; this does not load deferred providers or consider an unbound auto-buildable class bound. |

For class registrations, both supplied classes must be types and the concrete
must satisfy `issubclass(concrete, abstract)`; otherwise TypeError. Registration
does not instantiate a class or prove that reflection can build it later.
`instance` uses `isinstance` instead. An unhashable lookup key propagates
dictionary TypeError. Other operations invoked by custom classes/metaclasses
can also raise; this is not an exhaustive exception list.

For all four registration methods, `alias` is optional, must be a string when
supplied, and is stripped; a blank string raises ValueError, a non-string
raises TypeError. Lookup keys are not stripped. `override=False` rejects a
duplicate global contract/alias or scoped instance with ValueError;
`override=True` permits replacement. It is used by truthiness, not validated
as a literal bool. Replacing a class binding removes its global cached instance.
It does not clear existing scope entries, old alias names, facade pins, or
objects already handed to callers. Reusing an alias can point it at another
contract. No old service is disposed when replaced.

Global singleton cache lookup precedes scope lookup in `make`: publishing a
scope instance does not supersede a non-None global cached singleton. A warm
singleton or scope hit also ignores newly supplied constructor arguments.
Binding.instance remains None in records created by these methods; the actual
instances are kept in the container/scope caches.

### Container resolution and invocation

Source: [container.py](../container.py), with plans in
[entities/invocation.py](../entities/invocation.py).

| Method | Implemented operation and result |
| --- | --- |
| `make(key, *args, **kwargs)` | Wait for matching pending provider work, check type-key singleton cache, resolve aliases/deferred metadata, check singleton cache again, then current scope, then resolve the binding. An unbound class is built automatically. Unknown alias/non-buildable key raises ValueError. Return the resolved object, not its declared contract. |
| `build(type_, *args, **kwargs)` | Require an actual class before cache/binding lookup (TypeError otherwise), coordinate applicable deferred providers, then construct the supplied class. It never returns the service singleton cache or substitutes a bound implementation for the supplied class. Dependency lifetimes still apply, and a class's own `__new__` can itself reuse an object. |
| `invoke(fn, *args, **kwargs)` | Require a callable that is not a class (TypeError), select a callable plan, inject parameters, call it, and await only when the plan marks the target coroutine-function asynchronous. Return its result. |
| `call(instance, method_name, *args, **kwargs)` | Use `getattr(instance, method_name, None)`, then the same dispatch. Missing/None attribute raises AttributeError; a non-callable raises TypeError. Descriptor/accessor errors propagate. There is no runtime guard that the first argument is necessarily an instance, or a separate method-name validator. |

TRANSIENT builds every time unless an earlier scope hit supplies that key.
SINGLETON serializes the first construction and caches non-None results under
the contract; None is treated as a cache miss. SCOPED requires a non-None
current scope or raises RuntimeError, reuses its entry, and publishes a new
instance under a scope-owned creation lock. A closed inherited scope rejects
new construction/publication; `getCurrentScope` itself can still return it.

`CircularDependencyException` is raised when an argument-bearing construction
revisits its concrete type in the current resolution stack. The pre-lock
check avoids a same-stack lock reentry. The stack token is reset in finally.
This is a local stack check, not a global inter-task wait graph or a timeout.

The permissive callable guard is followed by ReflectionCallable validation:
ordinary Python functions, methods, lambdas, or callable objects exposing the
required function metadata are accepted. It does not imply support for every
built-in callable, functools.partial, or object with only `__call__`. An
unhashable cache target can raise TypeError before reflection. Reflection
validation and signature-inspection errors propagate.

An `async def` callable is awaited once. A synchronous function returning a
coroutine, Future, generator, or other awaitable is not awaited merely because
of its result type; callers receive that object. Provider boot and facade
dispatch use different awaiting rules, described in their own sections.
Constructors/callbacks can raise arbitrary exceptions, including cancellation;
the public operations do not translate or swallow them.

### Injected parameters and schemas

The controlling code is `Container.__resolveSignature` / `__resolveArgument`
in [container.py](../container.py), fed by
[dependency reflection](../../introspection/dependencies/reflection.py).
Literal public annotations on *args/**kwargs are retained in the appendix;
they are declarations, not runtime coercion or type checking.

The signature is processed in declaration order. The reflection layer removes
the bound receiver, names self/cls, and variadic parameters; **ordinary
parameters named args or kwargs remain injectable**. Positional-only and
positional-or-keyword metadata follow the same non-keyword-only branch.

For a non-keyword-only parameter:

1. Consume the next explicit positional value when available.
2. Otherwise consume a matching explicit keyword value, including None.
3. Resolve a deferred provider advertised for its full type path if applicable.
4. For a schema parameter, read Request and validate its payload asynchronously.
5. Resolve a registered parameter type through `make`, except an unresolved
   forward reference represented as typing/str.
6. Otherwise use automatic resolution: unresolved built-in/typing parameters
   raise TypeError; a declared default wins in the fallback; a resolved
   non-default class is passed to `make`.

Keyword-only parameters use the same order without consuming positionals.
Remaining explicit positionals are appended and unused keywords forwarded.
Python therefore still enforces call arity and can raise duplicate/unexpected
argument errors. No conversion or annotation validation is applied to supplied
values. **Explicit values skip deferred provider and request validation work.**

Reflection describes a default-bearing parameter using the type of its default,
not its annotation. A default None makes a parameter non-schema; a registered
default's type can be injected before fallback to that default. Built-in types
without defaults are usable when explicitly supplied or registered. Unsupported
typing constructs are not magically interpreted as union/optional factories.
Unknown string hints raise TypeError with a forward-reference message even if
a string service is registered.

Implicit schemas are subclasses of `msgspec.Struct`, not just Orionis Schema.
The container resolves the concrete [Request](../../http/request.py), awaits
`data()`, then [Schema.validateAsync](../../schemas/validator.py); it does not
produce an HTTP response. Missing request dependencies, parsing errors,
[ValidationException](../../schemas/exceptions/validation.py), custom rules,
and cancellation can propagate. Multiple parameters reuse whatever Request
caches but are each validated. Explicit schemas need not read a request.

### InvocationPlan and plan functions

Source/import: [orionis.container.entities.invocation](../entities/invocation.py).
`InvocationPlan` is `@dataclass(frozen=True, slots=True)` with required
`arguments: tuple[Argument, ...]` and `is_async: bool`. Its positional-capable
constructor, equality, representation, and hash are decorator-generated, not
literal methods in source. Field annotations are not runtime validation, and
referenced metadata/default values are not deeply frozen. There is no BaseEntity
inheritance or toDict method here.

| Function | Parameters, result and limits |
| --- | --- |
| `callable_plan(target)` | For a bound MethodType, use its underlying function with bound=True, excluding the receiver. Otherwise use the target directly. Validate through ReflectionCallable; return reusable InvocationPlan with coroutine classification from inspect.iscoroutinefunction. |
| `constructor_plan(target, constructor)` | Validate a concrete class through ReflectionConcrete; include the current constructor descriptor in the LRU key. Return arguments and is_async=False. Restore unresolved string class-local hints using constructor module globals plus class attributes and the class's own name; accept only resolved class types. |
| `warm_controller_plan(target, method_name)` | Use inspect.getattr_static so custom descriptor getters do not execute. Warm supported ordinary constructor descriptors and instance/static/class action functions; skip missing/custom action descriptors. Return None, without building a controller or resolving services. Ordinary inspected descriptors can still raise reflection errors. |

`constructor_plan` is decorated with lru_cache(maxsize=1024). The private
`_callable_plan` has its own LRU(1024), keyed by underlying callable and receiver
mode. Cache hits reuse the same plan; the cache API on the constructor wrapper
is supplied by functools, not separately declared here. Plans read live
bindings/arguments on each invocation. Replacing a function/constructor changes
the key; mutating the same callable's annotations/defaults does not guarantee
invalidation. Warm-up is subject to capacity, not permanent retention.

The lower [reflection layer](../../introspection/dependencies/reflection.py)
also restores available module-global string hints, independently when another
hint is unavailable, and retains defaults. Constructor-specific repair adds
class-local namespaces. Caught hint-evaluation failures preserve unresolved
metadata; later injection can reject it. This implementation supports the
verified future-annotation cases, contrary to the older blanket prohibition.
It does not guarantee resolution of arbitrary strings or unavailable types.

### ScopeManager and ScopedContext

Source/import: [ScopeManager](../context/manager.py) and
[ScopedContext](../context/scope.py).
`Container.beginScope()` returns a new manager; `getCurrentScope()` casts the
raw context value without validating it or checking isActive.

ScopeManager is slotted and single-use. Before entry it is inactive, but storage
and creationLock are permitted until it has closed. `__aenter__` rejects an
already active/closed manager with RuntimeError, stores a ContextVar token,
marks it active, and returns self. `__aexit__` marks it inactive/closed, clears
instances and its lock map, restores the prior token, returns None, and does
not suppress the block's exception. Tokens must be reset in the owning context;
calling exit before entry or reusing/resetting a token can raise underlying
errors after clearing state.

| Operation | Result, mutation and edge cases |
| --- | --- |
| `manager[key]` | Return stored value or None. No waiting, conversion, or closed-state error. |
| `manager[key] = value` / `set(key, value)` | Store by arbitrary hashable key. After closure raise RuntimeError; ordinary values, coroutines and Tasks are accepted. |
| `key in manager` | Check presence, so a stored None still counts as present. |
| `clear()` | Empty instances only; no return value, resource disposal, task cancellation, or active flag/lock reset. Callable even after closure. |
| `creationLock(key)` | Lazily retain one asyncio.Lock per key **in this manager**. Closed manager raises RuntimeError. No cross-loop replacement logic exists here. |
| `isActive` | Read-only property, False before entry/after exit, including in children retaining the same manager. |
| `await get(key)` | Missing/None -> None. Convert a stored coroutine into a Task and publish it before waiting; await a stored Task, then store its result through the closed-write guard. Return other values, including non-Task Future/awaitable objects, unchanged. |
| `await resolve(key)` | Same get behavior, but raise KeyError if its result is None, even if the key was present. |

Concurrent get calls share a published Task within one loop. A waiter's
cancellation can propagate to that shared Task: no shield is used. Failed Tasks
remain stored and can fail again on later access. A Task completing after exit
cannot republish its result. The coroutine-to-Task assignment itself uses the
internal dictionary directly; storing an unawaited coroutine and then clearing
it does not close it. Manage the resource/task lifecycle explicitly.

`ScopedContext.getCurrentScope()` returns the raw object or None.
`setCurrentScope(scope)` stores it and returns a Token; `reset(token)` restores
the prior binding. It performs no type, activity, or ownership validation.
Module aliases `get_current_scope`, `set_current_scope`, and `reset_scope`
are direct bound get/set/reset methods of the ContextVar, not extra wrappers;
their declarations are assignments, with standard contextvars token semantics.
All Containers consult this same ContextVar. Nested scopes restore the outer
scope. Copying/inheriting context does not copy stored services.

### Binding and Lifetime

Source/import: [Binding](../entities/binding.py), also reexported by entities,
and [Lifetime](../enums/lifetimes.py), also reexported by enums.

Binding is a frozen keyword-only dataclass extending BaseEntity, **without
slots=True**. Its generated constructor takes `contract`, `concrete`,
`instance`, `lifetime`, `alias`; the exact field expressions/metadata are in
the appendix. All default to None except lifetime=Lifetime.TRANSIENT.
`__post_init__` validates only that lifetime is a Lifetime, raising TypeError
otherwise. Contract/concrete/instance/alias are not validated by this record.
Generated frozen assignment guards do not deeply freeze an instance it holds;
generated hashing can fail for unhashable fields.

Inherited [BaseEntity.toDict / getFields](../../support/entities/base.py)
provide recursively copied dictionaries and normalized field descriptions.
toDict serializes enum members by value; getFields can invoke callable defaults
and normalizes metadata. Copy/metadata failures can propagate. These inherited
signatures belong to BaseEntity, not declarations in Binding.

Lifetime is an Enum with TRANSIENT, SINGLETON, SCOPED declared using auto().
Their runtime values are 1, 2, 3 in declaration order. The container compares
these exact members by identity; integer 2 is not a valid Binding lifetime.
Standard Enum construction/member lookup behavior is inherited. No custom
conversion method or additional public exception hierarchy is declared here.

### ServiceProvider and deferred lifecycle

Source/import: [ServiceProvider](../providers/service_provider.py) and
[DeferrableProvider](../providers/deferrable_provider.py), both reexported by
providers. ServiceProvider implements IServiceProvider, stores the supplied
`app: IApplication` directly, and performs no constructor type check.
`register()` and async `boot()` currently contain only docstrings and return
None. The register docstring's NotImplementedError is **not raised by the
implementation**. DeferrableProvider implements IDeferrableProvider independently;
it does not itself inherit ServiceProvider. Its classmethod provides() raises
NotImplementedError until overridden. Merely declaring provides does not
populate a bare Container's registry.

Application's [provider registration](../../foundation/application.py) records
module/class metadata by advertised alias or type path and distinguishes eager
providers from DeferrableProvider. An implementation needing application state
can inherit both bases, as in example 7.

Container's deferred coordination in [container.py](../container.py) is keyed
by **(module, class)**, not by each requested service alone:

1. Find metadata by alias or by type module/name; no metadata is a no-op.
2. Skip already completed providers and allow recursive/inherited bootstrap
   contexts to use their own published services via a context-local stack.
3. Serialize that provider identity using a container creation lock.
4. Import/load/build its class, call synchronous register(), retain its instance,
   and mark every advertised key pending.
5. Await boot only if inspect.iscoroutinefunction(boot); otherwise call it
   synchronously. A sync boot returning an awaitable is not awaited.
6. Only after successful boot mark the identity ready and remove pending state.

Outside that bootstrap context, make/build for matching pending keys wait for
boot. Alias-to-contract and type-to-binding-alias matching also participates;
do not generalize readiness to an arbitrary unadvertised concrete build target.
If boot fails or is cancelled after successful registration, retry reuses the
same provider instance without registering again. Failure during register has
no rollback guarantee; its side effects can survive and the next attempt may
register again. Import/getattr/build/register/boot errors propagate. Metadata
is not validated as a separate public schema, and its protected registry is
not a general-purpose public registration method.

### Facade and FacadeMeta

Source/import: [Facade](../facades/facade.py), reexported by facades, and
[FacadeMeta](../facades/meta.py), available from its defining module.
Facade uses the metaclass but does **not** inherit IFacade at runtime.
Defining a subclass without an accessor is allowed; the default classmethod
getFacadeAccessor() raises NotImplementedError when actually called.
Accessors are a type or string key supported by the real application container.

| Method or operation | Implemented behavior |
| --- | --- |
| `await resolve(*args, **kwargs)` | Lazily obtain/cache Application if `_application` is None. Require isBooted or raise RuntimeError, then await its make(accessor, *args, **kwargs). Do not inspect a pin or automatically set one. |
| `await pin()` | Resolve once and store `_pinned_instance` on cls; return None. This changes subsequent dynamic attributes to direct service access, even for a transient binding. |
| `unpin()` | Set that class attribute to None; return None. Do not clear application or dispatcher caches. |
| Missing class attribute | FacadeMeta.__getattr__ returns getattr(pinned_service, name) when pinned. Otherwise retain a dispatcher function per (facade class, name) and return it. No service is resolved merely by reading/calling that function. |

Unpinned `Facade.method(...)` returns a private `_FacadeDispatch`, not the
service result. `await` resolves the service fresh, reads the named attribute,
calls it when callable, then awaits an awaitable result once. For a non-callable
attribute, use `await Facade.attribute()`; supplied dispatcher arguments are
ignored in that case. Merely reading an unpinned attribute is not an existence
check: even an unknown name obtains a dispatcher; getattr can fail later.

`async with Facade.method(...)` resolves the attribute result and directly
awaits its __aenter__/__aexit__. Unlike the await path it does not first await
a coroutine returned by the service method. Use a sync method returning an
async context manager for that operation. The exit value is delegated, including
exception suppression. Entry before exit is required. Dispatch objects do not
memoize awaited results and hold one mutable context slot; reuse/reentry has
no coordination guarantee. They are not generic attribute-chaining proxies.

Pinned access is ordinary getattr: synchronous values stay synchronous,
coroutine methods still require await, descriptor and missing-attribute errors
are immediate. Real class attributes/classmethods bypass __getattr__ entirely.
Pins/applications are class state and follow inheritance until a subclass assigns
its own value. There is no request-local isolation or automatic invalidation
after binding changes. Provider boot can pin a facade as an independent effect;
awaiting the dispatcher alone does not inherently pin it.

### ScopedFacade and ScopedFacadeMeta

Source/import: [ScopedFacade](../facades/facade.py),
[ScopedFacadeMeta](../facades/meta.py). ScopedFacade inherits Facade, overrides
its lifecycle methods, and uses ScopedFacadeMeta for missing attributes.

`scopedInstance()` requires the raw current context to be a ScopeManager with
isActive=True and a non-None value under **the exact accessor key**; otherwise
RuntimeError. It does not translate global aliases, await a stored Task, call
container.make, auto-build a service, or read a global facade pin.

Async `resolve(*_args, **_kwargs)` ignores the supplied arguments and returns
scopedInstance. Async `pin()` checks availability only and returns None;
unpin() is a no-op returning None. ScopedFacadeMeta.__getattr__ immediately
delegates to getattr(scopedInstance(), name), so synchronous methods/properties
are already direct and async methods remain async. Missing service attributes
raise AttributeError; invalid/inactive scopes raise RuntimeError. Child tasks
retaining a closed scope cannot access the service through this facade.

### Contracts and exceptions

All four contracts are abstract ABC classes; their methods declare contracts
with docstring-only bodies and do not independently perform service resolution.
They do not declare __slots__, and are not runtime validation of annotations.

| Contract | Declared operations and relationship |
| --- | --- |
| [IContainer](../contracts/container.py) | Eleven abstract methods: instance, transient, singleton, scoped, bound, beginScope, getCurrentScope, make, build, invoke, call. Implemented by Container. |
| [IServiceProvider](../contracts/service_provider.py) | Abstract synchronous register and asynchronous boot; implemented by ServiceProvider. |
| [IDeferrableProvider](../contracts/deferrable_provider.py) | Abstract classmethod provides; implemented by DeferrableProvider's raising placeholder. |
| [IFacade](../contracts/facade.py) | Abstract classmethods getFacadeAccessor, resolve, pin, unpin; a typing contract, not a runtime base of Facade. |

[CircularDependencyException](../exceptions/container.py) directly inherits
Exception with no custom constructor or base module exception. Standard args,
message/traceback/chaining semantics are inherited. See [resolution](#container-resolution-and-invocation)
for the actual condition that raises it. TypeError, ValueError, RuntimeError,
AttributeError, KeyError, validation errors, and arbitrary invoked failures
remain distinct; none is universally wrapped into this exception.

### Literal declarations

Each owner below is linked to the inspected source. Class fields describe
generated constructors and constants; class headers do not reproduce generated
signatures. No-body declaration fragments preserve the code literally, including
comments attached to signatures, and are not examples to run independently.

#### __init__.py

Source: [orionis/container/__init__.py](../__init__.py).

No directly declared public API; empty package initializer.

#### container.py

Source: [orionis/container/container.py](../container.py).

`Container`

```python
class Container(IContainer):
```

`Container.__new__`

```python
def __new__(cls, *args: object, **kwargs: object) -> Self:
```

`Container.__init__`

```python
def __init__(self) -> None:
```

`Container.instance`

```python
def instance(
    self,
    abstract: type[Any] | None,
    instance: object,
    *,
    alias: str | None = None,
    override: bool = False,
) -> bool:
```

`Container.transient`

```python
def transient(
    self,
    abstract: type[Any] | None,
    concrete: type[Any],
    *,
    alias: str | None = None,
    override: bool = False,
) -> bool:
```

`Container.singleton`

```python
def singleton(
    self,
    abstract: type[Any] | None,
    concrete: type[Any],
    *,
    alias: str | None = None,
    override: bool = False,
) -> bool:
```

`Container.scoped`

```python
def scoped(
    self,
    abstract: type[Any] | None,
    concrete: type[Any],
    *,
    alias: str | None = None,
    override: bool = False,
) -> bool:
```

`Container.bound`

```python
def bound(
    self,
    key: type[Any] | str,
) -> bool:
```

`Container.beginScope`

```python
def beginScope(self) -> ScopeManager:
```

`Container.getCurrentScope`

```python
def getCurrentScope(self) -> ScopeManager | None:
```

`Container.make`

```python
async def make(
    self,
    key: type[Any] | str,
    *args: tuple[Any, ...],
    **kwargs: dict[str, Any],
) -> Any:
```

`Container.build`

```python
async def build(
    self,
    type_: Callable[..., Any],
    *args: tuple[Any, ...],
    **kwargs: dict[str, Any],
) -> Any:
```

`Container.invoke`

```python
async def invoke(
    self,
    fn: Callable[..., Any],
    *args: tuple[Any, ...],
    **kwargs: dict[str, Any],
) -> Any:
```

`Container.call`

```python
async def call(
    self,
    instance: object,
    method_name: str,
    *args: object,
    **kwargs: object,
) -> Any:
```

#### context/__init__.py

Source: [orionis/container/context/__init__.py](../context/__init__.py).

No directly declared public API; empty package initializer.

#### context/manager.py

Source: [orionis/container/context/manager.py](../context/manager.py).

`ScopeManager`

```python
class ScopeManager:

    # ruff: noqa: ANN401
```

`ScopeManager fields`

```python
__slots__ = ("__active", "__closed", "__creation_locks", "_instances", "_token")
```

`ScopeManager.__init__`

```python
def __init__(self) -> None:
```

`ScopeManager.creationLock`

```python
def creationLock(self, key: object) -> asyncio.Lock:
```

`ScopeManager.isActive`

```python
@property
def isActive(self) -> bool:
```

`ScopeManager.__getitem__`

```python
def __getitem__(self, key: object) -> object | None:
```

`ScopeManager.__setitem__`

```python
def __setitem__(self, key: object, value: object) -> None:
```

`ScopeManager.__contains__`

```python
def __contains__(self, key: object) -> bool:
```

`ScopeManager.clear`

```python
def clear(self) -> None:
```

`ScopeManager.__aenter__`

```python
async def __aenter__(self) -> Self:
```

`ScopeManager.__aexit__`

```python
async def __aexit__(
    self,
    exc_type: type[BaseException] | None,
    exc_val: BaseException | None,
    exc_tb: types.TracebackType | None,
) -> None:
```

`ScopeManager.get`

```python
async def get(self, key: object) -> Any | None:
```

`ScopeManager.set`

```python
def set(self, key: object, value: Any) -> None:
```

`ScopeManager.resolve`

```python
async def resolve(self, key: object) -> Any:
```

#### context/scope.py

Source: [orionis/container/context/scope.py](../context/scope.py).

`ScopedContext`

```python
class ScopedContext:

    # ruff: noqa: SLF001

    # Define a context variable to hold the active scope.
    # The default value is None, indicating no active scope.
```

`ScopedContext.getCurrentScope`

```python
@classmethod
def getCurrentScope(cls) -> object | None:
```

`ScopedContext.setCurrentScope`

```python
@classmethod
def setCurrentScope(cls, scope: object) -> contextvars.Token:
```

`ScopedContext.reset`

```python
@classmethod
def reset(cls, token: contextvars.Token) -> None:
```

`get_current_scope`

```python
get_current_scope = ScopedContext._active_scope.get
```

`set_current_scope`

```python
set_current_scope = ScopedContext._active_scope.set
```

`reset_scope`

```python
reset_scope       = ScopedContext._active_scope.reset
```

#### contracts/__init__.py

Source: [orionis/container/contracts/__init__.py](../contracts/__init__.py).

`__all__`

```python
__all__ = ["IFacade"]
```

#### contracts/container.py

Source: [orionis/container/contracts/container.py](../contracts/container.py).

`IContainer`

```python
class IContainer(ABC):

    # ruff: noqa: ANN401

    @abstractmethod
```

`IContainer.instance`

```python
@abstractmethod
def instance(
    self,
    abstract: type[Any] | None,
    instance: object,
    *,
    alias: str | None = None,
    override: bool = False,
) -> bool:
```

`IContainer.transient`

```python
@abstractmethod
def transient(
    self,
    abstract: type[Any] | None,
    concrete: type[Any],
    *,
    alias: str | None = None,
    override: bool = False,
) -> bool:
```

`IContainer.singleton`

```python
@abstractmethod
def singleton(
    self,
    abstract: type[Any] | None,
    concrete: type[Any],
    *,
    alias: str | None = None,
    override: bool = False,
) -> bool:
```

`IContainer.scoped`

```python
@abstractmethod
def scoped(
    self,
    abstract: type[Any] | None,
    concrete: type[Any],
    *,
    alias: str | None = None,
    override: bool = False,
) -> bool:
```

`IContainer.bound`

```python
@abstractmethod
def bound(
    self,
    key: type[Any] | str,
) -> bool:
```

`IContainer.beginScope`

```python
@abstractmethod
def beginScope(self) -> ScopeManager:
```

`IContainer.getCurrentScope`

```python
@abstractmethod
def getCurrentScope(self) -> ScopeManager | None:
```

`IContainer.make`

```python
@abstractmethod
async def make(
    self,
    key: type[Any] | str,
    *args: tuple[Any, ...],
    **kwargs: dict[str, Any],
) -> Any:
```

`IContainer.build`

```python
@abstractmethod
async def build(
    self,
    type_: Callable[..., Any],
    *args: tuple[Any, ...],
    **kwargs: dict[str, Any],
) -> Any:
```

`IContainer.invoke`

```python
@abstractmethod
async def invoke(
    self,
    fn: Callable[..., Any],
    *args: tuple[Any, ...],
    **kwargs: dict[str, Any],
) -> Any:
```

`IContainer.call`

```python
@abstractmethod
async def call(
    self,
    instance: object,
    method_name: str,
    *args: object,
    **kwargs: object,
) -> Any:
```

#### contracts/deferrable_provider.py

Source: [orionis/container/contracts/deferrable_provider.py](../contracts/deferrable_provider.py).

`IDeferrableProvider`

```python
class IDeferrableProvider(ABC):

    @classmethod
    @abstractmethod
```

`IDeferrableProvider.provides`

```python
@classmethod
@abstractmethod
def provides(cls) -> list[type | str]:
```

#### contracts/facade.py

Source: [orionis/container/contracts/facade.py](../contracts/facade.py).

`IFacade`

```python
class IFacade(ABC):

    @classmethod
    @abstractmethod
```

`IFacade.getFacadeAccessor`

```python
@classmethod
@abstractmethod
def getFacadeAccessor(cls) -> str | type:
```

`IFacade.resolve`

```python
@classmethod
@abstractmethod
async def resolve(cls, *args: object, **kwargs: object) -> object:
```

`IFacade.pin`

```python
@classmethod
@abstractmethod
async def pin(cls) -> None:
```

`IFacade.unpin`

```python
@classmethod
@abstractmethod
def unpin(cls) -> None:
```

#### contracts/service_provider.py

Source: [orionis/container/contracts/service_provider.py](../contracts/service_provider.py).

`IServiceProvider`

```python
class IServiceProvider(ABC):

    @abstractmethod
```

`IServiceProvider.register`

```python
@abstractmethod
def register(self) -> None:
```

`IServiceProvider.boot`

```python
@abstractmethod
async def boot(self) -> None:
```

#### entities/__init__.py

Source: [orionis/container/entities/__init__.py](../entities/__init__.py).

`__all__`

```python
__all__ = ["Binding"]
```

#### entities/binding.py

Source: [orionis/container/entities/binding.py](../entities/binding.py).

`Binding`

```python
@dataclass(frozen=True, kw_only=True)
class Binding(BaseEntity):
```

`Binding fields`

```python
contract: type | None = field(
        default=None,
        metadata={
            "description": "Contract of the concrete class to inject.",
            "default": None,
        },
    )
concrete: type | None = field(
        default=None,
        metadata={
            "description": "Concrete class implementing the contract.",
            "default": None,
        },
    )
instance: object | None = field(
        default=None,
        metadata={
            "description": "Concrete instance of the class, if provided.",
            "default": None,
        },
    )
lifetime: Lifetime = field(
        default=Lifetime.TRANSIENT,
        metadata={
            "description": "Lifetime of the instance.",
            "default": Lifetime.TRANSIENT,
        },
    )
alias: str | None = field(
        default=None,
        metadata={
            "description": "Alias for resolving the dependency from the container.",
            "default": None,
        },
    )
```

`Binding.__post_init__`

```python
def __post_init__(self) -> None:
```

#### entities/invocation.py

Source: [orionis/container/entities/invocation.py](../entities/invocation.py).

`InvocationPlan`

```python
@dataclass(frozen=True, slots=True)
class InvocationPlan:
```

`InvocationPlan fields`

```python
arguments: tuple[Argument, ...]
is_async: bool
```

`callable_plan`

```python
def callable_plan(target: Callable) -> InvocationPlan:
```

`constructor_plan`

```python
@lru_cache(maxsize=1024)
def constructor_plan(target: type, constructor: object) -> InvocationPlan:
```

`warm_controller_plan`

```python
def warm_controller_plan(target: type, method_name: str) -> None:
```

#### enums/__init__.py

Source: [orionis/container/enums/__init__.py](../enums/__init__.py).

`__all__`

```python
__all__ = ["Lifetime"]
```

#### enums/lifetimes.py

Source: [orionis/container/enums/lifetimes.py](../enums/lifetimes.py).

`Lifetime`

```python
class Lifetime(Enum):
```

`Lifetime fields`

```python
TRANSIENT = auto()
SINGLETON = auto()
SCOPED = auto()
```

#### exceptions/__init__.py

Source: [orionis/container/exceptions/__init__.py](../exceptions/__init__.py).

`__all__`

```python
__all__ = ["CircularDependencyException"]
```

#### exceptions/container.py

Source: [orionis/container/exceptions/container.py](../exceptions/container.py).

`CircularDependencyException`

```python
class CircularDependencyException(Exception):
```

#### facades/__init__.py

Source: [orionis/container/facades/__init__.py](../facades/__init__.py).

`__all__`

```python
__all__ = ["Facade"]
```

#### facades/facade.py

Source: [orionis/container/facades/facade.py](../facades/facade.py).

`Facade`

```python
class Facade(metaclass=FacadeMeta):

    # ruff: noqa: PLC0415

    # Cached application instance shared across all facade subclasses
```

`Facade.getFacadeAccessor`

```python
@classmethod
def getFacadeAccessor(cls) -> str | type:
```

`Facade.resolve`

```python
@classmethod
async def resolve(cls, *args: object, **kwargs: object) -> object:
```

`Facade.pin`

```python
@classmethod
async def pin(cls) -> None:
```

`Facade.unpin`

```python
@classmethod
def unpin(cls) -> None:
```

`ScopedFacade`

```python
class ScopedFacade(Facade, metaclass=ScopedFacadeMeta):
```

`ScopedFacade.scopedInstance`

```python
@classmethod
def scopedInstance(cls) -> object:
```

`ScopedFacade.resolve`

```python
@classmethod
async def resolve(cls, *_args: object, **_kwargs: object) -> object:
```

`ScopedFacade.pin`

```python
@classmethod
async def pin(cls) -> None:
```

`ScopedFacade.unpin`

```python
@classmethod
def unpin(cls) -> None:
```

#### facades/meta.py

Source: [orionis/container/facades/meta.py](../facades/meta.py).

`FacadeMeta`

```python
class FacadeMeta(type):
```

`FacadeMeta.__getattr__`

```python
def __getattr__(cls, name: str) -> object:
```

`ScopedFacadeMeta`

```python
class ScopedFacadeMeta(FacadeMeta):
```

`ScopedFacadeMeta.__getattr__`

```python
def __getattr__(cls, name: str) -> object:
```

#### providers/__init__.py

Source: [orionis/container/providers/__init__.py](../providers/__init__.py).

`__all__`

```python
__all__ = ["DeferrableProvider", "ServiceProvider"]
```

#### providers/deferrable_provider.py

Source: [orionis/container/providers/deferrable_provider.py](../providers/deferrable_provider.py).

`DeferrableProvider`

```python
class DeferrableProvider(IDeferrableProvider):
```

`DeferrableProvider.provides`

```python
@classmethod
def provides(cls) -> list[type | str]:
```

#### providers/service_provider.py

Source: [orionis/container/providers/service_provider.py](../providers/service_provider.py).

`ServiceProvider`

```python
class ServiceProvider(IServiceProvider):

    # ruff: noqa: TC001
```

`ServiceProvider.__init__`

```python
def __init__(
    self,
    app: IApplication,
) -> None:
```

`ServiceProvider.register`

```python
def register(self) -> None:
```

`ServiceProvider.boot`

```python
async def boot(self) -> None:
```


## Usage examples

Run each Python block as an independent script with the framework and its core
dependencies installed on Python 3.14+. For the verified local executions,
imports pointed to the inspected checkout, bytecode was disabled, processes and
resource trees were separate, and writes were blocked outside the temporary
validation root. No script uses the checkout bootstrap or a real external service.

### 1. Register lifetimes, aliases and replacements

Expect contract/alias identity for the singleton, fresh Report instances for
transient resolution, explicit argument precedence, and live binding replacement.

```python
import asyncio
from orionis.container.container import Container

class Repository:
    pass

class MemoryRepository(Repository):
    pass

class ReplacementRepository(Repository):
    pass

class Report:
    def __init__(self, repository: Repository, prefix: str = "report") -> None:
        self.repository = repository
        self.prefix = prefix

async def main() -> None:
    container = Container()
    assert container.singleton(Repository, MemoryRepository, alias=" repository ")
    first = await container.make(Repository)
    assert first is await container.make("repository")
    assert container.bound("repository") and not container.bound(" repository ")
    assert await container.build(MemoryRepository) is not first
    container.transient(None, Report)
    report = await container.make(Report)
    assert report is not await container.make(Report)
    assert report.repository is first
    explicit = MemoryRepository()
    prepared = await container.build(Report, explicit, prefix="prepared")
    assert prepared.repository is explicit and prepared.prefix == "prepared"
    container.singleton(Repository, ReplacementRepository, override=True)
    replaced = await container.build(Report)
    assert isinstance(replaced.repository, ReplacementRepository)
    assert report.repository is first

asyncio.run(main())
```

### 2. Invoke callables and handle real resolution errors

Expect explicit count/keyword values to be used, an unresolved built-in to
raise TypeError, an unknown alias to raise ValueError, and a self-referencing
constructor to raise the module's circular dependency exception.

```python
import asyncio
from orionis.container.container import Container
from orionis.container.exceptions import CircularDependencyException

def multiply(count: int, *, factor: int = 2) -> int:
    return count * factor

class Cycle:
    def __init__(self, dependency: "Cycle") -> None:
        self.dependency = dependency

async def main() -> None:
    container = Container()
    assert await container.invoke(multiply, 4, factor=3) == 12
    assert await container.invoke(multiply, count=4) == 8
    failures = []
    try:
        await container.invoke(multiply)
    except TypeError:
        failures.append("builtin")
    try:
        await container.make("missing.alias")
    except ValueError:
        failures.append("alias")
    try:
        await container.build(Cycle)
    except CircularDependencyException:
        failures.append("cycle")
    assert failures == ["builtin", "alias", "cycle"]

asyncio.run(main())
```

### 3. Share scoped services and use a ScopedFacade

Expect same-scope identity, a distinct nested service, restoration of the outer
scope, and immediate facade rejection after closure. The child task reads the
same service that the outer scope owns.

```python
import asyncio
from orionis.container.container import Container
from orionis.container.facades.facade import ScopedFacade

class SessionValue:
    def __init__(self) -> None:
        self.label = "unset"

class LocalValue(ScopedFacade):
    @classmethod
    def getFacadeAccessor(cls) -> type:
        return SessionValue

async def main() -> None:
    container = Container()
    container.scoped(None, SessionValue)
    try:
        await container.make(SessionValue)
    except RuntimeError:
        pass
    else:
        raise AssertionError("A scoped service resolved without a scope")
    async with container.beginScope() as outer:
        first = await container.make(SessionValue)
        first.label = "outer"
        assert first is await container.make(SessionValue)
        child = asyncio.create_task(LocalValue.resolve())
        assert await child is first and LocalValue.label == "outer"
        async with container.beginScope():
            second = await container.make(SessionValue)
            second.label = "inner"
            assert second is not first and LocalValue.label == "inner"
        assert container.getCurrentScope() is outer
        assert LocalValue.label == "outer"
    assert not outer.isActive and SessionValue not in outer
    try:
        LocalValue.scopedInstance()
    except RuntimeError:
        pass
    else:
        raise AssertionError("A closed scope exposed its service")

asyncio.run(main())
```

### 4. Resolve stored tasks and preserve context tokens

Expect a coroutine result to be cached, None to count as a present key but fail
resolve, temporary context clearing to be reversible, and writes to a closed
manager to fail. No unresolved coroutine is discarded by cleanup.

```python
import asyncio
from orionis.container.context.manager import ScopeManager
from orionis.container.context.scope import (
    get_current_scope,
    reset_scope,
    set_current_scope,
)

async def produce() -> str:
    await asyncio.sleep(0)
    return "ready"

async def main() -> None:
    manager = ScopeManager()
    manager.set("before", "entry")
    assert not manager.isActive
    async with manager:
        assert get_current_scope() is manager
        assert manager.creationLock("job") is manager.creationLock("job")
        manager.set("job", produce())
        results = await asyncio.gather(manager.resolve("job"), manager.get("job"))
        assert results == ["ready", "ready"] and manager["job"] == "ready"
        manager["null"] = None
        assert "null" in manager and await manager.get("null") is None
        try:
            await manager.resolve("null")
        except KeyError:
            pass
        else:
            raise AssertionError("None was accepted as a resolved instance")
        token = set_current_scope(None)
        try:
            assert get_current_scope() is None
        finally:
            reset_scope(token)
        assert get_current_scope() is manager
        manager.clear()
        assert manager.isActive and "job" not in manager
    assert get_current_scope() is None and not manager.isActive
    try:
        manager.set("late", "value")
    except RuntimeError:
        pass
    else:
        raise AssertionError("A closed manager accepted a value")

asyncio.run(main())
```

### 5. Inspect Binding and reusable invocation plans

Expect a shared bound-method plan without retaining the first controller,
constructor metadata describing Dependency, and enum serialization through
the inherited entity API. Integer lifetime input is a real definition error.

```python
import asyncio
import gc
import weakref
from orionis.container.container import Container
from orionis.container.entities.binding import Binding
from orionis.container.entities.invocation import (
    callable_plan,
    constructor_plan,
    warm_controller_plan,
)
from orionis.container.enums import Lifetime

class Dependency:
    pass

class Controller:
    def __init__(self, dependency: Dependency) -> None:
        self.dependency = dependency

    async def action(self, count: int = 2) -> int:
        return count

async def main() -> None:
    container = Container()
    container.singleton(None, Dependency)
    warm_controller_plan(Controller, "action")
    first = await container.build(Controller)
    second = await container.build(Controller)
    plan = callable_plan(first.action)
    assert plan is callable_plan(second.action) and plan.is_async
    constructor = constructor_plan(Controller, Controller.__init__)
    assert constructor.arguments[0].type is Dependency
    assert await container.call(second, "action", count=7) == 7
    reference = weakref.ref(first)
    del first
    gc.collect()
    assert reference() is None
    binding = Binding(contract=Dependency, concrete=Dependency,
                      lifetime=Lifetime.SINGLETON)
    assert binding.toDict()["lifetime"] == 2
    assert len(binding.getFields()) == 5
    try:
        Binding(lifetime=2)
    except TypeError:
        pass
    else:
        raise AssertionError("An integer was accepted as Lifetime")

asyncio.run(main())
```

### 6. Inject a schema from a real local Request

This uses real ASGITransportAdapter, Request, and Schema validation without an
HTTP server. Expect parsed quantity=3, a propagated ValidationException for
invalid quantity, and an explicit payload to work with no current Request.

```python
import asyncio
from orionis.container.container import Container
from orionis.http.adapters.request.asgi import ASGITransportAdapter
from orionis.http.enums.interfaces import Interface
from orionis.http.request import Request
from orionis.schemas.exceptions.validation import ValidationException
from orionis.schemas.schema import Schema

class Payload(Schema):
    quantity: int

async def action(payload: Payload, *, increment: int = 2) -> int:
    return payload.quantity + increment

def make_request(body: bytes) -> Request:
    messages = [{"type": "http.request", "body": body, "more_body": False}]
    async def receive() -> dict[str, object]:
        return messages.pop(0)
    scope = {
        "type": "http", "method": "POST", "scheme": "http", "path": "/",
        "query_string": b"", "server": ("localhost", 80),
        "headers": [(b"content-type", b"application/json")],
    }
    return Request(Interface.ASGI, ASGITransportAdapter(scope),
                   receive_or_protocol=receive)

async def main() -> None:
    container = Container()
    async with container.beginScope():
        request = make_request(b'{"quantity":3}')
        container.instance(Request, request)
        assert await container.invoke(action) == 5
        assert await request.data() == {"quantity": 3}
    async with container.beginScope():
        container.instance(Request, make_request(b'{"quantity":"invalid"}'))
        try:
            await container.invoke(action)
        except ValidationException as error:
            assert "quantity" in error.errors
        else:
            raise AssertionError("An invalid body was accepted")
    assert await container.invoke(action, Payload(quantity=9)) == 11

asyncio.run(main())
```

### 7. Boot a deferred multi-service provider and global facade

The temporary Application performs real registration and eager boot, then
concurrent lookups trigger the custom deferred provider once. Expect both
contracts to be ready, unpinned await/context dispatch to work, and pinning
to make synchronous service access direct. Temporary cwd/log cleanup is explicit.

```python
import asyncio
import logging
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

previous = Path.cwd()
with tempfile.TemporaryDirectory(prefix="container-provider-") as directory:
    os.chdir(directory)
    try:
        from orionis.container.facades.facade import Facade
        from orionis.container.providers import DeferrableProvider, ServiceProvider
        from orionis.foundation.application import Application

        class Catalogue:
            label = "catalogue"

            def count(self) -> int:
                return 7

            @asynccontextmanager
            async def context(self):
                yield self

        class Secondary:
            pass

        class CatalogueProvider(ServiceProvider, DeferrableProvider):
            registrations = 0
            boots = 0

            @classmethod
            def provides(cls) -> list[type | str]:
                return [Catalogue, Secondary, "docs.catalogue", "docs.secondary"]

            def register(self) -> None:
                type(self).registrations += 1
                self.app.singleton(None, Catalogue, alias="docs.catalogue")
                self.app.singleton(None, Secondary, alias="docs.secondary")

            async def boot(self) -> None:
                type(self).boots += 1
                await self.app.make(Catalogue)
                await asyncio.sleep(0)

        class CatalogueFacade(Facade):
            @classmethod
            def getFacadeAccessor(cls) -> type:
                return Catalogue

        async def main() -> None:
            app = Application(base_path=Path(directory))
            app.withProviders(CatalogueProvider)
            await app.boot()
            assert CatalogueProvider.registrations == 0
            first, second = await asyncio.gather(
                app.make(Catalogue), app.make("docs.secondary"),
            )
            assert isinstance(second, Secondary)
            assert CatalogueProvider.registrations == CatalogueProvider.boots == 1
            assert await CatalogueFacade.count() == 7
            assert await CatalogueFacade.label() == "catalogue"
            async with CatalogueFacade.context() as entered:
                assert entered is first
            await CatalogueFacade.pin()
            assert CatalogueFacade.count() == 7 and CatalogueFacade.label == "catalogue"
            CatalogueFacade.unpin()

        asyncio.run(main())
    finally:
        logging.shutdown()
        os.chdir(previous)
```

## Design characteristics

| Observed mechanism | Concrete consequence |
| --- | --- |
| Container singleton registry plus idempotent initialization | Repeated construction retains registrations; distinct subclasses have distinct singleton identities while normally sharing the class-keyed registry. |
| Frozen Binding and InvocationPlan dataclasses | Records resist generated-field assignment, not deep mutation. Binding has an instance dict; InvocationPlan is slotted. Generated methods are not literal source declarations. |
| ScopeManager slots and ContextVar token | No per-manager instance dict; nested contexts restore the prior scope while children can retain the same closed object. |
| ABC contracts without __slots__ | They describe operations, not storage-free implementations or runtime enforcement of annotations. Container/providers retain instance dictionaries. |
| Bound-method plans keyed by function, not receiver | Different controller instances share metadata without the plan retaining each receiver. Referenced functions/classes/defaults still occupy bounded caches. |
| Missing-attribute metaclass dispatch | Real facade attributes bypass proxies; pin changes missing-attribute behavior globally on that class; ScopedFacade resolves against the active scope each time. |
| Provider identity and pending registries | Multiple advertised contracts share startup and retry state; services are published at register time but matching external resolution waits for boot. |

## Performance and concurrency

### Caches and retained state

Sources: [container.py](../container.py), [invocation.py](../entities/invocation.py),
[scope manager](../context/manager.py), [facade metadata](../facades/meta.py).
Singleton/alias/binding dictionaries, registered/pending deferred providers,
creation-lock registry, and Container._instances have no public capacity limit
or reset. Completed provider instances are removed from the retry registry;
their identity remains marked ready. Cancellation before publication does not
populate a singleton/scoped result, but constructor/register side effects
already performed are not undone.

A callable/constructor plan materializes ordered parameter metadata as a tuple.
Each dispatch assembles a positional list and keyword dict, reads current
bindings, and does not mutate the caller's dictionary expanded via **kwargs.
Reflection has additional bounded LRU caches in its own module. The facade
dispatcher cache is **unbounded** by (class, name); cached functions retain the
class/name and create a new pending object per call. Pins retain service objects.
No module benchmark or allocation-rate claim was made for this task.

### Task, scope, loop and thread boundaries

Container.__new__ serializes subclass instance creation with a threading.RLock.
That does not serialize concurrent __init__, registrations, callbacks, or all
service use. The class docstring expressly limits other guarantees to one-loop
one-shot work. Mutable service objects remain responsible for their own safety.

Singleton/deferred construction uses a per-container key lock paired with the
running loop; a different loop replaces that registry entry, so there is no
cross-loop global creation exclusion. Scoped construction instead uses locks
owned by each ScopeManager: independent scopes can construct concurrently,
same-scope contenders share construction, and a scope has no foreign-loop lock
replacement. Do not infer that sharing a manager across threads/loops is safe.

The source configures no timeout, global wait graph, resource teardown, or
fairness guarantee. Cancellation releases async-with locks and resets stack
tokens; deferred boot retry retains a successfully registered provider. Children
with an inherited provider stack can participate in their parent's bootstrap.
Registration/override during suspended construction is not a transaction; the
module declares no guarantee for that combination.

`async def` entry points can perform synchronous construction, reflection,
annotation evaluation, imports, register hooks, and synchronous handlers on
the event-loop thread. There is no general executor offload in Container.
Awaiting a deferred facade handles awaitable results; ordinary callable dispatch
does not add that second result-based awaiting rule. Scope clearing/pins are
reference management, not automatic shutdown of resources.

## Compatibility notes

The minimum declared Python version is >=3.14. This checkout uses union syntax,
built-in generic annotations, dataclass slots, ContextVar, asyncio locks/tasks,
and inspect/typing annotation resolution. Validate against the declared target,
not an inferred older syntax minimum. All performed executions used **CPython
3.14.6 on Windows**; other runtimes/platforms were not executed.

| Dependency | Declared range | Lockfile resolution | Installed validation version |
| --- | --- | --- | --- |
| msgspec (core, reflection/schema integration) | >=0.21.1 | 0.22.0 | 0.22.0 |
| markdown (core; document validation here) | >=3.10.3,<4.0 | 3.11 | 3.11 |
| ruff (development lint) | >=0.16.8 | 0.16.9 | 0.16.9 |

Evidence: [pyproject.toml](../../../pyproject.toml), [uv.lock](../../../uv.lock),
and local installed metadata recorded during this execution. Lockfile versions
are resolutions, not supported minimums. Optional deployment dependencies
belong to injected components; no new dependency was installed.

Resolvable module-global string/future annotations now participate in callable
injection, with extra class-local restoration for constructors. Unknown names,
unsupported typing objects, and stale same-object metadata remain separate
limits. Parameters with defaults keep default-derived metadata. None and an
unprovided value are not interchangeable. These distinctions supersede older
documentation/instruction assumptions; no source was altered to reconcile them.

## Verification and limitations

### Inventory and tests

The inventory covers 23 sources, 17 public classes, 61 public/special methods,
three public plan functions, four field blocks, nine alias/export blocks, and
94 literal reference blocks. Every public candidate is mapped to a source and
API group; imported library names and typing helper T are explicitly excluded.
Private integration details are described where they control public behavior,
not catalogued as independent extension APIs.

Native TestingEngine discovery and TestRunner execution used a real booted
temporary Application and a discovery-settings view whose basePath points to
the inspected tests, with result caching disabled. **253 discovered, 253 run,
253 passed**, zero raw failures/errors/skips. An audit hook denied writes outside
the temporary root, external processes and service connections; no denied
operation occurred on the successful run. The initial harness attempt blocked
Windows asyncio's internal socketpair before discovery; the harness was narrowed
to permit that stdlib operation and rerun, without changing framework/tests.

An additional isolated probe confirmed child scope identity, visible closed
state, and rejection of a late publication. Existing tests verify explicit
argument precedence, plan reuse/receiver release, future constructor hints,
multi-contract provider readiness/retry, separate scope construction and
cancelled construction retry. Tests prove their scenarios, not universal
multi-thread/loop safety.

### Example and document status

| Example | Syntax | Local imports | Execution |
| --- | --- | --- | --- |
| 1 | Passed | Passed | Executed successfully. |
| 2 | Passed | Passed | Executed successfully. |
| 3 | Passed | Passed | Executed successfully. |
| 4 | Passed | Passed | Executed successfully. |
| 5 | Passed | Passed | Executed successfully. |
| 6 | Passed | Passed | Executed successfully. |
| 7 | Passed | Passed | Executed successfully. |

Both manuals have 60 corresponding headings and 101 byte-identical code blocks.
All 94 reference blocks match their inventory declarations; 90 public candidates
are mapped to the appropriate API group. Each language's seven scripts passed
syntax, real local-import resolution, and independent execution. There are
105 checked relative links/anchors per manual and 19 in the skill. Its valid
YAML contains only name and description, with derived name orionis-container.
Scoped Ruff passed for orionis/container and tests/container without fixes or
cache; editor diagnostics are clear for the three deliverables.

Scripts, recorded results and resource trees stay outside the repository. The
complete initial snapshot includes hidden, ignored and untracked entries and
all preexisting documentation changes. Source, tests, configuration and other
module documentation are compared against that baseline, not against a clean
HEAD assumption. The final comparison separately records the unrelated change
described below; no additional content was removed from docs, which contains
exactly README.md, README.es.md and SKILL.md, with no subdirectories.

### Remaining limits

Verified discrepancies include explicit-before-injected parameter precedence,
ordinary args/kwargs names, string-hint restoration, scope-owned creation locks,
ScopedFacade's distinct lifecycle, and ServiceProvider.register's no-op despite
its docstring's stated error. Callback/dependency errors are not an exhaustive
list. No fixes, automatic formatting, benchmarks, installs or Git index edits
were performed as part of documentation.

> ⚠️ Not specified in the source: atomic registration/override against an in-flight construction, whole-module cross-loop/thread safety, or automatic disposal of stored/pinned services.

> ⚠️ Not executed in this environment: deployed HTTP traffic, external services used by injected dependencies, Linux/macOS/free-threaded execution, or Python versions other than 3.14.6.

The complete comparison observed an unrelated content change to PUBLISH.ps1
after the baseline. It was preserved without modification or rollback by this
task; a Git-only status comparison would miss this ignored file. The Git index,
HEAD and preexisting tracked changes are checked independently. Executable
checks denied writes outside their temporary root, and documentation edits
targeted only container/docs. An entirely unchanged outside tree cannot be
certified because of that observed concurrent change; it is not silently
attributed to this task or undone to manufacture a clean result.
