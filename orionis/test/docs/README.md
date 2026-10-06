# orionis.test

> API reference derived from the current implementation.

## Table of contents

- Requirements
- Functional overview
- Module structure
- API reference
- Usage examples
- Design characteristics
- Performance and concurrency
- Compatibility notes
- Verification and limitations

## Requirements

Python 3.14 or newer, as declared by pyproject.toml.

## Functional overview

The orionis.test initializer exports 3 public symbols. This reference uses __all__, export routes, and current source files as evidence.

## Module structure

| Path | Responsibility |
| --- | --- |
| ../__init__.py | Defines package exports. |
| orionis.test/ | Implementations and subpackages for those exports. |

## API reference

| Symbol | Verified import | Source | Declaration | Observed behavior |
| --- | --- | --- | --- | --- |
| McpTestClient | from orionis.test import McpTestClient | [clients/mcp.py](../clients/mcp.py) | McpTestClient | Open scopes on the supplied container; never create a parallel application. |
| McpTestClient.stream | from orionis.test import McpTestClient | [clients/mcp.py](../clients/mcp.py) | async def stream(self, method: str, params: dict[str, object] / None, *, meta: dict[str, object] / None, request_id: str / int) -> AsyncIterator[dict[str, object]] | Keep the existing application's scope alive through the entire stream. Parameters ---------- method : str Value supplied for ``method``. params : dict[str, object] / None Parameters decoded for the requested operation. meta : dict[str, object] / None Value supplied for ``meta``. request_id : str / int Value supplied for ``request_id``. Yields ------ dict[str, object] Each item produced by the documented iteration. |
| McpTestClient.request | from orionis.test import McpTestClient | [clients/mcp.py](../clients/mcp.py) | async def request(self, method: str, params: dict[str, object] / None, *, meta: dict[str, object] / None, request_id: str / int) -> McpTestResponse | Collect a finite exchange; use stream() for subscriptions. Parameters ---------- method : str Value supplied for ``method``. params : dict[str, object] / None Parameters decoded for the requested operation. meta : dict[str, object] / None Value supplied for ``meta``. request_id : str / int Value supplied for ``request_id``. Returns ------- McpTestResponse Result of the operation described above. |
| McpTestClient.tool | from orionis.test import McpTestClient | [clients/mcp.py](../clients/mcp.py) | async def tool(self, name: str, arguments: dict[str, object] / None) -> McpTestResponse | Invoke a tool through JSON-RPC input and output bytes. Parameters ---------- name : str Value supplied for ``name``. arguments : dict[str, object] / None Arguments supplied for this operation. Returns ------- McpTestResponse Result of the operation described above. |
| McpTestResponse | from orionis.test import McpTestResponse | [clients/mcp.py](../clients/mcp.py) | McpTestResponse | Decoded result and notifications from a complete wire round trip. |
| McpTestResponse.assertOk | from orionis.test import McpTestResponse | [clients/mcp.py](../clients/mcp.py) | def assertOk(self) -> None | Require a successful protocol and tool result. Returns ------- None Complete the documented operation without returning a value. |
| McpTestResponse.assertTextContains | from orionis.test import McpTestResponse | [clients/mcp.py](../clients/mcp.py) | def assertTextContains(self, text: str) -> None | Check returned tool text without bypassing response serialization. Parameters ---------- text : str Value supplied for ``text``. Returns ------- None Complete the documented operation without returning a value. |
| TestCase | from orionis.test import TestCase | [cases/case.py](../cases/case.py) | TestCase | Exported public constant or alias. |
| TestCase.setMethodPattern | from orionis.test import TestCase | [cases/case.py](../cases/case.py) | def setMethodPattern(cls, pattern: str) -> None | Set the method pattern for identifying test methods. Parameters ---------- pattern : str The glob pattern to match test method names (e.g., "test*"). Returns ------- None This method stores the compiled pattern in the current context and returns None. |
| TestCase.mcp | from orionis.test import TestCase | [cases/case.py](../cases/case.py) | async def mcp(self, server: type[Server] / CompiledMcpServer, config: McpConfig / None, *, app: IContainer / None) -> McpTestClient | Create an MCP client using the test runner's application. Parameters ---------- server : type[Server] / CompiledMcpServer Server declaration or compiled snapshot to exercise. config : McpConfig / None, optional Client limits; use MCP defaults when omitted. app : IContainer / None, optional Explicit container for isolated tests; otherwise use the application already booted by the Orionis test runner. Returns ------- McpTestClient In-process client with independent request scopes and event state. Raises ------ RuntimeError If no container is supplied and the application is not booted. |

## Usage examples

    from orionis.test import McpTestClient

The import path matches the API table. Import status: executed successfully under Python 3.14.3.

## Design characteristics

The package uses an explicit public surface. Private names are excluded; declarations link to their concrete owner.

## Performance and concurrency

No uniform guarantee is declared at package level. Inspect each linked file for I/O, coroutines, caches, locks, and shared state.

## Compatibility notes

Declared minimum: Python 3.14. Validation used Python 3.14.3. Dependency bounds are in pyproject.toml.

## Verification and limitations

Python files were analysed and exports verified. Failures from dependencies, callbacks, I/O, or configuration may propagate and are not presented as exhaustive.
