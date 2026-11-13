# Scopes, isolation, and concurrency

A `scoped` service belongs to a unit of work enclosed by `async with`. Use it for request or command state. A singleton retaining a reference to that state extends its lifetime beyond the scope and breaks isolation: inject request services into consumers that themselves live inside that scope.

## Errors and edge cases

- Duplicate contract/alias registration raises `ValueError` unless `override=True`.
- Incorrect contract/concrete or contract/instance relationships raise `TypeError`.
- Scoped resolution without a scope, use of a closed scope, or repeated scope entry raises `RuntimeError`.
- Circular constructor graphs raise `CircularDependencyException`; the resolution stack is task-local and distinguishes container instances. Building the same class in an independent container does not create a false cycle.
- Missing annotations without defaults cannot be auto-resolved; explicit arguments can satisfy them.
- A class may be auto-built without registration, but a missing string alias cannot.
- A facade before application boot raises `RuntimeError`. A scoped facade outside its owning scope also raises `RuntimeError`.
- Registration dictionaries are mutable setup state; do not change global bindings concurrently during normal request handling.

## Performance and concurrency

Container construction is singleton-per-subclass. Publication and initialization are protected by double-checked thread locks, so concurrent constructors cannot reset an initialized instance's bindings. Reflection/invocation plans are cached. Singleton, scoped, and deferred-provider first construction uses per-key `asyncio.Lock` instances so concurrent tasks on one loop share one result.

Creation locks are replaced when the same container is used from a different event loop; serialization is therefore per loop, not a cross-loop global guarantee. Registration itself is not locked. `ContextVar` scope and resolution stacks isolate asyncio task contexts, while child tasks inherit the active scope reference.

Pinned facades remove repeated container resolution for singleton services. Scoped facades intentionally avoid that optimization to preserve lifetime isolation.

Unpinned facade dispatchers use a shared LRU cache of at most 1024 class/attribute pairs. Repeated access preserves dispatcher identity while the pair remains cached; eviction releases the cached reference. Missing Python special methods raise `AttributeError` instead of creating a service dispatcher.

`scope.get()` shares a stored coroutine as a task and caches its result. Completion does not overwrite a value replaced with `set()` or restore an entry removed by `clear()`; an already waiting caller still receives its original task's result. Completion after scope exit raises `RuntimeError`. Cancellation of a waiter propagates to the shared task.

## Configuration

The container consumes no application configuration or environment variables. Bindings are established by core/application providers and runtime registration. Provider lists and deferred-provider metadata belong to application bootstrap rather than a `container` config section.

## Examples

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
        print(first is third)  # False


asyncio.run(main())
```

## Close resources and tasks

Leaving a scope clears its references and invalidates the context. It does not automatically call `close()` or `aclose()` on arbitrary services, or await arbitrary tasks you created. The resource owner must close it with its context manager or a `finally` block. If a child task needs a scoped service, await its completion inside the scope; do not leave it running after scope exit. There is also no dependency-capture mechanism preventing a singleton from retaining a scoped object: control that relationship in your service design.

A native coroutine stored before it starts is owned by the scope until requested. Replacing that value, clearing the scope, or exiting closes such an unstarted coroutine. Assigning the same object again preserves it. This cleanup does not cancel borrowed tasks or close coroutines already running or suspended elsewhere.

## Evidence and next steps

[manager.py](../../context/manager.py) · [scope.py](../../context/scope.py) · [container.py](../../container.py)

[Return to the module index](README.md).
