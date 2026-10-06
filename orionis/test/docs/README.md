# orionis.test

> `orionis.test` extends `unittest` with Orionis dependency injection, async execution, structured results, Rich reporting, and in-process MCP testing.

## Overview

`orionis.test` is Orionis's asynchronous testing layer on top of Python's `unittest`. It supplies an application-aware `TestCase`, a configurable discovery and execution engine, structured test results, Rich console reporting, and an in-process MCP client that exercises the real JSON-RPC serialization and dispatcher path.

The package is designed for framework and application tests that need Orionis dependency injection without abandoning familiar `unittest` assertions, fixtures, skips, expected failures, or subtests.

## Requirements

- Python 3.14 or newer.
- A normal Orionis application layout when tests require application services.
- Test modules named by the configured file glob and methods named by the configured method glob.
- An MCP server declaration and bootable application container for MCP integration tests.

## Quick start

```python
from orionis.test import TestCase

class TestArithmetic(TestCase):
    async def testAddition(self) -> None:
        self.assertEqual(2 + 2, 4)
```

Run the suite from the project root:

```powershell
python reactor test
python reactor test --start-dir tests/unit --no-panel --verbosity 1
```

## Core concepts

### Application-aware cases

`TestCase` extends `unittest.IsolatedAsyncioTestCase`. At construction it wraps only the selected test method—not lifecycle hooks—and executes that method through `Application.invoke()`. This gives test methods the same automatic dependency resolution as application callables. Sync and async test methods are both accepted by the application invocation path.

Each case gets an isolated event loop. The slow-callback threshold is set to one second while asyncio debug behavior remains active. The method-name matcher is held in a `ContextVar`, so concurrent discovery contexts do not overwrite one another.

### Discovery and execution

`TestingEngine` walks the configured directory recursively, including directories without `__init__.py`, loads matching files, and filters individual methods. It creates a fresh suite for every run and executes the synchronous `unittest` runner in an executor so the caller's event loop is not blocked.

### Structured results

`TestResultProcessor` converts successes, failures, errors, skips, expected failures, unexpected successes, and subtest outcomes into `TestResult` entities. A result records status, timing, location, documentation, exception details, traceback, and nearby source code. Optional JSON caching serializes these entities under `storage/framework/cache/testing`.

### Protocol-level MCP tests

`McpTestClient` compiles a server once, sends encoded JSON-RPC messages through `McpDispatcher`, and creates a fresh container scope for each request or stream. `McpTestResponse` exposes the decoded final message plus collected notifications and concise assertions for success and returned text.

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

## Common workflows

### Test resolved dependencies

Annotate the test method like any application-invoked callable. Orionis resolves the parameter when the runner invokes the case:

```python
from orionis.cache.contracts.cache_manager import ICacheManager
from orionis.test import TestCase

class TestHealth(TestCase):
    async def testCache(self, cache: ICacheManager) -> None:
        await cache.put("health", "ok", seconds=10)
        self.assertEqual(await cache.get("health"), "ok")
```

### Assert an MCP response

```python
from orionis.test import McpTestResponse

response = McpTestResponse({
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "content": [{"type": "text", "text": "Hello, Ada"}],
        "isError": False,
    },
})
response.assertOk()
response.assertTextContains("Ada")
assert response.notifications == ()
```

### Inspect a structured result

```python
from orionis.test.entities.result import TestResult
from orionis.test.enums.status import TestStatus

result = TestResult(
    id="case-1",
    name="tests.unit.TestUsers.testCreate",
    status=TestStatus.PASSED,
    execution_time=0.012,
)

payload = result.toDict()
assert payload["status"] == "PASSED"
assert payload["execution_time"] == 0.012
```

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

### Exercise a real MCP tool

```python
from orionis.mcp import Server, Tool
from orionis.test import TestCase

class GreetingServer(Server):
    tools = [Tool(name="hello", handler=lambda name: f"Hello, {name}")]

class TestGreetingServer(TestCase):
    async def testHello(self) -> None:
        client = await self.mcp(GreetingServer)
        response = await client.tool("hello", {"name": "Ada"})
        response.assertOk()
        response.assertTextContains("Hello, Ada")
```

## Configuration

The `testing` configuration entity reads these environment variables:

| Environment variable | Default | Meaning |
| --- | --- | --- |
| `TESTING_VERBOSITY` | `2` | `0` silent, `1` compact, `2` detailed. |
| `TESTING_FAIL_FAST` | `False` | Stop after the first failure or error. |
| `TESTING_START_DIR` | `tests` | Discovery root. |
| `TESTING_FILE_PATTERN` | `test_*.py` | File glob. |
| `TESTING_METHOD_PATTERN` | `test*` | Method glob. |
| `TESTING_CACHE_RESULTS` | `False` | Persist structured results as JSON. |

CLI arguments override the corresponding configured values. `--no-panel` suppresses the Rich start and summary panels independently of per-test verbosity.

## Integration with Orionis

`TestingProvider` binds `ITestingEngine` as a singleton and pins the `Test` facade at boot. The `reactor test` command resolves that engine, applies command-line overrides, runs it, and derives the process status from the returned structured results.

`TestCase.mcp()` reuses the already booted application by default. Pass `app=` only when a test deliberately owns another compatible container. This prevents an MCP test client from silently creating a parallel application with different bindings.

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

## Verification notes

This documentation was regenerated against the current implementation and verified with CPython 3.14.6. Discovery under `tests/test` executed 178 results: 177 passed and one failed. The failure is `TestPublishGates.testPublicationRequiresEveryMandatoryGate` in the successful-gate subtest because its isolated fixture copies `PUBLISH.ps1` but not the `DOCS.ps1` script that `PUBLISH.ps1` now invokes; that repository test condition is outside this documentation-only scope. The first six Python examples were executed successfully; the dependency-injected MCP example was syntax-checked because it requires a booted application.
