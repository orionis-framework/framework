# orionis.aio

> Select event loops, run native coroutines, offload callables, and schedule tasks.

Spanish version: [README.es.md](README.es.md). Agent entry point:
[SKILL.md](SKILL.md).

## Table of contents

- [Functional overview](#functional-overview)
- [Module structure](#module-structure)
- [API reference](#api-reference)
- [Loop](#loop)
- [Loop.getEventLoop()](#loopgeteventloop)
- [Loop.run()](#looprun)
- [Loop.runSync()](#looprunsync)
- [Loop.execute()](#loopexecute)
- [Loop.createTask()](#loopcreatetask)
- [Loop.eventLoopContext()](#loopeventloopcontext)
- [Loop.isLoopRunning()](#loopislooprunning)
- [Usage examples](#usage-examples)
- [1. Run an entry-point coroutine](#1-run-an-entry-point-coroutine)
- [2. Bridge from synchronous code](#2-bridge-from-synchronous-code)
- [3. Execute both kinds of callable](#3-execute-both-kinds-of-callable)
- [4. Schedule and join named tasks](#4-schedule-and-join-named-tasks)
- [5. Clean up a stopped loop](#5-clean-up-a-stopped-loop)
- [6. Handle rejected inputs and nested execution](#6-handle-rejected-inputs-and-nested-execution)
- [7. Integrate with FreezeThaw](#7-integrate-with-freezethaw)
- [8. Process temporary JSON files concurrently](#8-process-temporary-json-files-concurrently)
- [Design characteristics](#design-characteristics)
- [Performance and concurrency](#performance-and-concurrency)
- [Compatibility notes](#compatibility-notes)
- [Verification and limitations](#verification-and-limitations)

## Functional overview

`orionis.aio` exposes `Loop` to select or obtain an event loop, run a native
coroutine synchronously, dispatch callables asynchronously, and create tasks.
Its context manager conditionally cancels pending tasks on a stopped loop.
The implementation uses the standard library and lazily detects `uvloop`;
no additional setup beyond the framework installation is required.

Verified direct consumers, not an exhaustive catalog:

| Source and symbol | Relationship |
| --- | --- |
| [reactor](../../../reactor), `__main__` | Passes `app.handleCommand(sys.argv)` to `Loop.run()` and its result to `sys.exit()`. |
| [orionis/schemas/rules/unique.py](../../schemas/rules/unique.py), `Unique.enforce()` | Uses `Loop.runSync()` for synchronous uniqueness validation; its asynchronous path awaits the current connection instead. |
| [orionis/mail/composer.py](../../mail/composer.py), `MailComposer.prepare()` | Awaits `Loop.execute()` to compose MIME data with its synchronous `_compose()` helper. |

These callers import `Loop` directly. The assigned module contains no provider,
facade, contract class, or configuration file. The integration example uses
[orionis/support/structures/freezer.py](../../support/structures/freezer.py),
`FreezeThaw.freeze()` and `FreezeThaw.thaw()`, without booting an application.

## Module structure

Paths in link labels are relative to the repository root; link destinations
are relative to this document.

| Inspected file | Responsibility and public symbols |
| --- | --- |
| [orionis/aio/__init__.py](../__init__.py) | Re-exports the implementation's `Loop` by identity; `__all__ = ["Loop"]`. |
| [orionis/aio/loop.py](../loop.py) | Defines `Loop`, its seven public methods, four private helpers, and class-level caches and locks. |

Both Python files were inspected in full. There are no Python subpackages or
runtime resource files in this module. Its three documentation files are
reference material, not runtime inputs.

## API reference

The following declaration blocks are **literal reference fragments**, including
decorators and source comments. They omit bodies and are not executable scripts.
`cls` is supplied by the `@classmethod` descriptor, not by the caller. Exception
lists distinguish explicit checks from propagated failures and are not exhaustive
when a callable, task factory, event-loop factory, or executor is involved.

### Loop

Source: [orionis/aio/loop.py](../loop.py#L15), `Loop`. Package export:
[orionis/aio/__init__.py](../__init__.py).

```python
class Loop:
```

Use `from orionis.aio import Loop` or `from orionis.aio.loop import Loop`.
The class has no base class, explicit constructor, properties, overloads, or
custom special methods. All eleven declared methods are class or static methods;
only the seven without an underscore are consumer API.

`Loop()` uses the inherited `object` constructor and is permitted. An instance
has a `__dict__` because no `__slots__` is declared, but construction does not
create a loop or a pool and the methods keep using class-level state. Call the
methods on `Loop`; there is no public cache reset, loop-close, or pool-shutdown
method. Private helpers and imported standard-library names are not additional
public APIs; their relevant mechanisms are covered under design and concurrency.

### Loop.getEventLoop()

Source: [orionis/aio/loop.py](../loop.py#L186), `Loop.getEventLoop`.

```python
@classmethod
def getEventLoop(cls) -> asyncio.AbstractEventLoop:
```

**Parameters:** no caller-supplied parameters. **Result:** the running loop in
the calling thread, otherwise an open loop retained in that thread's cache,
otherwise a newly created `asyncio.AbstractEventLoop`.

The creation branch selects the cached factory, falling back to
`asyncio.new_event_loop()`, calls `asyncio.set_event_loop(loop)`, and stores
`_loop_local.loop`. A closed cached loop is replaced. A running loop is returned
without being written to this cache. An unrelated loop registered externally
with `asyncio.set_event_loop()` is not consulted by the cache branch.

There is no explicit `raise` or broad exception translation: factory/import
failures and asyncio registration errors can propagate. Merely obtaining the
loop does not start or close it. The owner must arrange any required shutdown;
example 5 closes the borrowed stopped loop explicitly.

### Loop.run()

Source: [orionis/aio/loop.py](../loop.py#L213), `Loop.run`.

```python
@staticmethod
def run[T](coro: Coroutine[Any, Any, T]) -> T:
```

| Parameter | Declared annotation | Accepted value |
| --- | --- | --- |
| `coro` | `Coroutine[Any, Any, T]` | A native coroutine object, such as the result of calling an `async def`; no default. |

**Result:** the coroutine's result. A `KeyboardInterrupt` caught during runner
execution or teardown returns the literal integer `0`, even when `T` is not
`int`. The return annotation therefore does not describe this exceptional result.

**Explicit errors:** `TypeError("A coroutine object is required")` unless
`isinstance(coro, types.CoroutineType)` is true. A function, `None`, task, future,
or non-native awaitable fails this check. When a loop is already running in the
calling thread, the method itself raises `RuntimeError` before opening a runner:
`"Runner.run() cannot be called from a running event loop"` when a factory is
selected, otherwise `"asyncio.run() cannot be called from a running event loop"`.
That native coroutine remains unconsumed; close it or await it appropriately.

**Propagated errors:** coroutine failures other than the caught
`KeyboardInterrupt`, factory failures, and runner failures are not generally
translated. Reusing a consumed coroutine passed the native-type check but raised
`RuntimeError("cannot reuse already awaited coroutine")` in the validated runtime.

With a factory, the method uses `with asyncio.Runner(loop_factory=factory)`;
without one, it uses `asyncio.run(coro)`. The runner owns a new loop and its
teardown. This does not consume or populate `Loop`'s thread-local loop cache.
Factory resolution and the running-loop guard precede the `KeyboardInterrupt`
handler. Use `run()` at an entry point without an active loop in that thread.

### Loop.runSync()

Source: [orionis/aio/loop.py](../loop.py#L372), `Loop.runSync`;
pool initialization is in `Loop._getSyncExecutor` in the same file.

```python
@classmethod
def runSync[T](cls, coro: Coroutine[Any, Any, T]) -> T:
```

| Parameter | Declared annotation | Accepted value |
| --- | --- | --- |
| `coro` | `Coroutine[Any, Any, T]` | A native coroutine object accepted by `run()`; no default. |

Without a running loop in the caller's thread, delegates to `cls.run(coro)`.
Otherwise submits `cls.run` to the cached
`ThreadPoolExecutor(max_workers=1, thread_name_prefix="orionis-sync")` and waits
on `.result()` with **no timeout**. The coroutine then runs on a separate worker
loop, while the caller's thread, including its event loop, remains blocked.

**Result:** the result of `run()`, including integer `0` for a handled
`KeyboardInterrupt`. **Errors:** `run()`'s validation and execution errors reach
the caller directly or through the executor future; executor failures can also
propagate. The running-loop branch may create the pool even for invalid input,
because native-coroutine validation happens inside the submitted `run()`.

The worker and pool are shared on the class; arguments are not cloned. Do not
pass work that depends on the blocked caller's progress or requires the same
sole worker recursively. This bridge does not make loop-bound clients portable.
See `Unique.enforce()` above for a real consumer that creates an isolated
connection for the cross-loop branch.

### Loop.execute()

Source: [orionis/aio/loop.py](../loop.py#L266), `Loop.execute`.

```python
@staticmethod
async def execute(
        func: Callable[..., Any],
        /,
        *args: Any,  # noqa: ANN401
        **kwargs: Any,  # noqa: ANN401
) -> Any:  # noqa: ANN401
```

| Parameter | Declared annotation | Meaning |
| --- | --- | --- |
| `func` | `Callable[..., Any]` | Callable to invoke; required and positional-only. |
| `*args` | `Any` | Positional arguments forwarded unchanged; may be empty. |
| `**kwargs` | `Any` | Keyword arguments forwarded unchanged; may be empty. |

**Awaited result:** if `inspect.iscoroutinefunction(func)` is true, returns
`await func(*args, **kwargs)` directly. Otherwise it submits a
`functools.partial` to the current loop's **default executor**, waits for the
result, then awaits it only if `hasattr(result, "__await__")` is true.
An ordinary result, including `None`, is returned unchanged.

This last check is attribute-based, not `inspect.isawaitable()`. A
generator-based awaitable without `__await__` was returned unchanged in the
runtime probe. An object with an invalid `__await__` can instead fail when awaited.
Callable instances not detected as coroutine functions take the executor path;
a native coroutine they return is subsequently awaited on the caller's loop.

**Explicit error:** `TypeError("The provided object is not callable")` when
`callable(func)` is false. **Propagated errors:** argument-binding failures,
callable failures, await failures, cancellation, and executor failures. In the
synchronous branch, `asyncio.get_running_loop()` also raises `RuntimeError`
if the coroutine is driven without a running loop.

Calling `execute()` alone just constructs its coroutine; invocation occurs when
it is awaited. It does not copy arguments, close returned resources, shield work,
or join a worker after cancellation. A worker already executing continued after
its waiting task was cancelled in the isolated probe. See example 3 and the
concurrency section.

### Loop.createTask()

Source: [orionis/aio/loop.py](../loop.py#L350), `Loop.createTask`.

```python
@staticmethod
async def createTask[T](
        coro: Coroutine[Any, Any, T],
        *,
        name: str | None = None,
) -> asyncio.Task[T]:
```

| Parameter | Declared annotation | Meaning |
| --- | --- | --- |
| `coro` | `Coroutine[Any, Any, T]` | Coroutine passed directly to the running loop's `create_task()`; required. |
| `name` | `str \| None` | Optional task name; keyword-only, defaults to `None`. |

**Awaited result:** a scheduled `asyncio.Task[T]`, not the completed task's value.
Use `task = await Loop.createTask(coro)` and then `result = await task`.
The method itself has no suspension after calling `create_task()`, but calling it
without awaiting it does not schedule `coro`.

There is no module-level validation: input validation and scheduling behavior
belong to `asyncio.get_running_loop().create_task(coro, name=name)`, including any
custom task factory. Missing running loop propagates `RuntimeError`; invalid
coroutines can propagate `TypeError`. Task failures surface when the returned
task is awaited, not as this helper's completed task result. No task registry,
automatic joining, cancellation, or task-factory override is added.

### Loop.eventLoopContext()

Source: [orionis/aio/loop.py](../loop.py#L314), `Loop.eventLoopContext`.

```python
@staticmethod
@contextmanager
def eventLoopContext() -> Generator[asyncio.AbstractEventLoop]:
```

**Parameters:** none. The `@contextmanager` decorator provides a **synchronous**
context manager, used with `with`, not `async with`. Entering it obtains
`Loop.getEventLoop()`; the generator yields that loop once. The declaration's
generator annotation describes the decorated function's underlying generator,
not the externally returned context-manager object's type.

On exit, if the loop is not running, the method snapshots `asyncio.all_tasks(loop)`.
If this set is nonempty, it calls `cancel()` on every included task and drains
them with `loop.run_until_complete(asyncio.gather(..., return_exceptions=True))`.
This includes unrelated pending tasks on the borrowed loop, not just tasks
created within the block. Completed tasks are absent from that set. There is
no loop closure, async-generator shutdown, executor shutdown, or cleanup timeout.

When the loop is running at exit, **all cleanup is skipped**. With no pending
tasks, no gather is run. The cleanup region suppresses only `RuntimeError` and
`asyncio.CancelledError`; acquisition failures occur before that region. Ordinary
task exceptions returned by `gather` are discarded. A body exception propagates
when cleanup completes; do not infer universal exception suppression from the
docstring. Repeated use on an open cached loop is possible, but a decorated
context-manager instance is not a reusable lifecycle object.

### Loop.isLoopRunning()

Source: [orionis/aio/loop.py](../loop.py#L339), `Loop.isLoopRunning`;
detection helper `Loop._getRunningLoop` starts in the same file at
[the helper declaration](../loop.py#L70).

```python
@staticmethod
def isLoopRunning() -> bool:
```

**Parameters:** none. **Result:** whether `asyncio.get_running_loop()` succeeds
in the calling thread. The helper translates its `RuntimeError` into `None`;
this method returns whether the result is not `None`. It creates no loop and
mutates no cache. A cached but stopped loop, or a loop running in another thread,
does not make the result true. There is no explicit error raised by this method;
unexpected errors other than the helper's caught `RuntimeError` are not translated.

## Usage examples

Each block in this section is an independent script for Python 3.14+ with the
framework installed, or the checkout root on `PYTHONPATH`. No application boot,
credentials, or external services are needed. Assertions define the expected
behavior; each script prints only `example-N: OK` after its assertions pass.
Do not combine these scripts into a shared process when verifying class state.

### 1. Run an entry-point coroutine

The native coroutine runs to completion and exposes its loop only while active.

```python
import asyncio
from orionis.aio import Loop


async def main() -> int:
        assert Loop.isLoopRunning()
        assert Loop.getEventLoop() is asyncio.get_running_loop()
        await asyncio.sleep(0)
        return sum((10, 20, 30))


assert not Loop.isLoopRunning()
assert Loop.run(main()) == 60
assert not Loop.isLoopRunning()
print("example-1: OK")
```

### 2. Bridge from synchronous code

Without an active loop the coroutine runs in the caller's thread. Inside one,
`runSync()` blocks while the independent coroutine runs in the bridge worker.

```python
import threading
from orionis.aio import Loop


async def identify_thread() -> int:
        return threading.get_ident()


async def inside_loop() -> int:
        assert Loop.isLoopRunning()
        return Loop.runSync(identify_thread())


caller_thread = threading.get_ident()
assert Loop.runSync(identify_thread()) == caller_thread
assert Loop.run(inside_loop()) != caller_thread
print("example-2: OK")
```

### 3. Execute both kinds of callable

The synchronous invocation uses another thread; coroutine functions and native
coroutines returned by synchronous factories are awaited on the caller's loop.

```python
import asyncio
import threading
from orionis.aio import Loop


async def append_suffix(value: str, *, suffix: str) -> str:
        await asyncio.sleep(0)
        return value + suffix


def coroutine_factory(value: str, *, suffix: str) -> object:
        return append_suffix(value, suffix=suffix)


async def main() -> None:
        caller_thread = threading.get_ident()
        assert await Loop.execute(threading.get_ident) != caller_thread
        assert await Loop.execute(append_suffix, "direct", suffix="!") == "direct!"
        factory_result = await Loop.execute(
                coroutine_factory, "factory", suffix="!",
        )
        assert factory_result == "factory!"


Loop.run(main())
print("example-3: OK")
```

### 4. Schedule and join named tasks

Creating a task and waiting for its value are separate operations. Cleanup joins
every task retained by this example, including on an intermediate failure.

```python
import asyncio
from orionis.aio import Loop


async def square(value: int) -> int:
        await asyncio.sleep(0)
        return value * value


async def main() -> None:
        tasks: list[asyncio.Task[int]] = []
        try:
                for value in range(4):
                        task = await Loop.createTask(
                                square(value), name=f"square-{value}",
                        )
                        tasks.append(task)
                assert [task.get_name() for task in tasks] == [
                        f"square-{value}" for value in range(4)
                ]
                assert await asyncio.gather(*tasks) == [0, 1, 4, 9]
        finally:
                for task in tasks:
                        if not task.done():
                                task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)


Loop.run(main())
print("example-4: OK")
```

### 5. Clean up a stopped loop

The context cancels a pending task, retains the open loop, and permits reuse.
The script closes that loop itself and verifies replacement of the closed cache.

```python
import asyncio
from orionis.aio import Loop


async def wait_forever() -> None:
        await asyncio.Event().wait()


loop = Loop.getEventLoop()
try:
    assert Loop.getEventLoop() is loop
    with Loop.eventLoopContext() as borrowed:
        assert borrowed is loop
        leftover = borrowed.create_task(wait_forever())
        borrowed.run_until_complete(asyncio.sleep(0))
    assert leftover.cancelled()
    assert not loop.is_closed()
    assert not Loop.isLoopRunning()
finally:
    loop.close()
    asyncio.set_event_loop(None)

replacement = Loop.getEventLoop()
try:
    assert replacement is not loop and not replacement.is_closed()
finally:
    replacement.close()
    asyncio.set_event_loop(None)
print("example-5: OK")
```

### 6. Handle rejected inputs and nested execution

These are actual module validation errors. The rejected native coroutine remains
unstarted and is explicitly closed by its owner after the nested-run attempt.

```python
from orionis.aio import Loop


async def noop() -> None:
        return None


try:
    Loop.run(noop)
except TypeError as error:
    assert str(error) == "A coroutine object is required"
else:
    raise AssertionError("A coroutine function was accepted")


async def check_errors() -> None:
    try:
        await Loop.execute(42)
    except TypeError as error:
        assert str(error) == "The provided object is not callable"
    else:
        raise AssertionError("A non-callable value was accepted")

    coroutine = noop()
    try:
        try:
            Loop.run(coroutine)
        except RuntimeError:
            pass
        else:
            raise AssertionError("A nested runner was accepted")
    finally:
        coroutine.close()


Loop.run(check_errors())
print("example-6: OK")
```

### 7. Integrate with FreezeThaw

`Loop.execute()` returns the other Orionis component's actual result. This
integration uses an acyclic local structure; it does not claim that this module
provides freezing semantics or manages application configuration.

```python
from types import MappingProxyType
from orionis.aio import Loop
from orionis.support.structures.freezer import FreezeThaw


async def main() -> None:
        payload = {"names": ["Ada", "Linus"]}
        frozen = await Loop.execute(FreezeThaw.freeze, payload)
        assert isinstance(frozen, MappingProxyType)
        assert frozen["names"] == ("Ada", "Linus")
        editable = await Loop.execute(FreezeThaw.thaw, frozen)
        assert isinstance(editable, dict)
        editable["names"].append("Grace")
        assert editable["names"] == ["Ada", "Linus", "Grace"]
        assert payload["names"] == ["Ada", "Linus"]
        assert frozen["names"] == ("Ada", "Linus")


Loop.run(main())
print("example-7: OK")
```

### 8. Process temporary JSON files concurrently

Combine named tasks, synchronous file I/O dispatched with `execute()`, ordered
results, task joining, and temporary-directory cleanup. This is not a benchmark
or a claim that threads accelerate CPU-bound Python work.

```python
import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis.aio import Loop


def read_scores(path: Path) -> list[int]:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)["scores"]


async def summarize(path: Path) -> int:
        scores = await Loop.execute(read_scores, path)
        return sum(scores)


async def process(paths: tuple[Path, ...]) -> list[int]:
    tasks: list[asyncio.Task[int]] = []
    try:
        for path in paths:
            task = await Loop.createTask(summarize(path), name=path.stem)
            tasks.append(task)
        return list(await asyncio.gather(*tasks))
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


with TemporaryDirectory(prefix="orionis-aio-") as directory:
        paths: list[Path] = []
        for index, scores in enumerate(((1, 2), (3, 4), (5, 6))):
                path = Path(directory) / f"batch-{index}.json"
                path.write_text(json.dumps({"scores": scores}), encoding="utf-8")
                paths.append(path)
        assert Loop.run(process(tuple(paths))) == [3, 7, 11]
print("example-8: OK")
```

## Design characteristics

All mechanisms below are located in
[orionis/aio/loop.py](../loop.py), `Loop`, unless otherwise linked.

| Observed mechanism | Consumer-visible consequence |
| --- | --- |
| `_getRunningLoop()` catches `RuntimeError` from `asyncio.get_running_loop()`. | Detection is local to the calling thread and does not create a loop. |
| `_IS_WIN32` records `sys.platform == "win32"` at class definition. | Platform selection is not recalculated from environment variables on each call. |
| `_detectUvloop()` uses `_uvloop_checked`, `_uvloop_factory`, and `_loop_lock`. | Outside Windows, imports `uvloop` lazily and caches success or `ImportError`; on Windows it skips that import. |
| `_getLoopFactory()` uses `_loop_factory_resolved` and `_loop_factory_cached`. | Selects detected `uvloop.new_event_loop`, otherwise Windows `asyncio.ProactorEventLoop`, otherwise `None`. Missing Proactor attribute is tolerated; `None` delegates creation to asyncio. |
| `_loop_local` is `threading.local()`. | Open loops created through `getEventLoop()` are retained separately per thread, without automatic shutdown on thread exit. |
| `_getSyncExecutor()` uses `_sync_executor` and `_sync_executor_lock`. | Initializes one cached single-worker bridging pool with double-checked locking. |
| `run()` and `eventLoopContext()` explicitly reference `Loop`; class methods use `cls`. | Subclassing is not a complete way to customize every operation's factory or state. |
| `@contextmanager` wraps a generator; `createTask()` is itself asynchronous. | Use `with Loop.eventLoopContext()` and await task creation before awaiting its result. |

Importing the two module files defines the class, creates its `threading.local`
and two locks, and re-exports `Loop`; it does not create an event loop, pool, or
perform application startup. The parent package's lazy export resolver is in
[orionis/__init__.py](../../__init__.py) and
[orionis/_exports.py](../../_exports.py). Verified imports in isolated processes
resolved to this checkout, not a second framework installation.

## Performance and concurrency

Evidence: [orionis/aio/loop.py](../loop.py), particularly
`Loop._detectUvloop`, `Loop._getLoopFactory`, `Loop._getSyncExecutor`,
`Loop.runSync`, `Loop.execute`, and `Loop.eventLoopContext`.

- Detection and pool creation are deferred until needed. Subsequent calls use
    cached class state, including a failed `uvloop` import; there is no public
    invalidation or capacity control for these fixed entries.
- The running-loop path of `getEventLoop()` avoids the per-thread creation
    branch. `run()` instead creates a runner-owned loop for each valid call.
- `_loop_lock` protects `uvloop` detection and `_sync_executor_lock` protects
    pool creation. `_getLoopFactory()`'s final cached-field writes have no separate
    lock. A thread-local cache does not synchronize tasks, callbacks, or resources
    that users explicitly share between threads.
- Concurrent running-loop `runSync()` submissions share one worker and queue;
    `.result()` blocks without a timeout. The coroutine must be able to finish
    independently of the blocked caller and of recursive submissions to that
    worker. Class/docstring phrases about avoiding deadlock do not establish a
    universal deadlock-free contract.
- `execute()` uses the active loop's default executor, not the bridging pool.
    Parallelism and queueing depend on that executor. References captured by its
    `functools.partial` remain live while queued or running; mutable arguments are
    shared, not copied. There is no explicit per-submission context copy.
- Cancelling an await on `execute()` is not a stop mechanism for a synchronous
    callable already running in a thread. The module adds neither shielding nor
    a resource-cleanup protocol. Async-branch cancellation follows the callback.
- `eventLoopContext()` materializes the pending-task set and submits a gather.
    It issues one cancel per included task; tasks must cooperate. There is no
    timeout, and tasks created after the snapshot are not independently rescanned.
- The module never shuts down its cached bridge pool or closes loops retained
    by `getEventLoop()`. That statement does **not** apply to the dedicated loop
    owned and closed by each `run()` invocation.

> ⚠️ Not specified in the source code: module-wide safety under arbitrary
> concurrent access from multiple threads or multiple event loops, fairness
> between callers, and per-submission context-variable propagation.

No benchmarks, throughput figures, constant-time guarantees, or claims about
CPU-bound speedups were produced for this documentation task.

## Compatibility notes

| Evidence | Verified distinction |
| --- | --- |
| [pyproject.toml](../../../pyproject.toml), `project.requires-python` | The declared framework minimum is `>=3.14`; the examples target Python 3.14+. |
| [orionis/aio/loop.py](../loop.py), `run[T]`, `runSync[T]`, `createTask[T]` | PEP 695 function type-parameter syntax requires a parser supporting that syntax, introduced in Python 3.12. This does not declare framework support for 3.12 or 3.13. |
| [pyproject.toml](../../../pyproject.toml), `project.dependencies` | `uvloop>=0.22.1 ; sys_platform != 'win32'` is a platform-conditional **base** dependency, not an Orionis extra. The source tolerates its `ImportError` and falls back to asyncio. |
| [uv.lock](../../../uv.lock), package `uvloop` | The resolved version is `0.23.0`; this is not the supported minimum and was not installed or exercised on Windows during validation. |
| Actual validation | CPython `3.14.6`, `sys.platform == "win32"`; the selected loop was `asyncio.windows_events.ProactorEventLoop`. |

The module's other runtime imports are standard-library modules. `Callable`,
`Coroutine`, and `Generator` are imported only under `TYPE_CHECKING`, and
`from __future__ import annotations` retains string annotations. Consequently,
runtime type-hint resolution is not automatically complete: unassisted
`typing.get_type_hints(Loop.run)` raised `NameError` for `Coroutine` in the probe.
Literal declarations above are copied from source, not evaluated signatures.

> ⚠️ Not executed in this environment: a real `uvloop` backend, non-Windows
> execution, other Python releases, and a free-threaded Python build.

## Verification and limitations

Public inventory coverage is complete: both Python files, the `Loop` class and
re-export, and all seven public methods. The four private helpers and nine
private class-state fields are explained only where they determine public
behavior. Standard-library imports, names imported under `TYPE_CHECKING`, and
the reachable `loop` submodule attribute are excluded as additional consumer
symbols; they are not separately exported APIs. No public exceptions,
constants, properties,
protocols, enums, or overloads were found in the assigned module.

| Script | Syntax | Imports | Execution status |
| --- | --- | --- | --- |
| 1. Entry point | Passed | Local checkout verified | Executed successfully |
| 2. Synchronous bridge | Passed | Local checkout verified | Executed successfully |
| 3. Callable dispatch | Passed | Local checkout verified | Executed successfully |
| 4. Named tasks | Passed | Local checkout verified | Executed successfully |
| 5. Stopped-loop context | Passed | Local checkout verified | Executed successfully |
| 6. Real errors | Passed | Local checkout verified | Executed successfully |
| 7. FreezeThaw integration | Passed | Local checkout verified | Executed successfully |
| 8. Temporary JSON workflow | Passed | Local checkout verified | Executed successfully |

Each script was extracted from this README, parsed and compiled, import-checked,
and executed in a fresh process with a temporary working directory. The loaded
Orionis module paths were checked against the local repository. Every script
produced its expected success marker without stderr warnings.

The standalone behavior probes already confirmed the native-coroutine guard,
consumed-coroutine error, integer `0` on `KeyboardInterrupt`, cross-thread
`runSync()`, the attribute-based awaitable check, worker continuation after
cancelled waiting, context-body error propagation, conditional context cleanup,
cached-loop replacement, and the runtime type-hint limitation.

Existing tests were run through Orionis `TestingEngine` and `TestRunner` with
an application rooted in a temporary directory. Unmodified copies of
[tests/aio/test_loop.py](../../../tests/aio/test_loop.py) and
[tests/aio/test_package.py](../../../tests/aio/test_package.py) had their hashes
checked before execution. The result was **48 passed, 0 failed, 0 errored,
0 skipped**. Compilation caching and test-result persistence were disabled;
the local implementation was used. Test cases simulate optional-backend branches
with doubles; this does not certify the actual `uvloop` backend.

Neutral source/documentation distinctions:

- `run()` declares `-> T`, but its caught-interruption path returns integer `0`.
- The `run()` docstring associates the nested-loop error with standard-library
    entry points; the implementation raises it explicitly before entering them.
- `eventLoopContext()` says no exception escapes cleanup, but its suppression
    is limited to `RuntimeError` and `asyncio.CancelledError`; acquisition and body
    failures are not broadly caught, and cleanup may wait indefinitely.
- Class and `runSync()` docstrings use broad thread-safety/deadlock language;
    the executable mechanisms are the limited locks and blocking bridge described
    above, not unrestricted concurrency guarantees.

> ⚠️ Not executed in this environment: recursive `runSync()` submissions and
> cancellation-resistant cleanup tasks were not run because they can wait
> indefinitely and the module supplies no timeout.

This verification does not include live database or mail-service integration,
the entire framework test suite, or platform/version certification beyond the
runtime identified above. No implementation failure was repaired or source,
test, dependency, or configuration file changed as part of this task.
