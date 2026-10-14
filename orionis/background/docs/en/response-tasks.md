# Running actions after responding

A background task belongs to the serving process and runs after response delivery. Use it for short side effects whose loss is acceptable; the queues module covers work requiring persistence and retries.

## Requirements

- Python 3.14 or newer.
- A normal Orionis installation; there is no module-specific extra or configuration.
- Direct execution expects a running event loop and a booted Orionis logger facade.
- No external service is required unless the wrapped callable requires one.
## Quick start

Attach a task to an HTTP response; Orionis runs it after sending the response:

```python
from orionis.background import BackgroundTask
from orionis.http.responses import Response


def record_delivery(message_id: int) -> None:
    print(f"delivered:{message_id}")


task = BackgroundTask(record_delivery, 42)
response = Response("accepted", status_code=202, background=task)

print(response.getStatusCode())       # 202
print(response.background is task)    # True
```

The snippet constructs the response without executing the task. The active ASGI/RSGI adapter calls it after completing the response body.

## Design a reliable side effect

Attach work with `Response(..., background=BackgroundTask(...))`. The adapter awaits `runBackground()` after sending the body. A client may already have received `202` when the callback fails; that status cannot be retroactively turned into an HTTP error. The callback needs its own diagnostics and recovery policy.

Pass identifiers and stable data instead of a mutable request or a file that will be closed when the flow ends. Commit any transaction the callback depends on before returning. There is no automatic after-commit hook. If the effect must survive process restarts, use a persistent queues connection and design the consumer for retries.

Collections preserve order and stop at the first failure. If two actions must be attempted independently, catch failures inside separate callbacks according to your policy; do not assume `BackgroundTasks` will continue. Running the collection again repeats every item: execution does not consume the list. Make operations idempotent when they may be invoked again.

To extend an attached task, subclass `BackgroundTask` and override `async __call__()`. Implementing only `IBackgroundTask` does not satisfy the concrete `Response` check. Manual execution requires an available `Log` facade; logger failures can also interrupt execution.

## Core concepts

### Deferred response work

A response owns at most one `BackgroundTask`. Because `BackgroundTasks` inherits from `BackgroundTask`, a collection can fill that slot. “Background” means after response delivery, not a detached daemon: the adapter awaits completion before it finishes handling the response.

### Callable classification

At construction, `BackgroundTask` detects coroutine functions, async callable objects, and `functools.partial` wrappers of async functions. These execute directly on the current loop. Other callables execute in `run_in_executor(None, ...)`; if such a callable returns an awaitable, the task awaits that result back on the loop.

### Ordered collections

`BackgroundTasks` keeps a mutable public `tasks` list. `addTask` wraps the supplied callable and appends it. Execution awaits each item in insertion order; the first exception stops the collection, so later tasks do not run.

## Common workflows

### Run one action after a response

Create `BackgroundTask(callable, ...)` and pass it as the response's `background` argument. Return immediately from the controller; the transport sends the body and then awaits the task.

### Group related actions

Create `BackgroundTasks`, call `addTask` in the required order, and attach the collection to the response. Use this when ordering matters; it does not run tasks concurrently.

### Run a task manually

Inside a booted async Orionis context, use `await task.run()` or `await task()`. Manual invocation is useful outside HTTP adapters, but still uses the logger facade and current loop.

## Examples

### Build an ordered collection

```python
from orionis.background import BackgroundTasks
from orionis.http.responses import Response


def audit(event: str) -> None:
    print(event)


async def notify(address: str) -> None:
    print(f"notify:{address}")


tasks = BackgroundTasks()
tasks.addTask(audit, "account-created")
tasks.addTask(notify, "user@example.test")

response = Response({"created": True}, status_code=201, background=tasks)
print(len(tasks.tasks))  # 2
```

When the transport runs the collection, `audit` completes before `notify` starts.


### Execute manually in an async Orionis context

```python
from orionis.background import BackgroundTask


async def refresh_index(document_id: int) -> None:
    print(f"indexed:{document_id}")


async def after_import() -> None:
    await BackgroundTask(refresh_index, 17).run()
```

Calling `after_import` prints `indexed:17` and records a success log.


### Preserve keyword arguments for synchronous work

```python
from orionis.background import BackgroundTask


def export_report(*, report_id: int, format_name: str) -> None:
    print(f"{report_id}.{format_name}")


task = BackgroundTask(export_report, report_id=8, format_name="csv")
```

The implementation uses `functools.partial` so keyword arguments reach a callable executed by `run_in_executor`.


### Handle a failure at the execution boundary

```python
from orionis.background import BackgroundTask


def fail_delivery() -> None:
    raise RuntimeError("delivery unavailable")


async def run_delivery() -> None:
    try:
        await BackgroundTask(fail_delivery).run()
    except RuntimeError as error:
        print(str(error))
```

The task logs the failure, then the original `RuntimeError` remains available to the caller. In a collection, subsequent tasks are skipped.

## Configuration

The module consumes no Orionis configuration keys or environment variables. Executor sizing belongs to the running asyncio loop. Logging behavior comes from the normal Orionis logging configuration, not from this package.

## Integration with Orionis

`orionis.http.responses.Response` accepts a `BackgroundTask` in its `background` argument. ASGI and RSGI response adapters await `runBackground()` after buffered bodies, ordinary streams, files, empty responses, and HEAD framing are delivered. Orionis's registration and password-reset controllers use this mechanism to send mail outside the response's critical path.

The module uses the `Log` facade for success and failure records. It has no service provider or container binding of its own.

## Errors and edge cases

- Construction does not reject a non-callable; invoking it follows the synchronous path, logs the resulting `TypeError`, and re-raises it.
- Exceptions are never swallowed. A failing collection item prevents every later item from running.
- `asyncio.CancelledError` is a `BaseException`, not an `Exception`, so the logging handler does not intercept it.
- The callable style is classified once at construction. Replacing internals is unsupported.
- Ordinary response-delivery failures or stream disconnect paths can prevent background work from running. Use `orionis.queues` for durable or retryable work.
- A synchronous function returning an awaitable is supported: the function runs in the executor and the awaitable then runs on the event loop.

## Performance and concurrency

Synchronous functions run in the event loop's default executor and therefore do not occupy the loop thread while executing. Their concurrency limit and shutdown lifecycle belong to the loop. Async functions run normally and must yield control to permit concurrency.

`BackgroundTasks` is strictly sequential and creates no task group. Its public list is not protected against concurrent mutation; populate a collection before response delivery. A response adapter awaits background completion, so long-running tasks still consume worker capacity even though the client has received the response.

## Public API

### `BackgroundTask`

```text
BackgroundTask(func: Callable, *args: object, **kwargs: object)
```

The constructor stores the callable and arguments and classifies the callable once. It does not validate callability or execute work. Invoke an instance with `await task()` or `await task.run()`; both return `None`.

On success the task logs an info message containing the callable name. On failure it logs an error and re-raises the original exception. A callable object without `__qualname__` is identified by its class name.

### `BackgroundTasks`

```text
BackgroundTasks(tasks: Sequence[BackgroundTask] | None = None)
```

The constructor copies the supplied sequence into `tasks`; later changes to the source sequence do not affect the collection. `None` and an empty sequence create an empty collection.

#### `addTask(func, *args, **kwargs)`

Wraps the callable in `BackgroundTask`, appends it, and returns `None`. Passing another `BackgroundTasks` object is supported because collections themselves are async callable objects, enabling nested sequential groups.

#### `run()` and `__call__()`

`__call__` awaits stored tasks one by one. `run` is inherited from `BackgroundTask` and dispatches dynamically to the collection's `__call__`. Running an empty collection is a no-op.

### `IBackgroundTask`

The extension contract requires only `async run() -> None`. HTTP responses currently validate against `BackgroundTask`, so custom response tasks should normally subclass `BackgroundTask` rather than implementing the contract alone.

## Implementation reference for extensions

| Path | Responsibility |
|---|---|
| `task.py` | Callable detection, single-task execution, executor dispatch, and logging. |
| `tasks.py` | Ordered collection and `addTask` convenience method. |
| `contracts/task.py` | `IBackgroundTask` extension contract exposing async `run()`. |
| `__init__.py` | Re-exports `BackgroundTask` and `BackgroundTasks`. |

---

[Index](README.md) · [http](../../../http/docs/en/README.md) · [queues](../../../queues/docs/en/README.md) · [logging](../../../logging/docs/en/README.md)
