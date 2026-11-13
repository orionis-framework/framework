# Connecting synchronous and asynchronous code

`Loop` provides event-loop ownership, task scheduling, and callable dispatch. Import it directly; no Orionis application, provider, configuration file, or external service is required.

## Requirements

- Python 3.14 or newer, as declared by the project.
- A normal Orionis installation; there is no separate `aio` extra.
- Outside Windows, Orionis uses `uvloop` when importable. On Windows it selects `asyncio.ProactorEventLoop` when available. Otherwise it uses the standard asyncio factory.

## Choose the right operation

| Situation | Operation | Behavior |
|---|---|---|
| Script or CLI without a running loop | `Loop.run(main())` | Own a loop and return the coroutine's result. |
| Already inside an async function | `await main()` | Use the current loop and its resources. |
| Sync or async callable | `await Loop.execute(callback, ...)` | Offload synchronous execution and await asynchronous results. |
| Concurrent work on the current loop | `task = Loop.createTask(work())` | Schedule immediately; await `task` for its result. |
| Synchronous API without a running loop | `Loop.runSync(work())` | Use the same ownership and validation as `run`. |
| Synchronous block requiring a managed loop | `with Loop.eventLoopContext() as loop:` | Borrow an existing loop or own a new one. |

`run` and `runSync` reject a call from a thread already running an event loop. They do not move that coroutine to a private worker. A rejected coroutine remains the caller's responsibility: await it or close it.

## Start a script and offload blocking work

```python
from orionis.aio import Loop


def blocking_label(value: int) -> str:
    return f"job-{value}"


async def main() -> str:
    label = await Loop.execute(blocking_label, 7)
    return label.upper()


print(Loop.run(main()))  # JOB-7
```

`run` creates and registers an owned loop before starting the coroutine. On exit, `asyncio.Runner` cancels and drains pending tasks, finalizes asynchronous generators, shuts down the default executor, and closes that loop. A previously registered open loop is restored; a closed previous loop is not registered again. Coroutine failures and `KeyboardInterrupt` propagate to the caller.

`execute` accepts a callable, rather than an already-created coroutine object. It awaits coroutine functions on the calling loop. Other callables run on that loop's default executor with a copy of the caller's `contextvars` context. Changes made to context variables inside the worker do not change the caller's context. A synchronous callable's awaitable result, including a generator-based coroutine, is then awaited on the calling loop. Ordinary generators remain ordinary returned values.

Keyword arguments are forwarded unchanged:

```python
from orionis.aio import Loop


def sync_join(*, left: str, right: str) -> str:
    return f"{left}:{right}"


async def async_join(*, left: str, right: str) -> str:
    return f"{left}/{right}"


async def main() -> tuple[str, str]:
    first = await Loop.execute(sync_join, left="a", right="b")
    second = await Loop.execute(async_join, left="a", right="b")
    return first, second


print(Loop.run(main()))  # ('a:b', 'a/b')
```

Cancelling the awaiting task cannot forcibly stop a synchronous callable already running in a worker. In particular, cancellation does not prove that an SMTP send or file operation did not complete. Awaitable results belong on the calling loop; do not return pending futures bound to a different loop.

Queued work checks cancellation before invoking its callable. After an already-running callable finishes, an abandoned coroutine result is closed and cancellation of an abandoned future is requested on its owning loop when that loop remains open. A failed future's exception is still observed if it completes before cancellation. A late worker or cleanup exception is captured by the active Orionis failure runtime, or delivered to the loop's exception handler when no runtime is active.

## Schedule and observe a task

`createTask` is synchronous. Retain the returned task and await it to receive its result or exception:

```python
from orionis.aio import Loop


async def fetch_total() -> int:
    return 42


async def main() -> tuple[str, int]:
    task = Loop.createTask(fetch_total(), name="fetch-total")
    return task.get_name(), await task


print(Loop.run(main()))  # ('fetch-total', 42)
```

The task captures the creation-time context and is scheduled without waiting for a separate `await` on the factory. When an Orionis failure runtime is active, scheduling delegates to that runtime's task supervision. Otherwise it delegates to `asyncio.create_task`. Creating a task does not provide persistence or retries.

## Own or borrow a loop

The asyncio registration for the calling thread is the source of truth. `getEventLoop()` returns a running loop first, then an open registered loop, or creates and registers one. If it creates the loop, the caller owns it and must close it.

`eventLoopContext()` has two distinct lifecycles:

- With an open registered or running loop, it borrows that loop. It neither cancels the loop's tasks nor closes it, including when the block raises.
- Without an open registered loop, it creates one and uses Runner cleanup on exit. Nested contexts borrow the outer loop and leave cleanup to the owner.

For automatic cleanup, enter the context directly before acquiring a loop:

```python
from orionis.aio import Loop


async def calculate() -> int:
    return 42


with Loop.eventLoopContext() as loop:
    result = loop.run_until_complete(calculate())

print(result, loop.is_closed())  # 42 True
```

This example belongs in a synchronous thread with no registered loop. If you call `getEventLoop()` first, a later context borrows that loop and does not take ownership. Do not close an owned loop manually or leave it running when its context exits; either condition raises `RuntimeError` rather than silently skipping cleanup.

## Adapt a coroutine to a synchronous API

```python
from orionis.aio import Loop


async def lookup(code: str) -> str:
    return code.upper()


print(Loop.runSync(lookup("orionis")))  # ORIONIS
```

`runSync` is a direct synchronous entry point on the calling thread. Inside async code, use `await lookup(...)` instead. It has no shared executor, and independent synchronous callers do not serialize through a single worker. Resources tied to another event loop cannot be transferred merely by calling this bridge.

## Configuration and integration

Factory selection is cached at class level; uvloop detection uses a lock. There are no Orionis configuration keys or environment variables for this package, and no public factory override. Loop registration remains thread-specific through asyncio; Orionis does not maintain a second thread-local loop cache.

Direct consumers include the `reactor` entry point and console CLI (`run`), mail composition and transports (`execute`), and failure-runtime task supervision (`createTask`). Importing `orionis.aio` does not itself create a loop, executor, or application.

## API and errors

| Signature | Return value and constraints |
|---|---|
| `Loop.getEventLoop() -> asyncio.AbstractEventLoop` | Return an open loop; the caller owns only a loop newly created by this call. |
| `Loop.run(coro: Coroutine[Any, Any, T]) -> T` | Accept a native coroutine object; reject an active loop in this thread. |
| `await Loop.execute(func, /, *args, **kwargs) -> Any` | Accept a callable; preserve its result and exception semantics across dispatch. |
| `Loop.eventLoopContext()` | Yield a borrowed or owned loop using the lifecycle described above. |
| `Loop.isLoopRunning() -> bool` | Report whether this thread is currently running a loop; an idle registration is insufficient. |
| `Loop.createTask(coro, *, name=None) -> asyncio.Task[T]` | Require a running loop and return the scheduled task immediately. |
| `Loop.runSync(coro: Coroutine[Any, Any, T]) -> T` | Delegate to `run` without a private executor. |

`run` and `runSync` raise `TypeError("A coroutine object is required")` for coroutine functions, plain values, and general awaitables that are not native coroutine objects. They raise `RuntimeError` when called from a running loop. `execute` raises `TypeError("The provided object is not callable")` before dispatching a non-callable. Exceptions from executed code propagate; no error is converted to a successful return value.

Worker capacity and shutdown belong to the loop's default executor. Cached factory selection avoids repeated detection; it does not establish a throughput or latency guarantee. Cooperative tasks must yield for other work on the same loop to progress.

## Implementation reference

| Path | Responsibility |
|---|---|
| `__init__.py` | Expose `Loop` through the package's lazy exports. |
| `loop.py` | Select factories, manage ownership, dispatch callables, and schedule tasks. |

[Index](README.md) · [background](../../../background/docs/en/README.md) · [foundation](../../../foundation/docs/en/README.md)
