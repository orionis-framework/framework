# `orionis.aio`

> Thread-safe, platform-aware `asyncio` event loop manager exposed through a single fully static class.

🇪🇸 Versión en español: [README.es.md](README.es.md)

## Table of contents

- [Functional description](#functional-description)
  - [Where it fits in the framework](#where-it-fits-in-the-framework)
  - [Module map](#module-map)
  - [Loop factory resolution](#loop-factory-resolution)
  - [Design decisions](#design-decisions)
- [API reference](#api-reference)
  - [`Loop`](#loop)
  - [Class state](#class-state)
  - [`Loop.getEventLoop()`](#loopgeteventloop)
  - [`Loop.run()`](#looprun)
  - [`Loop.runSync()`](#looprunsync)
  - [`Loop.execute()`](#loopexecute)
  - [`Loop.createTask()`](#loopcreatetask)
  - [`Loop.eventLoopContext()`](#loopeventloopcontext)
  - [`Loop.isLoopRunning()`](#loopislooprunning)
  - [Internal helpers](#internal-helpers)
- [Usage examples](#usage-examples)
  - [1. Application entry point](#1-application-entry-point)
  - [2. Calling async code from synchronous code](#2-calling-async-code-from-synchronous-code)
  - [3. Running a blocking function from a coroutine](#3-running-a-blocking-function-from-a-coroutine)
  - [4. Scheduling a background task](#4-scheduling-a-background-task)
  - [5. Managing a loop lifecycle with cleanup](#5-managing-a-loop-lifecycle-with-cleanup)
  - [6. Rejected arguments](#6-rejected-arguments)
- [Performance and concurrency considerations](#performance-and-concurrency-considerations)
- [Compatibility notes](#compatibility-notes)

## Functional description

`orionis.aio` owns the event loop lifecycle for the framework: it picks the
fastest loop implementation available on the current platform, caches one loop
per thread, bridges synchronous and asynchronous code in both directions, and
cancels pending tasks when a managed context exits. Everything is exposed
through one class, `Loop`, whose members are all `@staticmethod` or
`@classmethod`.

### Where it fits in the framework

`orionis/aio/loop.py` imports only the standard library (`asyncio`,
`concurrent.futures`, `functools`, `inspect`, `sys`, `threading`, `types`,
`contextlib`, `typing`); it has **no dependency on any other Orionis module**,
which makes it importable from anywhere without circular-import risk.

Direct consumers inside the framework:

| Consumer | Member used | Purpose |
| --- | --- | --- |
| `reactor` (CLI entry point at the repository root) | `Loop.run(...)` | Runs `app.handleCommand(sys.argv)` and feeds its result to `sys.exit`. |
| `orionis/schemas/rules/unique.py` | `Loop.runSync(...)` | Bridges the synchronous validation-rule pipeline to the async ORM. |

The module is **not** registered in the container and has **no facade and no
service provider**: it is imported and used directly.

### Module map

| File | Contents |
| --- | --- |
| `orionis/aio/__init__.py` | Re-exports `Loop`; `__all__ == ["Loop"]`. |
| `orionis/aio/loop.py` | The `Loop` class: class-level state, four internal helpers and seven public members. |

### Loop factory resolution

`_getLoopFactory()` resolves the loop factory **once per process** and caches
the result:

1. `uvloop.new_event_loop` — only when `_IS_WIN32` is `False` and `import
   uvloop` succeeds.
2. `asyncio.ProactorEventLoop` — only when `_IS_WIN32` is `True`; guarded by
   `contextlib.suppress(AttributeError)` so a runtime that does not expose it
   falls through.
3. `None` — meaning "let asyncio decide"; callers then use
   `asyncio.new_event_loop()`.

Observed on this repository's platform (`sys.platform == "win32"`,
CPython 3.14):

```text
Loop._IS_WIN32:      True
Loop._detectUvloop(): None
Loop._getLoopFactory(): <class 'asyncio.windows_events.ProactorEventLoop'>
Loop.getEventLoop():  ProactorEventLoop instance
```

### Design decisions

The following notes describe decisions already present in the code; they are
informational, not recommendations.

- **Class-as-namespace, no instances.** Every attribute is a `ClassVar` and
  every member is a `@staticmethod`/`@classmethod`, so the class itself is the
  shared manager. `Loop` declares no `__init__` and no `__slots__`, so
  `Loop()` does succeed and produces an object with a `__dict__` — such an
  instance simply adds nothing over the class.
- **One loop per thread.** `_loop_local` is a `threading.local()`, so a loop
  created in one thread is never handed to another.
- **Double-checked locking twice.** `_detectUvloop()` (module import) and
  `_getSyncExecutor()` (thread-pool creation) read a guard outside the lock and
  re-read it inside, so the expensive operation runs at most once even when
  several threads race on the first call.
- **Single-worker bridging pool.** `runSync()` uses a
  `ThreadPoolExecutor(max_workers=1, thread_name_prefix="orionis-sync")` to run
  a coroutine on its own loop when the caller already sits inside one.
- **Public API over private internals.** `_getRunningLoop()` wraps
  `asyncio.get_running_loop()` in `try/except RuntimeError` instead of reading
  CPython internals.
- **Cleanup never raises.** `eventLoopContext()` gathers cancelled tasks with
  `return_exceptions=True` inside `contextlib.suppress(RuntimeError,
  asyncio.CancelledError)`, so the `finally` block cannot mask the exception
  that left the `with` body.

## API reference

### `Loop`

```python
class Loop:
    ...
```

Import it from either the package or the implementation module:

```python
from orionis.aio import Loop
from orionis.aio.loop import Loop
```

All members are called on the class (`Loop.run(...)`). The class stores every
piece of state at class level, so that state is shared by the whole process.

### Class state

Declared literally as:

```python
_IS_WIN32: ClassVar[bool] = sys.platform == "win32"
_loop_local: ClassVar[threading.local] = threading.local()
_uvloop_factory: ClassVar[Callable[[], asyncio.AbstractEventLoop] | None] = None
_uvloop_checked: ClassVar[bool] = False
_loop_lock: ClassVar[threading.Lock] = threading.Lock()
_loop_factory_resolved: ClassVar[bool] = False
_loop_factory_cached: ClassVar[
    Callable[[], asyncio.AbstractEventLoop] | None
] = None
_sync_executor: ClassVar[concurrent.futures.ThreadPoolExecutor | None] = None
_sync_executor_lock: ClassVar[threading.Lock] = threading.Lock()
```

| Attribute | Scope | Written by |
| --- | --- | --- |
| `_IS_WIN32` | Process | Evaluated once at class definition. |
| `_loop_local` | Thread | `getEventLoop()` stores the created loop as `_loop_local.loop`. |
| `_uvloop_factory`, `_uvloop_checked` | Process | `_detectUvloop()`. |
| `_loop_factory_cached`, `_loop_factory_resolved` | Process | `_getLoopFactory()`. |
| `_sync_executor` | Process | `_getSyncExecutor()`. |
| `_loop_lock`, `_sync_executor_lock` | Process | Never reassigned; guard the two detection paths. |

Neither the cached per-thread loops nor `_sync_executor` are ever closed or
shut down by this module.

### `Loop.getEventLoop()`

```python
@classmethod
def getEventLoop(cls) -> asyncio.AbstractEventLoop
```

Returns the event loop for the calling thread, creating one when needed.

Resolution order:

1. The loop currently running in this thread, when there is one.
2. `_loop_local.loop`, when it exists and `is_closed()` is `False`.
3. A new loop built with the resolved factory, or with
   `asyncio.new_event_loop()` when the factory is `None`.

**Parameters:** none.

**Returns:** `asyncio.AbstractEventLoop`.

**Raises:** nothing of its own.

**Side effects:** on branch 3 it calls `asyncio.set_event_loop(loop)` and
stores the loop in `_loop_local`. The loop is never closed by the module.

### `Loop.run()`

```python
@staticmethod
def run[T](coro: Coroutine[Any, Any, T]) -> T
```

Runs a coroutine as the application entry point, from a thread with **no**
running loop. Uses `asyncio.Runner(loop_factory=...)` when a factory is
resolved, otherwise `asyncio.run(coro)`.

| Parameter | Type | Description |
| --- | --- | --- |
| `coro` | `Coroutine[Any, Any, T]` | Coroutine object to execute. |

**Returns:** the value produced by `coro`. If the coroutine raises
`KeyboardInterrupt`, the exception is swallowed and the literal `0` (an `int`)
is returned instead, regardless of `T`.

**Raises:**

- `TypeError("A coroutine object is required")` when
  `isinstance(coro, types.CoroutineType)` is `False` — a coroutine *function*
  is rejected too.
- `RuntimeError` propagated from asyncio when a loop is already running in the
  calling thread; `coro` is then left unconsumed. Use `Loop.runSync()` to
  bridge into a running loop. The message belongs to the standard library and
  differs between the `asyncio.Runner` and `asyncio.run` branches — observed on
  CPython 3.14 / Windows: `Cannot run the event loop while another loop is
  running`.
- Any other exception raised inside the coroutine propagates unchanged.

**Side effects:** creates and closes a loop dedicated to this call; it does not
use nor populate the per-thread cache.

### `Loop.runSync()`

```python
@classmethod
def runSync[T](cls, coro: Coroutine[Any, Any, T]) -> T
```

Runs a coroutine to completion synchronously from any context.

- No loop running in the calling thread → delegates to `Loop.run(coro)`.
- A loop is running → submits `Loop.run` to the shared single-worker executor
  and blocks on `.result()`, so the coroutine gets its own loop in another
  thread instead of deadlocking the caller.

| Parameter | Type | Description |
| --- | --- | --- |
| `coro` | `Coroutine[Any, Any, T]` | Coroutine object to execute. |

**Returns:** the value produced by `coro` (or `0` when the coroutine raises
`KeyboardInterrupt`, inherited from `Loop.run`).

**Raises:** whatever `coro` raises, re-raised in the calling thread by
`concurrent.futures.Future.result()`; plus the same `TypeError` as
`Loop.run()` for an invalid argument.

**Side effects:** blocks the calling thread until the coroutine finishes and
may create the process-wide bridging executor on first use.

### `Loop.execute()`

```python
@staticmethod
async def execute(
    func: Callable[..., Any],
    /,
    *args: Any,
    **kwargs: Any,
) -> Any
```

Invokes a callable that may be synchronous or asynchronous, from inside a
coroutine, without the caller having to branch on its nature.

- `inspect.iscoroutinefunction(func)` → awaited directly on the running loop.
- Otherwise → wrapped in `functools.partial(func, *args, **kwargs)` and sent to
  the running loop's **default** executor via `loop.run_in_executor(None, ...)`.
- If the synchronous call returns an object with `__await__`, that object is
  awaited before returning.

| Parameter | Type | Description |
| --- | --- | --- |
| `func` | `Callable[..., Any]` | Callable to invoke; positional-only. |
| `*args` | `Any` | Positional arguments forwarded to `func`. |
| `**kwargs` | `Any` | Keyword arguments forwarded to `func`. |

**Returns:** the result of `func`, or the result of awaiting it when it is
awaitable.

**Raises:** `TypeError("The provided object is not callable")` when `func` is
not callable; the errors raised by `func` propagate unchanged. It calls
`asyncio.get_running_loop()` for the synchronous branch, so it must be awaited
from a running loop.

### `Loop.createTask()`

```python
@staticmethod
async def createTask[T](
    coro: Coroutine[Any, Any, T],
    *,
    name: str | None = None,
) -> asyncio.Task[T]
```

Schedules `coro` on the running loop through
`asyncio.get_running_loop().create_task(coro, name=name)`.

| Parameter | Type | Description |
| --- | --- | --- |
| `coro` | `Coroutine[Any, Any, T]` | Coroutine to schedule. |
| `name` | `str \| None` | Optional task name; keyword-only, defaults to `None`. |

**Returns:** `asyncio.Task[T]`.

**Raises:** the `RuntimeError` raised by `asyncio.get_running_loop()` when no
loop is running.

Note that the member is itself a coroutine function: the task is obtained with
`task = await Loop.createTask(...)`, and awaited a second time to collect its
result.

### `Loop.eventLoopContext()`

```python
@staticmethod
@contextmanager
def eventLoopContext() -> Generator[asyncio.AbstractEventLoop]
```

Context manager that yields `Loop.getEventLoop()` and performs cooperative
cleanup on exit.

Cleanup runs only when, at exit time, the loop is **not** running *and*
`asyncio.all_tasks(loop)` is non-empty. In that case every pending task is
cancelled and then awaited with `asyncio.gather(*pending,
return_exceptions=True)` through `loop.run_until_complete(...)`.

**Parameters:** none.

**Yields:** `asyncio.AbstractEventLoop`.

**Raises:** nothing — `RuntimeError` and `asyncio.CancelledError` raised while
cleaning up are suppressed by design.

**Side effects:** cancels the pending tasks of the yielded loop. The loop
itself is **not** closed, so it stays cached for the thread.

### `Loop.isLoopRunning()`

```python
@staticmethod
def isLoopRunning() -> bool
```

Reports whether an event loop is running in the calling thread.

**Parameters:** none.

**Returns:** `bool` — `True` when `_getRunningLoop()` is not `None`.

**Raises:** nothing.

### Internal helpers

Documented because they define the caching guarantees of the public members;
they are not part of the supported surface.

```python
@staticmethod
def _getRunningLoop() -> asyncio.AbstractEventLoop | None

@classmethod
def _detectUvloop(cls) -> Callable[[], asyncio.AbstractEventLoop] | None

@classmethod
def _getLoopFactory(cls) -> Callable[[], asyncio.AbstractEventLoop] | None

@classmethod
def _getSyncExecutor(cls) -> concurrent.futures.ThreadPoolExecutor
```

- `_getRunningLoop()` — `asyncio.get_running_loop()` wrapped in
  `try/except RuntimeError`, returning `None` instead of raising.
- `_detectUvloop()` — imports `uvloop` at most once per process, only outside
  Windows; `ImportError` is swallowed and the result cached in
  `_uvloop_factory`.
- `_getLoopFactory()` — applies the resolution order described above and caches
  the answer in `_loop_factory_cached`.
- `_getSyncExecutor()` — creates the single-worker bridging pool on first use
  and returns the same instance afterwards.

## Usage examples

Every snippet below is a complete script that can be executed as is with
`python <file>.py`.

### 1. Application entry point

```python
import asyncio
from orionis.aio import Loop


async def main() -> int:
    print("Application started")
    await asyncio.sleep(0.1)
    return 0


exit_code = Loop.run(main())
print("exit code:", exit_code)
```

Output:

```text
Application started
exit code: 0
```

This is the pattern used by the `reactor` CLI, which passes the returned value
straight to `sys.exit(...)`.

### 2. Calling async code from synchronous code

```python
from orionis.aio import Loop


async def fetch_greeting() -> str:
    return "Hello from an async task"


def sync_entrypoint() -> str:
    # Same call works with or without a loop already running in this thread.
    return Loop.runSync(fetch_greeting())


async def async_entrypoint() -> str:
    return Loop.runSync(fetch_greeting())


print("no loop running:", sync_entrypoint())
print("loop running:", Loop.run(async_entrypoint()))
```

Output:

```text
no loop running: Hello from an async task
loop running: Hello from an async task
```

### 3. Running a blocking function from a coroutine

```python
import time
from orionis.aio import Loop


def slow_blocking_call(seconds: float) -> str:
    time.sleep(seconds)
    return "blocking call finished"


async def handler() -> None:
    print(await Loop.execute(slow_blocking_call, 0.2))
    print(await Loop.execute(slow_blocking_call, seconds=0.1))


Loop.run(handler())
```

Output:

```text
blocking call finished
blocking call finished
```

### 4. Scheduling a background task

```python
import asyncio
from orionis.aio import Loop


async def background_job() -> str:
    await asyncio.sleep(0.05)
    return "background job finished"


async def controller() -> None:
    print("loop running:", Loop.isLoopRunning())
    task = await Loop.createTask(background_job(), name="warmup")
    print("task name:", task.get_name())
    print("task result:", await task)


Loop.run(controller())
```

Output:

```text
loop running: True
task name: warmup
task result: background job finished
```

### 5. Managing a loop lifecycle with cleanup

```python
import asyncio
from orionis.aio import Loop


async def pending_forever() -> None:
    await asyncio.sleep(3600)


def run_batch() -> None:
    with Loop.eventLoopContext() as loop:
        leftover = loop.create_task(pending_forever())
        loop.run_until_complete(asyncio.sleep(0))
    print("leftover cancelled:", leftover.cancelled())
    print("loop closed:", loop.is_closed())


run_batch()
```

Output:

```text
leftover cancelled: True
loop closed: False
```

### 6. Rejected arguments

```python
from orionis.aio import Loop


async def noop() -> None:
    return None


try:
    Loop.run(noop)
except TypeError as error:
    print("run:", error)


async def guard() -> None:
    try:
        await Loop.execute(42)
    except TypeError as error:
        print("execute:", error)


Loop.run(guard())
```

Output:

```text
run: A coroutine object is required
execute: The provided object is not callable
```

## Performance and concurrency considerations

- **Platform detection happens once.** `_detectUvloop()` and
  `_getLoopFactory()` cache their result in class attributes, so repeated calls
  to `getEventLoop()`, `run()` or `runSync()` never repeat the import or the
  platform check.
- **Fast path when a loop is already running.** `getEventLoop()` and
  `isLoopRunning()` resolve through a single `asyncio.get_running_loop()` call
  inside `try/except`, which is the common case inside request handlers.
- **Thread isolation.** The loop cache lives in a `threading.local()`, so two
  threads calling `getEventLoop()` receive two different loops; no lock is
  taken on that path.
- **`runSync()` blocks and serialises.** It blocks the calling thread until the
  coroutine finishes, and the bridging pool has exactly **one** worker, so
  concurrent `runSync()` calls made from inside a running loop queue up behind
  each other instead of running in parallel.
- **`execute()` uses asyncio's default executor**, not the single-worker
  bridging pool, so its parallelism is whatever the running loop's default
  executor provides.
- **Cleanup is conditional.** `eventLoopContext()` cancels tasks only when the
  loop is idle at exit; when the loop is still running, the block exits without
  touching any task.
- **`run()` builds a fresh loop per call.** It never reuses the thread-local
  loop, so it is meant for entry points and not for hot paths.
- **Nothing is ever torn down.** Neither the per-thread loops nor the bridging
  executor are closed by this module; they live until the process ends.

## Compatibility notes

- **Python:** `>= 3.14`, as declared in `pyproject.toml`. The module relies on
  PEP 695 generic syntax (`def run[T](...)`, `def createTask[T](...)`,
  `def runSync[T](...)`), which is a syntax error on older interpreters.
- **Dependencies:** standard library only. `uvloop>=0.22.1` is a base
  dependency of the framework restricted to `sys_platform != 'win32'`, so
  nothing extra needs to be installed; when it is importable it is picked up
  automatically and, when it is not, `ImportError` is swallowed.
- **Platform behaviour differs by design:** Windows resolves to
  `asyncio.ProactorEventLoop`, other platforms to `uvloop` when available and
  to the asyncio default otherwise.
- **Type annotations:** the module uses `from __future__ import annotations`,
  so its annotations are strings at runtime; the class is never built by the
  dependency-injection container, which resolves constructor annotations
  eagerly.
- **Public surface:** `orionis/aio/__init__.py` exports exactly `Loop`
  (`__all__ == ["Loop"]`).
