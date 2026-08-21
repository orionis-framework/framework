# Orionis Background Tasks (`orionis.background`)

> Lightweight, execution-agnostic wrapper for running callables — sync or
> async — after the main flow of a request or process has completed.
>
> 🇪🇸 Versión en español: [README.es.md](README.es.md)

`orionis.background` provides a small set of classes to defer the execution
of one or more callables until after the "main" work is done — the same
concept used by web frameworks to run side effects (send an email, write an
audit log, warm a cache) **after** an HTTP response has been sent to the
client, without making the client wait for that side effect to finish.

---

## Table of contents

1. [Requirements](#requirements)
2. [What problem it solves](#what-problem-it-solves)
3. [API reference](#api-reference)
   - [`IBackgroundTask`](#ibackgroundtask)
   - [`BackgroundTask`](#backgroundtask)
   - [`BackgroundTasks`](#backgroundtasks)
   - [`is_async_callable()`](#is_async_callable)
4. [Usage examples](#usage-examples)
5. [Design notes](#design-notes)
6. [Performance and concurrency considerations](#performance-and-concurrency-considerations)
7. [Compatibility notes](#compatibility-notes)

---

## Requirements

No installation steps beyond the framework itself are required:

```bash
pip install orionis
```

- **Python:** 3.14 or newer.
- **Dependencies:** none beyond the Python standard library (`asyncio`,
  `functools`, `inspect`, `abc`).

## What problem it solves

Some operations triggered by a request or a workflow step do not need to
finish before the caller receives a result — e.g. sending a confirmation
email, logging an analytics event, or cleaning up a temporary file. Running
them inline would add unnecessary latency; running them with ad-hoc
`asyncio.create_task` calls scattered through the codebase is inconsistent
and hard to test. `orionis.background` standardises this pattern with a
minimal API:

- Wrap **any** callable — synchronous or asynchronous — behind the same
  interface (`BackgroundTask`), so callers don't need to branch on the
  callable's nature.
- Group **several** callables into a single unit that runs them in order
  (`BackgroundTasks`), useful when more than one side effect must follow an
  operation.
- Expose a common contract (`IBackgroundTask`) so other parts of the
  framework (e.g. `orionis.http.response`) can accept "something
  background-task-shaped" without depending on a concrete implementation.

## API reference

### `IBackgroundTask`

```python
from orionis.background.contracts.task import IBackgroundTask
```

Abstract base class (`abc.ABC`) that defines the contract every background
task implementation must satisfy.

| Member | Signature | Description |
| --- | --- | --- |
| `run` | `async def run(self) -> None` | Abstract coroutine method. Concrete subclasses must implement it to execute the task. |

**Raises:** instantiating `IBackgroundTask` directly raises `TypeError`
(standard `abc.ABC` behaviour) because `run` is abstract.

---

### `BackgroundTask`

```python
from orionis.background.task import BackgroundTask
```

Wraps a single callable — sync or async — along with the positional and
keyword arguments it should be called with, and exposes it as an awaitable
unit of work. Implements `IBackgroundTask`.

#### `BackgroundTask(func, *args, **kwargs)`

Constructor.

| Parameter | Type | Description |
| --- | --- | --- |
| `func` | `Callable` | The function (or coroutine function) to execute in the background. |
| `*args` | `object` | Positional arguments forwarded to `func` when the task runs. |
| `**kwargs` | `object` | Keyword arguments forwarded to `func` when the task runs. |

**Returns:** a new `BackgroundTask` instance. Whether calling `func`
produces an awaitable is detected once, at construction time, via
`is_async_callable`.

#### `await task()`

```python
async def __call__(self) -> None
```

Executes the wrapped callable:

- If calling `func` produces a coroutine, it is awaited directly:
  `await func(*args, **kwargs)`.
- Otherwise, `func` is invoked in the running loop's **default executor**
  via `loop.run_in_executor(None, functools.partial(func, *args, **kwargs))`
  so it does not block the event loop.

**Returns:** `None`.

**Raises:** propagates any exception raised by `func`.

**Side effects:** executes `func`, including whatever side effects `func`
itself has (I/O, logging, mutating state, etc.).

#### `await task.run()`

```python
async def run(self) -> None
```

Convenience coroutine that simply does `await self()`. Provided to satisfy
the `IBackgroundTask` contract explicitly (some callers may prefer calling
`.run()` over invoking the instance directly).

**Returns:** `None`.

**Raises:** same as `__call__`.

---

### `BackgroundTasks`

```python
from orionis.background.tasks import BackgroundTasks
```

Manages an **ordered collection** of `BackgroundTask` instances and runs
them one after another, in insertion order. Inherits from `BackgroundTask`
(so a `BackgroundTasks` instance can be used anywhere a single
`BackgroundTask` is expected — e.g. as the `background` argument of
`orionis.http.response.Response`), but overrides its constructor, `__call__`
and internal storage to hold a list of tasks instead of a single callable.

#### `BackgroundTasks(tasks=None)`

Constructor.

| Parameter | Type | Description |
| --- | --- | --- |
| `tasks` | `Sequence[BackgroundTask] \| None`, optional | An optional sequence of already-built `BackgroundTask` instances to seed the collection with. |

**Returns:** a new `BackgroundTasks` instance. The `tasks` argument is
converted to a `list` and exposed as the public attribute `self.tasks`. If
omitted or falsy, `self.tasks` starts as an empty list.

#### `bt.addTask(func, *args, **kwargs)`

```python
def addTask(self, func: Callable, *args: object, **kwargs: object) -> None
```

Wraps `func` (plus its arguments) in a new `BackgroundTask` and appends it
to `self.tasks`.

| Parameter | Type | Description |
| --- | --- | --- |
| `func` | `Callable` | The function (or coroutine function) to add as a new background task. |
| `*args` | `object` | Positional arguments forwarded to `func`. |
| `**kwargs` | `object` | Keyword arguments forwarded to `func`. |

**Returns:** `None`.

**Side effects:** mutates `self.tasks` in place (appends).

#### `await bt()`

```python
async def __call__(self) -> None
```

Executes every task currently in `self.tasks`, **sequentially**, in the
order they were added: `for task in self.tasks: await task()`.

**Returns:** `None`.

**Raises:** propagates the exception raised by whichever task fails; tasks
scheduled after the failing one are **not** executed (there is no
try/except around each iteration).

#### `await bt.run()`

```python
async def run(self) -> None
```

Inherited from `BackgroundTask`: it does `await self()`, which runs every
task in the collection.

**Returns:** `None`.

**Raises:** same as `__call__`.

---

### `is_async_callable()`

```python
from orionis.background.task import is_async_callable
```

Module-level helper used by `BackgroundTask` to decide how a callable must
be executed.

#### `is_async_callable(func)`

| Parameter | Type | Description |
| --- | --- | --- |
| `func` | `object` | Callable to inspect. `functools.partial` objects are unwrapped first, and instances are inspected through their `__call__`. |

**Returns:** `True` when invoking `func` produces a coroutine — coroutine
functions, partials of coroutine functions, and objects whose `__call__` is
a coroutine (such as `BackgroundTasks`) — and `False` otherwise, including
values that are not callable at all.

**Raises:** nothing.

## Usage examples

### 1. Wrapping a single synchronous function

```python
import asyncio
from orionis.background.task import BackgroundTask

def write_audit_log(user_id: int, action: str) -> None:
    print(f"[audit] user={user_id} action={action}")

async def main() -> None:
    task = BackgroundTask(write_audit_log, 42, action="login")
    await task()  # runs write_audit_log in the loop's default executor

asyncio.run(main())
```

### 2. Wrapping an async function

```python
import asyncio
from orionis.background.task import BackgroundTask

async def send_welcome_email(address: str) -> None:
    await asyncio.sleep(0.1)  # simulates an async I/O call
    print(f"welcome email sent to {address}")

async def main() -> None:
    task = BackgroundTask(send_welcome_email, "user@example.com")
    await task.run()

asyncio.run(main())
```

### 3. Running several tasks in sequence

```python
import asyncio
from orionis.background.tasks import BackgroundTasks

def log_event(event: str) -> None:
    print(f"event logged: {event}")

async def notify_admin(message: str) -> None:
    await asyncio.sleep(0.05)
    print(f"admin notified: {message}")

async def main() -> None:
    tasks = BackgroundTasks()
    tasks.addTask(log_event, "user.created")
    tasks.addTask(notify_admin, "a new user just signed up")

    await tasks()  # runs log_event, then notify_admin, in order

asyncio.run(main())
```

### 4. Attaching a background task to an HTTP response

```python
from orionis.background.task import BackgroundTask
from orionis.http.response import JSONResponse

async def send_confirmation(order_id: int) -> None:
    print(f"confirmation sent for order {order_id}")

def make_response(order_id: int) -> JSONResponse:
    background = BackgroundTask(send_confirmation, order_id)
    return JSONResponse({"order_id": order_id}, background=background)

# The framework calls `await response.runBackground()` internally after the
# response body has been sent to the client.
```

## Design notes

The following notes describe **existing** design decisions for
informational purposes only — they are not suggestions for change.

- **Single contract, two implementations.** `IBackgroundTask` (an `abc.ABC`)
  defines the minimal surface (`async def run(self) -> None`) that any
  background task must expose; `BackgroundTask` and `BackgroundTasks` both
  satisfy it, so code that only depends on the abstract contract can accept
  either one interchangeably.
- **Inheritance for structural compatibility.** `BackgroundTasks` extends
  `BackgroundTask` rather than only implementing `IBackgroundTask`
  directly. This allows a collection of tasks to be passed wherever an
  `isinstance(x, BackgroundTask)` check is performed — notably in
  `orionis.http.response`, whose responses accept a single
  `background: BackgroundTask | None` parameter. `BackgroundTasks`
  overrides `__init__` and `__call__` completely, so the parent's private
  `func`/`args`/`kwargs` attributes are never populated or used on a
  `BackgroundTasks` instance.
- **Name-mangled private state.** `BackgroundTask` stores `func`, `args`,
  `kwargs`, and the sync/async flag as double-underscore attributes
  (`self.__func`, `self.__args`, `self.__kwargs`, `self.__is_async`),
  relying on Python's name-mangling to keep them private to the class,
  rather than exposing them as part of the public API. Both classes and
  the contract declare `__slots__`, so task instances carry no `__dict__`.
- **Callable-as-task pattern.** Both classes implement `__call__`, so a
  task (or a task collection) can be invoked directly (`await task()`) or
  through the more descriptive `await task.run()` — both do exactly the
  same thing.
- **Sync/async detection happens once.** `BackgroundTask` inspects `func`
  with the module-level helper `is_async_callable` at construction time and
  caches the result (`self.__is_async`), rather than re-checking it on every
  invocation. The helper unwraps `functools.partial` objects and inspects
  `__call__` on instances, so callable objects returning a coroutine — a
  `BackgroundTasks` collection among them — are awaited instead of being
  offloaded to a thread and dropped.

## Performance and concurrency considerations

These are informative notes about existing behaviour, not tuning advice:

- Synchronous callables wrapped by `BackgroundTask` are always offloaded to
  the running event loop's **default executor** via
  `loop.run_in_executor(None, ...)`. This requires a running event loop
  (`asyncio.get_running_loop()` is called internally) — invoking a
  `BackgroundTask` wrapping a sync function outside of an active loop will
  raise a `RuntimeError`.
- Because the default executor is shared with everything else that uses it
  in the process, a long-running synchronous background task can consume
  one of its worker threads for its full duration.
- `BackgroundTasks.__call__` runs its tasks **sequentially, not
  concurrently** — each task is awaited before the next one starts. If
  several tasks need to run in parallel, they must be scheduled
  independently (e.g. with `asyncio.gather` or `Loop.createTask` from
  `orionis.aio`) rather than through a single `BackgroundTasks` instance.
- If one task in a `BackgroundTasks` collection raises, the exception
  propagates immediately and any remaining tasks in the list are **not**
  executed — there is no built-in error isolation between tasks.
- Async callables wrapped by `BackgroundTask` run on the same event loop
  that awaits them; they follow the normal cooperative-multitasking rules
  of `asyncio` (a long `await`-free async task can still delay other
  coroutines on the same loop).

## Compatibility notes

- **Minimum Python version:** 3.14.
- **Dependencies:** standard library only — `abc`, `asyncio`, `functools`,
  `inspect`, `typing`. No third-party packages are required by this
  module.
- **Framework integration:** `orionis.http.response` depends on
  `BackgroundTask` (accepts it as the `background` constructor parameter
  and exposes `await response.runBackground()`), so this module is a
  transitive dependency of the HTTP response layer.
