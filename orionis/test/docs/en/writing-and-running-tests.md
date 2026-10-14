# Writing and running tests

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

## Common workflows

### Test resolved dependencies

Annotate the test method like any application-invoked callable. Orionis resolves the parameter when the runner invokes the case:

```python
from uuid import uuid4
from orionis.cache.contracts.cache_manager import ICacheManager
from orionis.test import TestCase

class TestHealth(TestCase):
    async def testCache(self, cache: ICacheManager) -> None:
        key = f"tests:health:{uuid4().hex}"
        try:
            await cache.set(key, "ok", ttl=10)
            self.assertEqual(await cache.get(key), "ok")
        finally:
            await cache.delete(key)
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

## Isolate test state

Each case uses an isolated event loop; the application, its singletons, and external data may remain shared. The base does not promise database rollback, cache flushing, or a separate scope per method. Use temporary or memory stores, unique keys, and explicit cleanup. The cache example deletes its key in `finally`. To resolve a scoped service, enter `async with app.beginScope()` and resolve it inside that block; do not request it as an argument before the scope exists. The `setUp` and `asyncSetUp` hooks retain their unittest signatures and do not receive automatic injection.

## Evidence and next steps

[case.py](../../cases/case.py) · [engine.py](../../core/engine.py) · [test_example.py](../../../../tests/test_example.py)

[Return to the module index](README.md).
