# Orionis Performance (`orionis.support.performance`)

> High-resolution stopwatch utility (`PerformanceCounter`) with matching synchronous and asynchronous APIs, plus `with`/`async with` context-manager support, for timing code blocks.
>
> 🇪🇸 Versión en español: [README.es.md](README.es.md)

`orionis.support.performance` provides a single, focused utility class —
`PerformanceCounter` — for measuring elapsed wall-clock time around a
block of code (a request handler, a console command, a benchmark, etc.).
It wraps `time.perf_counter()` behind a small, chainable API that works
identically whether the surrounding code is synchronous or `async`, and
exposes the elapsed duration in several common units. The framework's
own console kernel (`orionis.console.core.reactor.Reactor`) uses it to
report how long each executed command took.

---

## Table of contents

1. [Requirements](#requirements)
2. [Module overview](#module-overview)
3. [API reference](#api-reference)
   - [`PerformanceCounter`](#performancecounter-orionissupportperformancecounterperformancecounter)
   - [Contract (`IPerformanceCounter`)](#contract-iperformancecounter)
4. [Usage examples](#usage-examples)
5. [Performance and concurrency considerations](#performance-and-concurrency-considerations)
6. [Design notes](#design-notes)
7. [Compatibility notes](#compatibility-notes)

---

## Requirements

No extra installation is required beyond the framework itself:

```bash
uv add orionis
```

- **Python:** 3.14 or newer (the same minimum as the rest of the framework).
- **Dependencies:** none beyond the Python standard library (`time`,
  `typing.Self`).

## Module overview

| Type | File | Base class | Purpose |
|---|---|---|---|
| `PerformanceCounter` | [counter.py](../counter.py) | `IPerformanceCounter` (`ABC`) | Stopwatch object: `start()`/`stop()` (or their `async` counterparts `astart()`/`astop()`) record `time.perf_counter()` readings, and a family of `get*`/`aget*` methods convert the resulting elapsed time into seconds, milliseconds, microseconds, or minutes. |

`PerformanceCounter` implements the `IPerformanceCounter` contract
(defined in `orionis/support/performance/contracts/counter.py`) and is
re-exported directly from the package:

```python
from orionis.support.performance import PerformanceCounter
```

---

## API reference

### `PerformanceCounter` (`orionis.support.performance.counter.PerformanceCounter`)

```python
PerformanceCounter() -> None
```

A `__slots__`-based object (`_start_time`, `_diff_time`,
`_is_async_mode`) with no constructor arguments. Every "start" and
"stop" method returns `self`, so calls can be chained; every "get"
method reads the elapsed time recorded by the last `start()`/`stop()`
(or `astart()`/`astop()`) cycle.

| Method | Signature | Description |
|---|---|---|
| `start` | `start() -> PerformanceCounter` | Records the current `time.perf_counter()` reading as the start time, clears the previous result and marks the instance as **synchronous** mode. Returns `self`. |
| `astart` | `astart() -> PerformanceCounter` *(async)* | Same as `start()`, but marks the instance as **asynchronous** mode. Returns `self`. |
| `stop` | `stop() -> PerformanceCounter` | Reads the clock and computes the elapsed time since `start()`. Returns `self`. Raises `RuntimeError` if the counter was started with `astart()` (use `astop()` instead) or `ValueError` if it was never started. |
| `astop` | `astop() -> PerformanceCounter` *(async)* | Records the end time and computes the elapsed time since `astart()`. Returns `self`. Raises `RuntimeError` if the counter was started with `start()` (use `stop()` instead). |
| `elapsedTime` | `elapsedTime() -> float` | Elapsed time in seconds since the last completed `start()`/`stop()` cycle. Raises `ValueError` if the counter has not been started and stopped. |
| `aelapsedTime` | `aelapsedTime() -> float` *(async)* | Async equivalent of `elapsedTime()`. Same `ValueError` behavior. |
| `getSeconds` / `agetSeconds` | `getSeconds() -> float` | Elapsed time in seconds — an alias for `elapsedTime()`/`aelapsedTime()`. |
| `getMilliseconds` / `agetMilliseconds` | `getMilliseconds() -> float` | Elapsed time in milliseconds (`elapsed * 1_000`). |
| `getMicroseconds` / `agetMicroseconds` | `getMicroseconds() -> float` | Elapsed time in microseconds (`elapsed * 1_000_000`). |
| `getMinutes` / `agetMinutes` | `getMinutes() -> float` | Elapsed time in minutes (`elapsed / 60`). |
| `restart` | `restart() -> PerformanceCounter` | Clears the end/elapsed readings and immediately records a new start time in **synchronous** mode. Returns `self`. |
| `arestart` | `arestart() -> PerformanceCounter` *(async)* | Same as `restart()`, but marks the instance as **asynchronous** mode. Returns `self`. |
| `__enter__` / `__exit__` | — | `with PerformanceCounter() as counter:` calls `start()` on enter and `stop()` on exit (including when the block raises). |
| `__aenter__` / `__aexit__` | — | `async with PerformanceCounter() as counter:` calls `astart()` on enter and `astop()` on exit (including when the block raises). |

All `get*`/`aget*` accessor methods (`elapsedTime`, `getSeconds`,
`getMilliseconds`, `getMicroseconds`, `getMinutes`, and their `a`-prefixed
counterparts) raise `ValueError` with the message *"Counter has not been
started and stopped properly."* if no completed measurement cycle
exists yet (i.e. `stop()`/`astop()` was never called after `start()`/
`astart()`).

### Contract (`IPerformanceCounter`)

`orionis/support/performance/contracts/counter.py` defines
`IPerformanceCounter` as an `abc.ABC` (`__slots__ = ()`) with
`@abstractmethod` declarations mirroring every public method of
`PerformanceCounter` (docstrings included, no implementation). It exists
so other modules — such as the console `Reactor` kernel, which receives
a `PerformanceCounter` through dependency injection typed as
`IPerformanceCounter` — can depend on the interface rather than the
concrete class.

---

## Usage examples

### Manual start/stop (synchronous)

```python
import time
from orionis.support.performance import PerformanceCounter

counter = PerformanceCounter()
counter.start()
time.sleep(0.05)
counter.stop()

print(f"{counter.getMilliseconds():.2f} ms")
print(f"{counter.elapsedTime():.4f} s")
```

### `with` context manager (synchronous)

```python
import time
from orionis.support.performance import PerformanceCounter

with PerformanceCounter() as counter:
    time.sleep(0.05)

print(f"Block took {counter.getSeconds():.4f} s")
```

### `async with` context manager (asynchronous)

```python
import asyncio
from orionis.support.performance import PerformanceCounter

async def main() -> None:
    async with PerformanceCounter() as counter:
        await asyncio.sleep(0.05)
    print(f"Block took {await counter.agetMilliseconds():.2f} ms")

asyncio.run(main())
```

### Reusing an instance with `restart()`

```python
import time
from orionis.support.performance import PerformanceCounter

counter = PerformanceCounter()
counter.start()
time.sleep(0.02)
counter.stop()
print(f"First pass: {counter.getMilliseconds():.2f} ms")

counter.restart()
time.sleep(0.04)
counter.stop()
print(f"Second pass: {counter.getMilliseconds():.2f} ms")
```

### Mixing sync/async modes raises `RuntimeError`

```python
import asyncio
from orionis.support.performance import PerformanceCounter

async def main() -> None:
    counter = PerformanceCounter()
    await counter.astart()
    try:
        counter.stop()  # started with astart(), must be stopped with astop()
    except RuntimeError as exc:
        print(exc)  # "Cannot use stop() after astart(). Use astop() instead."

asyncio.run(main())
```

---

## Performance and concurrency considerations

- `PerformanceCounter` uses `time.perf_counter()`, a monotonic,
  high-resolution clock intended specifically for measuring short
  durations — it is **not** wall-clock/calendar time and its absolute
  value has no meaning outside of computing differences between two
  readings from the same process.
- The class is `__slots__`-based (`_start_time`, `_diff_time`,
  `_is_async_mode`), so each instance has a small, fixed
  memory footprint with no `__dict__` overhead.
- The `a`-prefixed methods (`astart`, `astop`, `aelapsedTime`,
  `agetSeconds`, `agetMilliseconds`, `agetMicroseconds`, `agetMinutes`,
  `arestart`) are `async def` for API symmetry and to integrate cleanly
  with `async`/`await` call sites (like `async with`), but they perform
  **no actual asynchronous I/O or awaiting internally** — timing itself
  is always a synchronous `time.perf_counter()` call.
- `start()`/`stop()` and `astart()`/`astop()` are mutually exclusive on
  the same instance: mixing them (e.g. `astart()` followed by `stop()`)
  raises `RuntimeError` instead of silently producing an incorrect
  reading. `restart()`/`arestart()` reset this mode flag along with the
  timing state.
- A `PerformanceCounter` instance is **not thread-safe** and is not
  meant to be shared across concurrent tasks/threads: it holds a single
  mutable start/elapsed state, so measuring multiple overlapping
  operations requires one instance per operation (or reusing one
  instance sequentially via `restart()`).
- All operations are `O(1)` and use fixed-size state. Clock reads and
  arithmetic produce float objects, and each awaited `async def` call
  creates a coroutine object; there is no iteration or external I/O.

## Design notes

- **Fluent/chainable API**: `start()`, `stop()`, `astart()`, `astop()`,
  `restart()`, and `arestart()` all return `self`, allowing patterns
  like `PerformanceCounter().start()` in a single expression.
- **Explicit sync/async modes**: rather than silently supporting mixed
  usage, `PerformanceCounter` tracks `_is_async_mode` and raises
  `RuntimeError` on mismatched `stop`/`astop` calls — this makes
  incorrect usage fail fast instead of producing a misleading duration.
- **Context manager support (both flavors)**: `__enter__`/`__exit__` and
  `__aenter__`/`__aexit__` are implemented directly on the class (rather
  than via `contextlib`), always stopping the counter on exit — even if
  the `with`/`async with` block raises an exception — mirroring
  `contextlib.ExitStack`-style guaranteed cleanup.
- **Interface-first design**: `IPerformanceCounter` (an `abc.ABC` with
  only `@abstractmethod` declarations) lets other framework components,
  such as `orionis.console.core.reactor.Reactor`, depend on and receive
  the counter via dependency injection using the interface type rather
  than the concrete `PerformanceCounter` class.
- **`__slots__` for a value-like object**: as a small, frequently
  instantiated timing utility, `PerformanceCounter` avoids the per-instance
  `__dict__` by declaring `__slots__` for its three attributes.

## Compatibility notes

- Requires **Python 3.14+**, consistent with the rest of the `orionis`
  framework (`requires-python = ">=3.14"` in `pyproject.toml`).
- No third-party dependencies; only uses `time` and `typing.Self` from
  the standard library.
- No platform-specific behavior; `time.perf_counter()` is available and
  behaves consistently across the platforms Python itself supports.
- Used internally by `orionis.console.core.reactor.Reactor` (the
  framework's console kernel) to time command execution, but the module
  itself has no dependency on the rest of the framework beyond its own
  contract.
