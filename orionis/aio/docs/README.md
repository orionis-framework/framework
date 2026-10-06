# orionis.aio

> `orionis.aio` provides Orionis's platform-aware event-loop lifecycle and safe bridges between synchronous and asynchronous callables.

## Overview

Use this module when code must start an asynchronous entry point, obtain a loop outside async code, run blocking work without occupying the current loop thread, create a named task, or call a coroutine from synchronous code. The public entry point is `Loop`, imported with `from orionis.aio import Loop`.

`Loop` is a class-level utility; it is not instantiated. It selects an event-loop factory once, keeps non-running loops in thread-local storage, and exposes explicit operations for the common boundaries between synchronous and asynchronous code. Orionis itself uses `Loop.execute` in mail composition and transports, and `Loop.runSync` in synchronous schema validation.

## Requirements

- Python 3.14 or newer, as declared by the project.
- A normal Orionis installation. There is no `aio`-specific installation extra.
- On non-Windows platforms, the project declares `uvloop>=0.22.1`; `Loop` uses it when importable. On Windows, `uvloop` is not required and Orionis tries `asyncio.ProactorEventLoop` instead.
- No application bootstrap, container binding, configuration file, or external service is required to use `Loop` directly.

## Quick start

Run an async application entry point and move a blocking callable to the loop's default executor:

```python
import time

from orionis.aio import Loop


def blocking_label(value: int) -> str:
    time.sleep(0.01)
    return f"job-{value}"


async def main() -> str:
    label = await Loop.execute(blocking_label, 7)
    return label.upper()


result = Loop.run(main())
print(result)  # JOB-7
```

`Loop.run` creates and owns the entry-point loop. `Loop.execute` invokes `blocking_label` in the default executor, then returns its result to `main`.

Validation: **Executed successfully** on CPython 3.14.6.

## Core concepts

### Entry-point loop versus the current loop

`Loop.run(coro)` is for a synchronous entry point where no event loop is running in the calling thread. Inside async code, use `await` normally. `Loop.getEventLoop()` returns the active loop when called inside async code; outside it, the method creates or reuses an open loop cached for the current thread.

### Callable bridge

`Loop.execute(func, *args, **kwargs)` accepts both kinds of callable. A coroutine function is called and awaited on the current loop. A synchronous callable is sent to that loop's default executor. If the synchronous callable returns an awaitable, the returned object is subsequently awaited on the current loop.

### Synchronous coroutine bridge

`Loop.runSync(coro)` deliberately blocks until the coroutine finishes. Without an active loop it delegates to `Loop.run`. With an active loop in the calling thread, it submits `Loop.run(coro)` to one shared, single-worker `ThreadPoolExecutor`, where the coroutine receives a separate loop.

### Loop ownership and cleanup

`Loop.eventLoopContext()` borrows the loop returned by `getEventLoop`; it does not close it. On exit, when that loop is not running, it cancels and drains all pending tasks for the loop. When called from an already running loop, cleanup is skipped so the context does not cancel the task driving its caller.

## Module structure

| Path | Responsibility |
|---|---|
| `__init__.py` | Re-exports `Loop` as the package's only supported top-level symbol. |
| `loop.py` | Implements factory selection, per-thread loop reuse, task cleanup, callable dispatch, and sync/async bridges. |

## Public API

### `Loop`

Recommended import:

```python
from orionis.aio import Loop
```

All public methods are static or class methods and operate on shared class state.

#### `getEventLoop()`

```text
Loop.getEventLoop() -> asyncio.AbstractEventLoop
```

Returns the loop currently running in the calling thread. If none is running, it reuses that thread's cached open loop or creates a new one, installs it with `asyncio.set_event_loop`, and caches it in thread-local storage. A closed cached loop is replaced. Loops are never shared between thread-local caches.

#### `run(coro)`

```text
Loop.run(coro: Coroutine[Any, Any, T]) -> T
```

Runs a native coroutine object to completion and returns its value. Factory selection is `uvloop.new_event_loop` when available outside Windows, then `asyncio.ProactorEventLoop` on Windows when exposed, then the standard `asyncio` factory. If an explicit factory is available, the implementation uses `asyncio.Runner`; otherwise it uses `asyncio.run`.

The method accepts a coroutine object, not a coroutine function or a general awaitable. It returns `0` after `KeyboardInterrupt`, propagates other coroutine exceptions, and rejects use from a thread that already has a running loop.

#### `execute(func, /, *args, **kwargs)`

```text
await Loop.execute(func, *args, **kwargs) -> Any
```

Invokes a coroutine function directly and awaits it. It offloads any other callable to the current loop's default executor using `run_in_executor(None, ...)`. Arguments and return values pass through unchanged; an awaitable returned by the offloaded callable is awaited before the result is returned. Original exceptions cross the await boundary unchanged.

This method must be called inside a running event loop. It does not use the private single-worker executor reserved for `runSync`.

#### `eventLoopContext()`

```python
with Loop.eventLoopContext() as loop:
    assert loop is Loop.getEventLoop()
```

Yields `getEventLoop()`'s result. On exit from a non-running loop, every pending task on that loop is cancelled and gathered with `return_exceptions=True`. Cleanup suppresses `RuntimeError` and `asyncio.CancelledError`, including the case where code inside the block closed the loop. The context leaves the loop open and reusable when it can do so.

#### `isLoopRunning()`

```text
Loop.isLoopRunning() -> bool
```

Reports whether an event loop is actively running in the calling thread. A cached but idle loop does not make this return `True`.

#### `createTask(coro, *, name=None)`

```text
await Loop.createTask(coro, name=None) -> asyncio.Task[T]
```

Creates the task on the current running loop and returns it without awaiting the task's completion. Although the method itself is async, callers must retain or await the returned task to observe completion and exceptions. The optional name is forwarded to `loop.create_task`.

#### `runSync(coro)`

```text
Loop.runSync(coro: Coroutine[Any, Any, T]) -> T
```

Synchronously waits for a coroutine and returns its result. In a thread without a running loop, this is a direct call to `run`. In a thread with a running loop, execution moves to the module's lazily created, shared single-worker executor. Exceptions raised by the coroutine are re-raised in the calling thread.

Because `runSync` blocks the calling thread, it should be reserved for genuinely synchronous APIs. Async callers that control their call chain should use `await` instead.

## Common workflows

### Start a CLI or script

Define one top-level coroutine, create the coroutine object, and pass it to `Loop.run`. Do not call `Loop.run` from an async handler; that would attempt to nest event loops in one thread.

### Call blocking code from async code

Pass the synchronous function and its arguments to `await Loop.execute(...)`. The loop remains available to run other tasks while the default executor performs the blocking call. Coroutine functions can use the same entry point and are awaited directly.

### Schedule concurrent work

Inside a running loop, call `await Loop.createTask(coro, name=...)` for each coroutine. Save the returned tasks and later await them individually or with `asyncio.gather`.

### Adapt an async operation to a synchronous contract

Use `Loop.runSync(coro)` only at a synchronous boundary that cannot become async. If the caller is already on an event-loop thread, the bridge uses its dedicated worker so it does not try to run a second loop in that same thread. The call still blocks the caller until completion.

## Examples

### Dispatch sync and async callables through one interface

The same operation handles both callable styles while preserving keyword arguments:

```python
from orionis.aio import Loop


def sync_join(*, left: str, right: str) -> str:
    return f"{left}:{right}"


async def async_join(*, left: str, right: str) -> str:
    return f"{left}/{right}"


async def main() -> tuple[str, str]:
    sync_value = await Loop.execute(sync_join, left="a", right="b")
    async_value = await Loop.execute(async_join, left="a", right="b")
    return sync_value, async_value


print(Loop.run(main()))  # ('a:b', 'a/b')
```

The synchronous function runs in the loop's default executor; the coroutine function stays on the caller's loop.

Validation: **Executed successfully** on CPython 3.14.6.

### Create and identify a task

Task names are useful in diagnostics, while the task object retains the result:

```python
import asyncio

from orionis.aio import Loop


async def fetch_total() -> int:
    await asyncio.sleep(0)
    return 42


async def main() -> tuple[str, int]:
    task = await Loop.createTask(fetch_total(), name="fetch-total")
    return task.get_name(), await task


print(Loop.run(main()))  # ('fetch-total', 42)
```

`createTask` schedules immediately; awaiting the returned task is what retrieves its result.

Validation: **Executed successfully** on CPython 3.14.6.

### Bridge an async operation into synchronous code

This example exercises the worker-thread path because `runSync` is called while `main`'s loop is active:

```python
from orionis.aio import Loop


async def lookup(code: str) -> str:
    return code.upper()


async def main() -> str:
    return Loop.runSync(lookup("orionis"))


print(Loop.run(main()))  # ORIONIS
```

The result returns synchronously to `main`. During that call, the thread running `main` is blocked, so direct `await lookup(...)` is preferable when the surrounding API can be async.

Validation: **Executed successfully** on CPython 3.14.6.

### Handle invalid entry-point usage

Pass the coroutine object returned by calling an async function, not the function itself:

```python
from orionis.aio import Loop


async def main() -> int:
    return 1


try:
    Loop.run(main)  # type: ignore[arg-type]
except TypeError as error:
    print(str(error))  # A coroutine object is required
```

Validation occurs before a loop is created.

Validation: **Executed successfully** on CPython 3.14.6.

## Configuration

This module consumes no Orionis configuration keys or environment variables. Factory selection follows the current platform and whether `uvloop` can be imported; there is no public setting to override that selection. The resolved factory is cached for the life of the process.

## Integration with Orionis

- `orionis.mail` uses `Loop.execute` to keep synchronous rendering, file storage, and SMTP work off the active event-loop thread.
- `orionis.schemas.rules.unique` uses `Loop.runSync` because its public validation hook is synchronous while its existence check uses asynchronous database operations.
- The repository's `reactor` executable starts `app.handleCommand(sys.argv)` with `Loop.run`.
- `Loop` has no provider and is not resolved through the service container; importing it is sufficient.

These are direct consumers, not bootstrap side effects. Importing `orionis.aio` does not create a loop, executor, or application.

## Errors and edge cases

- `run` raises `TypeError("A coroutine object is required")` for a coroutine function, plain value, or other object that is not a native coroutine object.
- `run` raises `RuntimeError` when the calling thread already has a running loop. The supplied coroutine remains unconsumed and is still owned by the caller.
- `execute` raises `TypeError("The provided object is not callable")` before scheduling a non-callable. Without a running loop, its call to `asyncio.get_running_loop()` raises `RuntimeError`.
- Exceptions from invoked callables and coroutines propagate; the module does not wrap them.
- `run` converts `KeyboardInterrupt` raised during coroutine execution into the integer `0`.
- `eventLoopContext` may cancel any pending task associated with its idle loop, not only tasks created inside the context. It intentionally does not close that loop.
- A closed thread-local loop is discarded and replaced on the next `getEventLoop` call.

## Performance and concurrency

Loop-factory resolution and `uvloop` detection are process-wide caches guarded by a `threading.Lock` during first use. Repeated resolution uses an unlocked fast path.

Idle loops are cached in `threading.local`, so each thread receives its own loop and repeated calls in that thread reuse it until closed. A currently running loop always takes precedence over the cached value.

`execute` uses the current loop's default executor for synchronous work; its capacity and lifecycle therefore belong to that event loop. `runSync` uses a separate process-wide `ThreadPoolExecutor(max_workers=1)` created lazily under a lock. Consequently, concurrent `runSync` calls that require the worker are serialized. The executor is retained rather than shut down after each call.

`runSync` avoids nested-loop errors by running the coroutine in another thread, but it is a blocking call and can pause the caller's event-loop thread. `createTask` only schedules work; concurrency depends on the coroutine yielding control.

## Compatibility

The package declares Python 3.14+ and uses Python 3.14 generic function syntax. Validation for this document used CPython 3.14.6 on Windows.

On Windows, factory resolution skips `uvloop` and attempts `asyncio.ProactorEventLoop`; if that attribute is unavailable it falls back to `asyncio.new_event_loop` or `asyncio.run` as appropriate. Outside Windows, importable `uvloop` is preferred; if the import fails, standard `asyncio` is used. No module code imposes an external-service requirement.

## Verification notes

The implementation in `orionis/aio/loop.py`, package exports, direct framework consumers, `pyproject.toml`, and `tests/aio` were inspected. All 48 module tests passed through the Orionis test runner on CPython 3.14.6. All five Quick start/Examples programs were executed successfully in the project virtual environment. The examples require no external services.
