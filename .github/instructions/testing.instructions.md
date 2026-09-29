---
name: "Orionis Tests"
description: "Use when writing, restructuring or running Orionis tests: the reactor test runner and its flags, mirror test layout, explicit stubs instead of unittest.mock, forcing defensive branches, measuring coverage with trace.Trace, and the lint rules that only apply under tests/."
applyTo: "tests/**"
---

# Testing

> The test module itself is documented in `orionis/test/docs/README.md`
> (`.es.md`): `TestCase`, `TestingEngine`, `TestRunner`, `TestResultProcessor`,
> `TestResult`, `TestStatus`, `TestingProvider` and the `testing.*` config keys.
> This file only covers how to write and run tests in this repo.

## Running the suite

The framework has its **own runner** — plain `unittest` fails because tests need the
booted application.

```powershell
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe reactor test --start-dir="tests/http" --verbosity=1
.\.venv\Scripts\python.exe reactor test --start-dir="tests/orm" --file-pattern="test_model.py" --verbosity=2
```

- Flags **always use `=`**. `--verbosity=2` shows the full traceback panel.
- `--file-pattern` is a **file name** pattern, not a path: passing a full file path to
  `--start-dir` silently yields "0 tests".
- Always use the repo venv (`.\.venv\Scripts\python.exe`); the global interpreter lacks
  the dependencies.
- Counting results with `Select-String "FAILED|ERRORED"` produces false positives (it is
  case-insensitive and matches test *names*) — use `-CaseSensitive`.

## Structure and style

- `tests/` **mirrors** the source tree: one file per module, with `contracts/`,
  `stores/`, `drivers/`, `entities/`, `enums/` subfolders as the module has them. Add a
  `test_package.py` for what `__init__.py` exports.
- **No `unittest.mock`.** Use explicit doubles with `__slots__` (`_StubApp`,
  `_RecordingEngine`, `_StubFacade`, ...). A `MagicMock` never raises `AttributeError`,
  so an attribute that is never assigned in production code passes unnoticed — that has
  hidden real bugs.
- `async def` only when the test actually awaits something.
- No tautological tests: one per `abstractmethod`, "the enum has member X",
  `assertIsInstance(CONST, str)` for every constant. Collapse contract tests into one
  surface test (`__abstractmethods__`) plus a signature-parity test comparing
  `list(signature.parameters)` (never the full `Signature`: contracts often use
  `from __future__ import annotations`, so their annotations are strings).
- `TestCase` extends `unittest.IsolatedAsyncioTestCase` and wraps each test method with
  `await Application.invoke(...)` → **test methods can declare extra parameters resolved
  by DI**.
- **Never** use `from __future__ import annotations` in test files whose helper classes
  are built by the container.

## Techniques that work here

- Swapping a module attribute (a facade, `DotEnv`, `sys.modules` entries, `sys.path`)
  must happen in `setUp`/`tearDown`, **not** inside the test body — SonarLint flags
  "use the monkeypatch fixture" for global mutation inside a test.
- For classes that are all classmethods with `ClassVar` state (e.g. `Loop`), create a
  disposable **subclass** per test instead of patching global state.
- Double-checked-locking branches are covered deterministically with a fake lock whose
  `__enter__` publishes the value that "won the race" — no threads, no sleeps.
- Private/mangled members can be called directly (`obj._Class__method`) because `SLF001`
  is in the per-file ignores for `tests/**`.
- Unreachable-from-the-API defensive branches are covered by constructing the internal
  object by hand (e.g. a `Binding` with an unsupported lifetime).
- Under the `reactor test` runner there is an **ambient container scope**, so container
  tests must neutralise it (`ScopedContext.setCurrentScope(None)` in `setUp`) or
  registrations leak between tests.
- Class-level shared state must be saved and restored in `setUp`/`tearDown`
  (model events, global scopes, `TestCase` method pattern).

## Coverage

There is no `coverage` package in the venv. Measure with stdlib `trace.Trace`:

- Start the tracer **before importing the test modules** (metaclasses and decorators run
  at class-definition time, i.e. at import).
- Call `threading.settrace(tracer.globaltrace)` too — anything running in
  `asyncio.to_thread` is invisible otherwise.
- Filter module-level lines with `ast` and only count **function-body** lines.
- Subtract docstring lines (they are not traced) and treat a statement as covered if any
  line in its `lineno..end_lineno` range ran (a multi-line `if (` traces the first
  subexpression).
- Python 3.14 reports pseudo-line `0` as missing — ignore it.

## Lint under `tests/**`

`tests/**` has its own ignores in `ruff.toml` (including `SLF001` and `DTZ001` — adding
`# noqa: DTZ001` there yields `RUF100`). Rules that still apply and bite:

| Rule | Situation | Fix |
|---|---|---|
| `S105`/`S106` | literal assigned to a `password=`/`token=`/`secret=` key or kwarg | module constant with a neutral name (`_CREDENTIAL`) |
| `EM101`/`TRY003` | `raise Error("literal")` inside a test | assign the message to a variable first |
| `B018` | bare attribute access inside `assertRaises` | `# noqa: B018` (a bare **call** does not trigger it → `RUF100`) |
| `ANN401` | direct `Any` annotation (`value: Any`) | use `object` (nested `dict[str, Any]` is fine) |
| `D200` | one-sentence docstring spread over three lines | collapse to one line or add the second paragraph |
| `ARG002` | unused argument named `_type_` | rename to `_target` |

## Before declaring a task done

Run the affected suites plus `python -m ruff check <paths>`, and state real numbers
(`tests/http 492/492`). Pre-existing unrelated failures must be called out as such, not
silently absorbed.
