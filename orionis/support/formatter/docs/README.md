# Orionis Formatter (`orionis.support.formatter`)

> Exception-to-dictionary serializer (`Parser` / `ExceptionParser`) that turns any Python exception into a structured, JSON-friendly dictionary with type, message, error code, and an annotated stack trace (including surrounding source code lines).
>
> 🇪🇸 Versión en español: [README.es.md](README.es.md)

`orionis.support.formatter` provides a small, focused utility for
converting a caught `Exception` into a structured `dict` suitable for
logging, HTTP error responses, or JSON serialization. It is used by the
framework's default HTTP error responses
(`orionis.http.default.responses`) to build consistent error payloads,
but has no dependency on the HTTP layer and can be used anywhere an
exception needs to be turned into structured data.

---

## Table of contents

1. [Requirements](#requirements)
2. [Module overview](#module-overview)
3. [API reference](#api-reference)
   - [`Parser`](#parser-orionissupportformatterserializerparser)
   - [`ExceptionParser`](#exceptionparser-orionissupportformatterexceptionsparserexceptionparser)
   - [Contract (`IExceptionParser`)](#contract-iexceptionparser)
4. [Usage examples](#usage-examples)
5. [Performance and concurrency considerations](#performance-and-concurrency-considerations)
6. [Design notes](#design-notes)
7. [Compatibility notes](#compatibility-notes)

---

## Requirements

No extra installation is required beyond the framework itself:

```bash
pip install orionis
```

- **Python:** 3.14 or newer (the same minimum as the rest of the framework).
- **Dependencies:** none beyond the Python standard library
  (`traceback`, `linecache`, `typing`).

## Module overview

| Type | File | Purpose |
|---|---|---|
| `Parser` | [serializer.py](../serializer.py) | Tiny factory: `Parser.exception(exception)` builds an `ExceptionParser` for the given exception. |
| `ExceptionParser` | [exceptions/parser.py](../exceptions/parser.py) | Does the actual work: captures the exception's traceback at construction time and exposes `toDict()` to render it as a plain dictionary. |
| `IExceptionParser` | [exceptions/contracts/parser.py](../exceptions/contracts/parser.py) | `typing.Protocol` describing the `toDict()` contract that `ExceptionParser` satisfies structurally. |

Typical flow: catch an exception → `Parser.exception(exc)` → `.toDict()`
→ pass the resulting `dict` to a logger, an HTTP error response, or
`json.dumps`.

---

## API reference

### `Parser` (`orionis.support.formatter.serializer.Parser`)

```python
class Parser:
    @staticmethod
    def exception(exception: Exception) -> ExceptionParser: ...
```

| Method | Signature | Description |
|---|---|---|
| `exception` | `exception(exception: Exception) -> ExceptionParser` *(staticmethod)* | Instantiates and returns an `ExceptionParser` wrapping the given `exception`. Accepts any `Exception` subclass. |

### `ExceptionParser` (`orionis.support.formatter.exceptions.parser.ExceptionParser`)

```python
ExceptionParser(exception: Exception) -> None
```

A `__slots__`-based object (`_cache`, `_error_code`, `_exc_type`, `_tb`)
that **eagerly** parses the exception's traceback metadata in
`__init__` — using `traceback.TracebackException.from_exception(exception,
capture_locals=False)` — so that calling `toDict()` later does not repeat
that work.

| Method | Signature | Description |
|---|---|---|
| `__init__` | `__init__(exception: Exception) -> None` | Captures the traceback (`traceback.TracebackException`, without local variables), resolves the exception type name, and reads an optional `code` attribute from the exception (`getattr(exception, "code", None)`) as the error code. |
| `toDict` | `toDict() -> dict[str, Any]` | Serializes the exception into a dictionary (see keys below). The result is computed once and cached internally; subsequent calls return the same `dict` object with no extra computation. |

`toDict()` returns a dictionary with these keys:

| Key | Type | Description |
|---|---|---|
| `error_type` | `str` | The exception class name (e.g. `"ValueError"`). |
| `error_message` | `str` | The formatted traceback text (`str(TracebackException)`, right-stripped). |
| `error_code` | `Any` | The value of the exception's `code` attribute if it has one, otherwise `None`. |
| `stack_trace` | `list[dict]` | One entry per stack frame, **most-recent-first** (the frame where the exception was raised comes first). |

Each `stack_trace` entry is a dict with these keys:

| Key | Type | Description |
|---|---|---|
| `id` | `int` | 1-based frame index, most-recent-first. |
| `filename` | `str` | Source file path, with `\` normalized to `/`. |
| `lineno` | `int` | Line number where the frame was executing (`0` if unknown). |
| `name` | `str` | Function/method name for the frame (`"<unknown>"` if unavailable). |
| `line_code` | `str \| None` | The single source line reported by the traceback for that frame. |
| `code` | `list[str]` | Up to 5 source lines of context around `lineno` (2 before, the line itself, 2 after), read via `linecache`. |
| `lines` | `list[int]` | The corresponding 1-based line numbers for the `code` entries. |
| `code_with_lines` | `list[str]` | `"{lineno}:{code}"` strings pairing each line number with its source text. |

`ExceptionParser` has two internal helper methods,
`_getSourceCode(filename, lineno)` and `_parseStack(stack)`, which are
implementation details used by `toDict()` and are not part of the
public contract.

### Contract (`IExceptionParser`)

```python
class IExceptionParser(Protocol):
    def toDict(self) -> dict[str, Any]: ...
```

Defined in `orionis/support/formatter/exceptions/contracts/parser.py`
as a `typing.Protocol` (structural typing) rather than an `abc.ABC` —
any object exposing a compatible `toDict()` method satisfies
`IExceptionParser` without needing to inherit from it explicitly.
`ExceptionParser` satisfies this protocol.

---

## Usage examples

### Basic exception serialization

```python
from orionis.support.formatter.serializer import Parser

try:
    1 / 0
except ZeroDivisionError as exc:
    payload = Parser.exception(exc).toDict()
    print(payload["error_type"])     # "ZeroDivisionError"
    print(payload["error_message"])  # formatted traceback text
    print(payload["error_code"])     # None (no `code` attribute)
    print(len(payload["stack_trace"]) > 0)  # True
```

### Custom exceptions with an error code

```python
from orionis.support.formatter.serializer import Parser

class AppError(Exception):
    def __init__(self, message: str, code: int) -> None:
        super().__init__(message)
        self.code = code

try:
    raise AppError("invalid payload", code=422)
except AppError as exc:
    payload = Parser.exception(exc).toDict()
    print(payload["error_code"])  # 422
```

### Using `ExceptionParser` directly

```python
import json
from orionis.support.formatter.exceptions.parser import ExceptionParser

try:
    raise RuntimeError("boom")
except RuntimeError as exc:
    parser = ExceptionParser(exc)
    as_json = json.dumps(parser.toDict())
    print(as_json)
```

### Inspecting the first stack frame

```python
from orionis.support.formatter.serializer import Parser

def inner() -> None:
    raise ValueError("nested failure")

try:
    inner()
except ValueError as exc:
    top_frame = Parser.exception(exc).toDict()["stack_trace"][0]
    print(top_frame["name"])      # "inner"
    print(top_frame["filename"])  # path to this script, with forward slashes
```

---

## Performance and concurrency considerations

- `ExceptionParser.__init__` does all the traceback parsing **eagerly**
  (up front), while `toDict()` itself just reads cached fields and
  builds the output dict — this trades a slightly higher construction
  cost for cheap, repeatable `toDict()` calls.
- `toDict()`'s result (`self._cache`) is memoized after the first call:
  the second and subsequent calls return the exact same `dict` object
  with no re-parsing. This is a simple, unlocked memoization — calling
  `toDict()` concurrently from multiple threads on the same
  `ExceptionParser` instance before the cache is populated could compute
  the dictionary more than once, but each computation is deterministic
  and produces an equal result, so there is no data corruption, only a
  possible redundant computation.
- `_getSourceCode` reads the surrounding source lines with one
  `linecache.getlines(filename)` call per frame. `linecache` caches file
  contents across calls within the process.
- `_parseStack` iterates the traceback's `StackSummary` directly in reverse
  to produce the most-recent-frame-first ordering without copying the
  stack into a second list. Frame IDs increase from 1 in that same order.
- `ExceptionParser` is `__slots__`-based, keeping the per-instance
  memory footprint small and fixed (`_cache`, `_error_code`,
  `_exc_type`, `_tb`).
- None of the classes in this module perform network or async I/O;
  `_getSourceCode` does perform synchronous file reads via `linecache`
  the first time each source file is accessed within the process.

## Design notes

- **Factory + worker split**: `Parser` is a minimal static factory
  (`Parser.exception(...)`) that exists purely to provide a short,
  descriptive entry point; all the real logic lives in
  `ExceptionParser`.
- **Eager parsing, lazy formatting**: capturing the traceback via
  `traceback.TracebackException.from_exception(..., capture_locals=False)`
  happens once in `__init__`; `capture_locals=False` deliberately avoids
  capturing local variables from every frame, which keeps the parser
  itself lightweight and avoids holding references to potentially large
  or sensitive local state.
- **`Protocol`-based contract**: `IExceptionParser` is a
  `typing.Protocol`, not an `abc.ABC` — a deliberate, more lightweight
  form of interface typing that relies on structural compatibility
  (having a matching `toDict()` method) rather than explicit
  inheritance, unlike the `abc.ABC`-based contracts used elsewhere in
  `orionis.support`.
- **Most-recent-frame-first ordering**: the `stack_trace` list is
  ordered so the frame where the exception was actually raised is
  first, which matches how error reports are typically read (the
  "cause" before the calling context).

## Compatibility notes

- Requires **Python 3.14+**, consistent with the rest of the `orionis`
  framework (`requires-python = ">=3.14"` in `pyproject.toml`).
- No third-party dependencies; only uses `traceback`, `linecache`, and
  `typing` from the standard library.
- No platform-specific behavior, aside from the standard `\\`-to-`/`
  path-separator normalization applied to `filename` in each stack
  frame entry (relevant mainly on Windows).
- Used internally by `orionis.http.default.responses` to build error
  response payloads, but the module itself has no dependency on the
  HTTP layer or any other part of the framework.
