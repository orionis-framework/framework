# Results, configuration, and reference

## Public API

The stable root imports are:

- `TestCase`: base class for Orionis application tests.
- `McpTestClient`: request, stream, and tool-call client for an MCP server.
- `McpTestResponse`: decoded response with `assertOk()` and `assertTextContains()`.

Framework integrations also expose:

- `TestingEngine`: fluent setters `setVerbosity`, `setFailFast`, `setStartDir`, `setFilePattern`, `setMethodPattern`, `withoutPanel`; plus `discover()` and async `run()`.
- `Test` facade: container proxy implementing the testing-engine contract.
- `TestResult`: immutable result entity with `toDict()` from `BaseEntity`.
- `TestStatus`: string enum for the four exported statuses.
- `TestRunner` and `TestResultProcessor`: lower-level `unittest` integration points.

## Errors and edge cases

- Running an application-aware case without a booted application causes dependency resolution to fail.
- Lifecycle methods (`setUp`, `tearDown`, class and async variants) are never wrapped as test methods.
- Import failures found by the loader are preserved in the suite instead of being removed by method filtering.
- `McpTestResponse.assertOk()` fails for JSON-RPC errors and tool results with `isError=True`.
- `request()` is for finite MCP exchanges; use `stream()` for subscriptions or other open-ended responses.
- Unexpected successes are failures, while expected failures are exported as skipped results.
- A failing subtest is represented in exported results and honors fail-fast behavior.
- JSON result filenames use second-resolution timestamps, so multiple cached runs in the same second target the same path.
- Rich's emoji output needs a Unicode-capable terminal; on legacy Windows code pages, set `PYTHONUTF8=1`.

## Performance and concurrency

Discovery creates a fresh `TestLoader` and suite each time. Execution is moved to the default thread executor, while each `TestCase` owns its asyncio loop. Method patterns are context-local, and result processor state is instance-local, allowing independent runs without shared verbosity or result lists.

MCP requests create independent application scopes and close stream bodies in `finally`. The compiled MCP server and in-memory event bus are retained by the client, so reuse one client when testing multiple operations against the same server while keeping each request scoped.

## Compatibility

The module targets Python 3.14+ and extends standard `unittest` protocols. Existing `unittest` assertions and decorators remain usable. Orionis method and file filters use shell-style glob semantics through `fnmatch`, not regular expressions. Rich is responsible only for presentation; `TestResult` objects remain the machine-readable result contract.

## Module structure

| Path | Responsibility |
| --- | --- |
| `cases/case.py` | Application-aware isolated async `TestCase`. |
| `clients/mcp.py` | In-process MCP client and response assertions. |
| `contracts/engine.py` | Testing-engine interface used by the container. |
| `core/engine.py` | Configuration, recursive discovery, execution, and JSON cache. |
| `entities/result.py` | Immutable structured `TestResult`. |
| `enums/status.py` | `PASSED`, `FAILED`, `ERRORED`, and `SKIPPED` statuses. |
| `executors/results.py` | `unittest.TestResult` adapter and Rich rendering. |
| `executors/runner.py` | Runner, start panel, and summary panel. |
| `provider.py` | Deferred service registration and `Test` facade pinning. |

## Examples

### Use the lower-level runner

```python
import unittest

from orionis.test.executors.runner import TestRunner

class PlainCase(unittest.TestCase):
    def testValue(self) -> None:
        self.assertTrue(True)

suite = unittest.defaultTestLoader.loadTestsFromTestCase(PlainCase)
result = TestRunner(verbosity=0, with_panel=False).run(suite)
assert result.wasSuccessful()
assert result.testsRun == 1
```

### Validate testing configuration

```python
from orionis.foundation.config.testing import Testing, VerbosityMode

config = Testing(
    verbosity=VerbosityMode.MINIMAL,
    fail_fast=True,
    start_dir="tests/unit",
    file_pattern="test_*.py",
    method_pattern="testCreate*",
    cache_results=False,
)

assert config.verbosity == 1
assert config.fail_fast is True
```

## Evidence and next steps

[result.py](../../entities/result.py) · [runner.py](../../executors/runner.py) · [results.py](../../executors/results.py)

[Return to the module index](README.md).
