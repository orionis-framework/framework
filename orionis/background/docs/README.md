# orionis.background

> Wrap callables for awaited, in-process execution and compose ordered tasks.

Spanish version: [README.es.md](README.es.md).

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

There is no background-specific configuration, provider, installation extra,
or external worker service. The module imports standard-library utilities and
Orionis's `IBackgroundTask` and `Log`; it is not independent of the framework.
See [../task.py](../task.py), [../tasks.py](../tasks.py), and the dependency
versions in [Compatibility notes](#compatibility-notes).

- Execute the coroutine entry points in an asyncio context. The synchronous
  branch calls `asyncio.get_running_loop()` and uses its default executor.
  Each script below supplies its own context through `asyncio.run()`.
- To produce execution logs, initialize and pin the logger. Normal application
  startup boots `LoggerProvider`; in an already created headless application,
  `await LoggerProvider(app).boot()` performs that provider's pin operation.
  `Application.create()` alone does not perform that operation. Evidence:
  [../../logging/provider.py](../../logging/provider.py), `LoggerProvider.boot`;
  [../../foundation/application.py](../../foundation/application.py),
  `Application.create`, `Application.boot`, and `Application.__onStartup`.

Without a pinned `Log`, the module's unawaited `Log.info(...)` and
`Log.error(...)` calls create deferred dispatch objects and do not write
records. Task execution itself still works. This was checked in a fresh
process. Evidence: [../task.py](../task.py), `BackgroundTask.__call__`, and
[../../container/facades/meta.py](../../container/facades/meta.py),
`FacadeMeta.__getattr__` and `_FacadeDispatch`.

## Functional overview

`BackgroundTask` captures a callable and its arguments until explicitly
executed with `await task()` or `await task.run()`. `BackgroundTasks` composes
such tasks into a sequential, reusable collection. A single task delegates
execution records to Orionis's `Log` facade.

Construction does not schedule or invoke the callback. The module contains no
automatic dispatch, persistent queue, scheduler, retry policy, timeout, or
process-lifetime completion mechanism. These statements concern this module,
not other Orionis subsystems. Evidence: the complete implementations in
[../task.py](../task.py) and [../tasks.py](../tasks.py).

### HTTP integration

`Response.__init__` accepts `background: BackgroundTask | None` and explicitly
rejects other objects with `TypeError`. `BackgroundTasks` is accepted because
it inherits `BackgroundTask`; implementing only `IBackgroundTask` is not
sufficient. `Response.runBackground()` awaits `self.background()` when that
attribute is truthy. It neither clears the attribute nor marks it completed,
so another call executes the work again. Evidence:
[../../http/responses.py](../../http/responses.py), `Response.__init__` and
`Response.runBackground`.

`ASGIResponseAdapter.send` and `RSGIResponseAdapter.send` await this hook after
their successful response-delivery path, including HEAD. They do not detach it
with `asyncio.create_task`. ASGI's buffered path has already awaited the final
body message; RSGI's buffered and file paths have submitted the response to
the protocol. This does not prove that a remote client received the bytes.
An earlier sending/cleanup failure prevents the hook from being reached;
an SSE disconnect path can return without executing it. Evidence:
[../../http/adapters/response/asgi.py](../../http/adapters/response/asgi.py),
`ASGIResponseAdapter.send` and `ASGIResponseAdapter.__sendHead`;
[../../http/adapters/response/rsgi.py](../../http/adapters/response/rsgi.py),
`RSGIResponseAdapter.send` and `RSGIResponseAdapter.__sendResponseStream`.

## Module structure

All five Python files under `orionis/background` were inspected recursively.
No non-Python runtime resource is referenced by these implementations.

```text
orionis/background/
|-- __init__.py
|-- task.py
|-- tasks.py
|-- contracts/
|   |-- __init__.py
|   `-- task.py
`-- docs/
    |-- README.md
    |-- README.es.md
    `-- SKILL.md
```

| Source | Responsibility | Documented public surface |
| --- | --- | --- |
| [../__init__.py](../__init__.py) | Reexport the concrete classes. | `BackgroundTask`, `BackgroundTasks`, `__all__`. |
| [../task.py](../task.py) | Classify callables, execute one callback, and log its outcome. | `is_async_callable`, `BackgroundTask`, its constructor, `__call__`, and `run`. |
| [../tasks.py](../tasks.py) | Store and execute an ordered task list. | `BackgroundTasks`, its constructor, `tasks`, `addTask`, `__call__`, and inherited `run`. |
| [../contracts/task.py](../contracts/task.py) | Declare the abstract execution contract. | `IBackgroundTask` and `run`. |
| [../contracts/__init__.py](../contracts/__init__.py) | Empty package initializer. | No explicit public reexports. |

## API reference

The declaration blocks in this section copy source signatures, including
decorators and formatting. They are reference fragments without method
bodies, not runnable scripts. The scripts in [Usage examples](#usage-examples)
are independent executable examples.

### Public imports and exports

| Symbol | Verified import | Definition |
| --- | --- | --- |
| `BackgroundTask` | `from orionis.background import BackgroundTask` or `from orionis.background.task import BackgroundTask` | [../task.py](../task.py) |
| `BackgroundTasks` | `from orionis.background import BackgroundTasks` or `from orionis.background.tasks import BackgroundTasks` | [../tasks.py](../tasks.py) |
| `IBackgroundTask` | `from orionis.background.contracts.task import IBackgroundTask` | [../contracts/task.py](../contracts/task.py) |
| `is_async_callable` | `from orionis.background.task import is_async_callable` | [../task.py](../task.py) |

The package's public export list is copied from
[../__init__.py](../__init__.py):

```python
__all__ = [
    "BackgroundTask",
    "BackgroundTasks",
]
```

The helper and contract are documented because they have public names and
existing direct consumers/tests; they are not root-package reexports.
Imported utilities such as `asyncio`, `Any`, `Callable`, and `Log` are
dependencies, not additional background APIs. The name-mangled task fields
are implementation state; `__slots__` is covered under design characteristics.
The empty contracts initializer does not reexport `IBackgroundTask`.
Evidence: [../../../tests/background/test_package.py](../../../tests/background/test_package.py),
[../../../tests/background/test_task.py](../../../tests/background/test_task.py),
and [../../../tests/background/contracts/test_task.py](../../../tests/background/contracts/test_task.py).

### IBackgroundTask

Import `orionis.background.contracts.task.IBackgroundTask`. Source:
[../contracts/task.py](../contracts/task.py).

```python
class IBackgroundTask(ABC):
```

```python
@abstractmethod
async def run(self) -> None:
```

An `abc.ABC` with `__slots__ = ()`, no explicit constructor, and exactly one
abstract member, `run`. The declaration requires no arguments beyond `self`
and describes an awaited result of `None`. Its body contains only a docstring;
there is no default task execution. Implement the execution behavior in a
concrete subclass.

Direct instantiation, or instantiation of a subclass leaving `run` abstract,
raises Python's `TypeError`. No additional validation of callbacks or subclass
method signatures is implemented here. The contract does not declare
`__call__`, so use `await implementation.run()` for a contract-only object.
Concrete subclass state, effects, and exceptions depend on that implementation.
HTTP's concrete-type restriction is described above. Evidence:
[../../../tests/background/contracts/test_task.py](../../../tests/background/contracts/test_task.py),
`TestBackgroundTaskContract`.

### is_async_callable

Import `orionis.background.task.is_async_callable`. Source:
[../task.py](../task.py), `is_async_callable`.

```python
def is_async_callable(func: object) -> bool:
```

| Item | Implemented behavior |
| --- | --- |
| `func: object` | Target to inspect; it is not called. |
| Inspection | Unwrap `functools.partial` repeatedly, then apply `inspect.iscoroutinefunction` to the target. Otherwise, check the `__call__` attribute of a callable target. |
| Result | `True` when either coroutine-function check succeeds; otherwise `False`. Ordinary non-callable values such as `42` return `False`. |
| State and effects | No module cache or target invocation. Custom attribute lookup can itself have effects or raise. |
| Exceptions | No explicit `raise` or exception handler. Attribute-inspection exceptions propagate; a throwing `__call__` lookup was checked. |

A normal synchronous function returning a coroutine is classified `False`.
An async callable instance and a partial of it are classified `True`. The
executor branch of `BackgroundTask` separately inspects the returned value,
so this classification does not determine whether that result is awaited.
The helper itself never validates the eventual result or argument signature.

**Docstring discrepancy:** the helper's docstring describes whether invoking
the target produces an awaitable/coroutine. The implementation only inspects
coroutine-function status; it does not invoke the target. This distinction
was checked using a synchronous coroutine factory. Existing evidence:
[../../../tests/background/test_task.py](../../../tests/background/test_task.py),
`TestIsAsyncCallable`.

### BackgroundTask

Import `orionis.background.task.BackgroundTask`, also reexported by
`orionis.background`. Source: [../task.py](../task.py), `BackgroundTask`.

```python
class BackgroundTask(IBackgroundTask):
```

#### Construction

```python
def __init__(
    self,
    func: Callable,
    *args: object,
    **kwargs: object,
) -> None:
```

| Parameter | Meaning and restrictions |
| --- | --- |
| `func: Callable` | Required callback. The annotation is unparameterized; no callability check is enforced by the constructor. |
| `*args: object` | Positional arguments captured in a tuple. Defaults to an empty tuple when omitted. |
| `**kwargs: object` | Keyword arguments captured in a dictionary. Defaults to an empty dictionary when omitted. |

The constructor returns `None` and normal class construction produces the
task instance. It retains the callback and argument values without deep
copying them, and caches `is_async_callable(func)` once for this instance.
Changes to referenced mutable objects before a later execution are observable
by the callback. It does not invoke the callback or obtain an event loop.
Inspection errors can propagate during classification.

`BackgroundTask(42)` is accepted at construction despite its annotation;
execution later raises `TypeError` while building `functools.partial`.
Missing or incompatible callback arguments are also validated only when
the callback is actually invoked. Evidence:
[../../../tests/background/test_task.py](../../../tests/background/test_task.py),
`TestBackgroundTaskConstruction` and
`TestBackgroundTaskSynchronousExecution.testRejectsNonCallableTargetsWhenExecuted`.

#### Invocation

```python
async def __call__(self) -> None:
```

`await task()` executes one fresh invocation:

1. Resolve its logging name from `func.__qualname__`, falling back to the
   callable's class name. A partial normally uses `partial` as that fallback.
   This lookup occurs before the execution `try` block.
2. For a cached asynchronous classification, directly await
   `func(*args, **kwargs)` on the caller's event loop.
3. Otherwise bind the arguments with `functools.partial` and await
   `loop.run_in_executor(None, bound)`. If its result satisfies
   `inspect.isawaitable(result)`, await that result on the caller's loop too.
4. Discard the callback's result, including the value produced by a returned
   awaitable, and return `None` after successful logging.

The worker branch does not automatically iterate an ordinary or asynchronous
generator. Only an awaitable result is additionally awaited. It does not
relocate loop-bound resources returned by the callback. The extra result
check exists only in the executor branch: values returned by a directly
awaited async callback are discarded without a second await.

Within the execution block, `except Exception` calls `Log.error` and uses a
bare `raise`. The `else` block calls `Log.info`; actual record emission depends
on the pinned logger's configuration and filtering. The message templates in
[../task.py](../task.py) are:

```text
Background task '<task_name>' failed: <error>
Background task '<task_name>' executed successfully.
```

These are templates, not fixed runtime output. Callback and executor errors
propagate if error logging succeeds. Logging can itself fail: an error in
`Log.error` interrupts the bare re-raise, and an error in `Log.info` escapes
even though the callback has already completed. Name-lookup errors occur
outside the handler. `asyncio.CancelledError` is not caught by
`except Exception`. These boundaries make an exhaustive exception list
inappropriate for arbitrary callbacks and logging configurations.

The task does not cache results or mark itself consumed; each invocation runs
again. `task()` produces a coroutine that must be awaited or scheduled by its
caller. The instance itself has no `__await__`: `await task` is not this API.
The wrapper performs no automatic cleanup of callback-owned resources.
Evidence: [../task.py](../task.py), `BackgroundTask.__call__`, and
[../../../tests/background/test_task.py](../../../tests/background/test_task.py),
`TestBackgroundTaskSynchronousExecution` and
`TestBackgroundTaskAsynchronousExecution`.

#### Explicit execution

```python
async def run(self) -> None:
```

`await task.run()` delegates to `await self()` and returns `None`. It has the
same execution effects and exception boundaries as `__call__`, with no
additional validation or exception handling. Source:
[../task.py](../task.py), `BackgroundTask.run`; tests:
[../../../tests/background/test_task.py](../../../tests/background/test_task.py),
`TestBackgroundTaskRunMethod`.

### BackgroundTasks

Import `orionis.background.tasks.BackgroundTasks`, also reexported by
`orionis.background`. Source: [../tasks.py](../tasks.py), `BackgroundTasks`.

```python
class BackgroundTasks(BackgroundTask):
```

#### Construction and tasks

```python
def __init__(self, tasks: Sequence[BackgroundTask] | None = None) -> None:
```

`tasks` is an optional initial sequence of task objects. The constructor
returns `None` and initializes this public, writable attribute literally as:

```python
self.tasks: list[BackgroundTask] = list(tasks) if tasks else []
```

`None` and an empty/falsy input create a fresh empty list. A truthy input is
materialized through `list(tasks)`: the list is copied, but its task objects
are not. Truthiness or iteration errors propagate. The annotation does not
enforce element types at runtime, and entries are not wrapped or validated.
An invalid entry fails later when `__call__` tries to call and await it.

Mutating the input list after construction does not change the new list;
mutating a shared task object still affects that task. The public `tasks`
attribute can be inspected, appended to, cleared, or reassigned without a
setter check. Later methods operate on its then-current value. Duplicate
entries are kept and executed separately. The constructor does not call the
parent constructor: the single-task callback slots remain uninitialized and
are not used by the overridden execution method.
Evidence: [../tasks.py](../tasks.py), `BackgroundTasks.__init__`, and
[../../../tests/background/test_tasks.py](../../../tests/background/test_tasks.py),
`TestBackgroundTasksInitialization`.

#### Registration

```python
def addTask(
    self, func: Callable, *args: object, **kwargs: object,
) -> None:
```

`func`, `*args`, and `**kwargs` have the same meanings and restrictions as
in `BackgroundTask.__init__`. This method creates a new `BackgroundTask`
and appends it to `self.tasks`, returning `None`, not the collection.
It neither executes nor deduplicates callbacks. Classification errors from
the new wrapper propagate before append; errors from a replaced `tasks`
container can also propagate.

An async callable instance, another task, or another `BackgroundTasks` can
be registered as a callable. Registering an inner collection through
`addTask(inner)` adds an outer wrapper, so that wrapper also produces its own
logging call. A directly seeded inner collection does not add that wrapper.
Evidence: [../tasks.py](../tasks.py), `BackgroundTasks.addTask`, and
[../../../tests/background/test_tasks.py](../../../tests/background/test_tasks.py),
`TestBackgroundTasksAddTask` and
`TestBackgroundTasksExecution.testRunsNestedCollectionsRegisteredWithAddTask`.

#### Invocation and inherited run

```python
async def __call__(self) -> None:
```

The implementation is a live-list iteration: `for task in self.tasks:
await task()`. Each entry finishes before the next begins; it returns `None`
when all entries complete. An empty collection is a no-op. It has no snapshot,
per-entry exception handler, collection-level logging call, or completion
flag. The first exception stops the sequence; later tasks are not invoked
in that run, and the stored list remains intact.

Append/removal during execution can change which entries the current list
iterator visits. A probe confirmed that an append during the first callback
is visited in the same run. Subsequent runs start from the beginning of the
then-current list, including tasks already completed in a prior failed run.
Nested collections execute depth-first according to their stored ordering;
there is no cycle detector.

`run` is inherited unchanged from `BackgroundTask`: its literal signature
is `async def run(self) -> None:` as shown above, and `await self()` dispatches
to this collection's `__call__`. It has the same ordering, results, and
exception behavior. Evidence: [../tasks.py](../tasks.py),
`BackgroundTasks.__call__`; [../task.py](../task.py), `BackgroundTask.run`;
[../../../tests/background/test_tasks.py](../../../tests/background/test_tasks.py),
`TestBackgroundTasksExecution` and
`TestBackgroundTasksSubstitutability.testInheritsTheRunEntryPoint`.

## Usage examples

Run each block as a separate script with the installed framework and Python
3.14+. Each supplies its own asyncio context and uses no external service.
These examples deliberately do not start an application or pin `Log`, so
they verify task effects, not execution-log records. Configured logging was
checked separately with an isolated application during the native test run.

### 1. Run and reuse a synchronous task

Construction is lazy, the callback runs on a worker thread, and both entry
points discard its return value. Reusing the instance invokes it again.

```python
import asyncio
import threading
from orionis.background import BackgroundTask

observed: list[tuple[int, int]] = []

def record(value: int) -> str:
    """Record a value and the executing thread."""
    observed.append((value, threading.get_ident()))
    return "discarded"

async def main() -> None:
    """Execute the same task through both entry points."""
    loop_thread = threading.get_ident()
    task = BackgroundTask(record, 7)
    assert observed == []
    assert await task() is None
    assert await task.run() is None
    assert [value for value, thread_id in observed] == [7, 7]
    assert all(thread_id != loop_thread for value, thread_id in observed)

asyncio.run(main())
```

### 2. Detect and await an async callable instance

The helper looks through a partial and recognizes the instance's async
`__call__`. The callback completes before `run` returns.

```python
import asyncio
from functools import partial
from orionis.background import BackgroundTask
from orionis.background.task import is_async_callable

class Recorder:
    """Collect values through an async call method."""

    __slots__ = ("values",)

    def __init__(self) -> None:
        """Initialize the recorded values."""
        self.values: list[str] = []

    async def __call__(self, value: str) -> None:
        """Record one supplied value."""
        self.values.append(value)

async def main() -> None:
    """Classify and execute a partially bound callable instance."""
    recorder = Recorder()
    bound = partial(recorder, "completed")
    assert is_async_callable(bound)
    assert await BackgroundTask(bound).run() is None
    assert recorder.values == ["completed"]

asyncio.run(main())
```

### 3. Handle a callback failure in a collection

The callback's `ValueError` reaches the caller; the following task does not
run. The collection still contains all three entries.

```python
import asyncio
from orionis.background import BackgroundTask, BackgroundTasks

events: list[str] = []

def record(value: str) -> None:
    """Append one execution marker."""
    events.append(value)

def reject() -> None:
    """Raise a deliberate callback failure."""
    error_msg = "task rejected"
    raise ValueError(error_msg)

async def main() -> None:
    """Observe the failure without losing the stored task list."""
    tasks = BackgroundTasks([BackgroundTask(record, "before")])
    tasks.addTask(reject)
    tasks.addTask(record, "after")
    try:
        await tasks.run()
    except ValueError as error:
        assert str(error) == "task rejected"
    else:
        error_msg = "Expected the callback failure"
        raise AssertionError(error_msg)
    assert events == ["before"]
    assert len(tasks.tasks) == 3

asyncio.run(main())
```

### 4. Execute after an in-memory ASGI response

This uses the real response and adapters with an in-memory ASGI send channel,
not a server or socket. It checks ordering after the buffered body message,
and demonstrates that an explicit second `runBackground()` repeats the work.

```python
import asyncio
from orionis.background import BackgroundTask
from orionis.http.adapters.request.asgi import ASGITransportAdapter
from orionis.http.adapters.response.asgi import ASGIResponseAdapter
from orionis.http.responses import Response

events: list[str] = []
messages: list[dict[str, object]] = []

async def receive() -> dict[str, object]:
    """Supply a complete empty request message."""
    return {"type": "http.request", "body": b"", "more_body": False}

async def send(message: dict[str, object]) -> None:
    """Record an ASGI response message."""
    messages.append(message)
    events.append(str(message["type"]))

async def after_send() -> None:
    """Record background execution after the final body message."""
    assert messages[-1]["type"] == "http.response.body"
    assert messages[-1]["more_body"] is False
    events.append("background")

async def main() -> None:
    """Send a buffered response through the real ASGI adapter."""
    adapter = ASGITransportAdapter({
        "type": "http", "method": "GET", "headers": [],
    })
    response = Response("accepted", background=BackgroundTask(after_send))
    assert events == []
    await ASGIResponseAdapter().send(adapter, response, receive, send)
    assert events == ["http.response.start", "http.response.body", "background"]
    assert messages[0]["status"] == 200
    assert messages[1]["body"] == b"accepted"
    await response.runBackground()
    assert events[-2:] == ["background", "background"]

asyncio.run(main())
```

### 5. Compose a local file workflow and an awaitable factory

The seeded list is copied, an inner collection is registered as a callable,
and a synchronous factory returns a coroutine that is awaited on the loop.
Every run repeats the workflow; the final explicit clear makes it a no-op.
The temporary directory is removed only after all awaited work completes.

```python
import asyncio
from collections.abc import Coroutine
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis.background import BackgroundTask, BackgroundTasks
from orionis.background.contracts.task import IBackgroundTask
from orionis.background.task import is_async_callable

def write_report(path: Path, content: str) -> None:
    """Write the local report from a worker thread."""
    path.write_text(content, encoding="utf-8")

def read_report(path: Path, events: list[str]) -> None:
    """Record the report contents from a worker thread."""
    events.append(path.read_text(encoding="utf-8"))

async def mark_ready(events: list[str]) -> None:
    """Record completion on the awaiting event loop."""
    events.append("ready")

def make_completion(events: list[str]) -> Coroutine[object, object, None]:
    """Return a coroutine without being a coroutine function."""
    return mark_ready(events)

async def execute(task: IBackgroundTask) -> None:
    """Execute any implementation through the abstract contract."""
    await task.run()

async def main() -> None:
    """Complete and replay an isolated mixed task workflow."""
    with TemporaryDirectory(prefix="orionis-background-example-") as directory:
        path = Path(directory) / "report.txt"
        events: list[str] = []
        seed = [BackgroundTask(write_report, path, "report")]
        inner = BackgroundTasks(seed)
        seed.clear()
        assert len(inner.tasks) == 1
        outer = BackgroundTasks()
        outer.addTask(inner)
        outer.addTask(partial(read_report, path), events)
        outer.addTask(make_completion, events)
        assert is_async_callable(inner)
        assert not is_async_callable(make_completion)
        await execute(outer)
        assert events == ["report", "ready"]
        await outer.run()
        assert events == ["report", "ready", "report", "ready"]
        outer.tasks.clear()
        assert await outer.run() is None

asyncio.run(main())
```

### 6. Implement the contract without a callable interface

Only `run` is required by the ABC. A contract-only implementation can execute
directly or have its bound `run` method wrapped in `BackgroundTask`. It is not
itself a valid value for `Response(background=...)`.

```python
import asyncio
from orionis.background import BackgroundTask
from orionis.background.contracts.task import IBackgroundTask

class Checkpoint(IBackgroundTask):
    """Count executions through the abstract contract."""

    __slots__ = ("executions",)

    def __init__(self) -> None:
        """Initialize the execution counter."""
        self.executions = 0

    async def run(self) -> None:
        """Record one completed execution."""
        self.executions += 1

async def main() -> None:
    """Execute a contract-only object and its wrapped method."""
    checkpoint = Checkpoint()
    assert not callable(checkpoint)
    await checkpoint.run()
    await BackgroundTask(checkpoint.run).run()
    assert checkpoint.executions == 2
    try:
        IBackgroundTask()
    except TypeError:
        pass
    else:
        error_msg = "Expected the abstract-construction error"
        raise AssertionError(error_msg)

asyncio.run(main())
```

## Design characteristics

| Observed mechanism | Consequence for consumers | Evidence |
| --- | --- | --- |
| `IBackgroundTask(ABC)` with one abstract coroutine | Consumers of the contract call `run`; HTTP uses a narrower concrete-type check. | [../contracts/task.py](../contracts/task.py); [../../http/responses.py](../../http/responses.py) |
| `BackgroundTasks(BackgroundTask)` with overridden constructor and invocation | Collections pass HTTP's `isinstance` check and reuse the inherited `run` dispatcher. | [../tasks.py](../tasks.py); [../task.py](../task.py) |
| Slots on the ABC and both concrete classes | The shipped task instances have no instance `__dict__`; arbitrary subclasses must make their own layout choices. | `IBackgroundTask.__slots__`, `BackgroundTask.__slots__`, `BackgroundTasks.__slots__` in the sources above |
| Per-instance cached coroutine classification | Classification is fixed at construction; the executor result is still inspected on every synchronous-branch run. | [../task.py](../task.py), `BackgroundTask.__init__` and `__call__` |
| Captured argument references and a public mutable task list | Mutable arguments and shared task objects remain live; collection construction only copies the outer list. | [../task.py](../task.py); [../tasks.py](../tasks.py) |

There is no module-level task/result cache, dataclass-generated constructor,
singleton task registration, or generator-based collection interface.
Imported `Log` uses its own facade state; it is not a per-task logger.
Evidence: all five module files, and
[../../container/facades/facade.py](../../container/facades/facade.py),
`Facade._pinned_instance`.

## Performance and concurrency

- Registration retains callback and argument references until the task itself
  is released. A seeded collection materializes a new list and retains the
  supplied task objects; execution does not clear it or copy it again.
- Every synchronous-branch invocation creates a new `functools.partial` and
  uses the loop's default executor, not a dedicated background pool. A running
  callback occupies a worker until it returns. Any awaitable it returns is
  subsequently awaited on the caller's loop.
- Async callbacks run directly on that loop. Their blocking operations can
  still block it; an `async def` declaration is not a nonblocking guarantee.
- `Log.info` and `Log.error` are called synchronously from the awaiting loop.
  With a pinned framework logger, initialization and file-handler operations
  can perform synchronous I/O. Evidence:
  [../../logging/logger.py](../../logging/logger.py), `Logger.info`,
  `Logger.error`, and `Logger.__initializeLogger`.
- A collection awaits entries sequentially. Separate concurrent calls on the
  same task or collection are not serialized, and can invoke the same callback
  more than once concurrently. The module contains no execution or list lock.
- The collection iterates its live list. Mutation across a callback's await
  can alter the current run, not just the next one. No exactly-once or
  snapshot-isolation behavior is implemented.
- Cancellation propagates through awaits; there is no shielding, timeout,
  retry, or worker-stop protocol here. Cancelling an awaiter does not forcibly
  stop an already running executor callback. A release-controlled worker probe
  confirmed that distinction.
- The wrapper uses `run_in_executor`, not `asyncio.to_thread`, and does not
  explicitly copy `contextvars` context. Do not infer context propagation or
  resource lifetime management from the word "background".

Unless separately linked, the evidence for these points is
[../task.py](../task.py), `BackgroundTask.__init__` and `__call__`, and
[../tasks.py](../tasks.py), `BackgroundTasks.__init__`, `addTask`, and
`__call__`. Repeated execution and sequential failure behavior are also
covered by [../../../tests/background/test_task.py](../../../tests/background/test_task.py)
and [../../../tests/background/test_tasks.py](../../../tests/background/test_tasks.py).

> ⚠️ Not specified in the source code: a safety contract for cross-thread
> reuse, concurrent mutation, or the thread safety of arbitrary callbacks.
> The observable lack of serialization above is not a blanket thread-safety
> guarantee.

## Compatibility notes

- Project minimum: Python `>=3.14`, declared by
  [../../../pyproject.toml](../../../pyproject.toml). This task targets 3.14+;
  validation used Windows CPython **3.14.6** from the repository virtualenv.
  No other Python version was certified by these executions.
- The concrete modules use `from __future__ import annotations`, union syntax,
  and `TYPE_CHECKING` imports of `Callable`/`Sequence`. Runtime execution does
  not need those annotation-only imports. Evaluating
  `typing.get_type_hints(BackgroundTask.__init__)` in the inspected module
  raised `NameError` for `Callable`; do not confuse that introspection issue
  with failure to execute a task. Evidence: [../task.py](../task.py) and
  [../tasks.py](../tasks.py).
- There are no direct third-party imports in these five files. `Log` is an
  internal runtime dependency. Its logging infrastructure and the HTTP
  integration use framework dependencies; they are not optional background
  extras. The module does not choose an asyncio loop implementation.

Relevant declared and resolved versions are distinct:

| Dependency and role | Manifest constraint | Lockfile resolution | Validation environment |
| --- | --- | --- | --- |
| `rich`, native test output | `>=15.0.0,<16.0` | `15.0.0` | `15.0.0` |
| `pendulum`, framework dates/startup | `>=3.2.0,<4.0` | `3.2.0` | `3.2.0` |
| `msgspec`, response infrastructure | `>=0.21.1` | `0.22.0` | `0.22.0` |
| `granian`, framework HTTP server | `>=2.8.3,<3.0` | `2.8.4` | `2.8.4` |
| `ruff`, development-only lint check | `>=0.16.8` | `0.16.9` | `0.16.9` |

Evidence: [../../../pyproject.toml](../../../pyproject.toml), `dependencies`
and `dependency-groups.dev`; [../../../uv.lock](../../../uv.lock), the named
package entries; installed versions were queried during validation. Lockfile
resolutions are not minimum supported versions. The ASGI example does not
start Granian or exercise its network protocol.

## Verification and limitations

### Coverage and evidence

The inventory covers five source files, three public classes, one public
helper, seven explicit method declarations, the `tasks` attribute, the two
root reexports, and `__all__`. All are represented above. Imported utilities
and private storage fields are excluded from the public API for the reasons
given under [Public imports and exports](#public-imports-and-exports).

The four existing test files were inspected:
[../../../tests/background/test_package.py](../../../tests/background/test_package.py),
[../../../tests/background/test_task.py](../../../tests/background/test_task.py),
[../../../tests/background/test_tasks.py](../../../tests/background/test_tasks.py),
and [../../../tests/background/contracts/test_task.py](../../../tests/background/contracts/test_task.py).
Native `TestingEngine` discovery and `TestRunner` execution ran **77/77 tests
successfully**, with zero raw failures, raw errors, or skips. The application
was created in a temporary directory, `LoggerProvider.boot()` initialized
the logging facade, and no result cache was enabled. This was not a run of
the checkout's configured Reactor bootstrap or a full-framework suite.

Supplementary local probes checked coroutine classification, local module
import origins, the annotation-evaluation failure, a synchronous coroutine
factory's worker/loop split, delayed rejection of a non-callable, live-list
append behavior, unsynchronized concurrent calls, and cancellation of an
awaiter while its executor callback continued. Further checks confirmed the
single await of a direct async callback, the unpinned logger after
`Application.create()`, and logging failures after callback success or during
error propagation. These are concrete checked cases, not universal callback
guarantees or benchmark measurements.

### Example results

| Example | Syntax | Local imports | Execution |
| --- | --- | --- | --- |
| 1. Synchronous task | Passed | Passed | Executed successfully. |
| 2. Async callable instance | Passed | Passed | Executed successfully. |
| 3. Callback failure | Passed | Passed | Executed successfully. |
| 4. ASGI response | Passed | Passed | Executed successfully. |
| 5. File workflow | Passed | Passed | Executed successfully. |
| 6. Abstract contract | Passed | Passed | Executed successfully. |

The eleven declarations, export list, and field initialization were compared
literally with local source. The six scripts were extracted from this README,
compiled, checked for local imports separately, and executed in separate
temporary working directories. No runtime warnings were emitted.

Both README files have 32 corresponding headings, 21 identical fenced blocks,
and 78 valid local links each. The skill's 14 links and its two-field YAML
frontmatter were checked independently; its derived name is
`orionis-background`. Manifest constraints and lockfile resolutions were
compared through TOML parsing. Scoped Ruff checks passed for the module and
its existing tests without fixes or cache writes. Validation scripts,
reports, and resources are kept outside the repository.

### Remaining limits

The helper docstring discrepancy and annotation-evaluation behavior are
documented above without changing the implementation. Callback-specific
exceptions and resource contracts cannot be reduced to an exhaustive list
by this wrapper. Test results do not imply durable execution or exactly-once
delivery.

The VS Code skill validator reports that the skill name differs from its
`docs` parent directory and treats `README.md#section` links as literal file
paths. Independent YAML parsing and Markdown target/anchor checks passed.
The requested name, directory, and valid section links are preserved: this
entry point does not claim automatic platform registration.

> ⚠️ Not executed in this environment: RSGI/SSE transport paths, real
> Granian/network delivery, Linux/free-threaded execution, and other Python
> versions. Transport execution was limited to buffered ASGI; validation used
> Windows CPython 3.14.6 and isolated local/in-memory resources.
