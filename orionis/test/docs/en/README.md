# Application testing

## Overview

`orionis.test` is Orionis's asynchronous testing layer on top of Python's `unittest`. It supplies an application-aware `TestCase`, a configurable discovery and execution engine, structured test results, Rich console reporting, and an in-process MCP client that exercises the real JSON-RPC serialization and dispatcher path.

The package is designed for framework and application tests that need Orionis dependency injection without abandoning familiar `unittest` assertions, fixtures, skips, expected failures, or subtests.

## Requirements

- Python 3.14 or newer.
- A normal Orionis application layout when tests require application services.
- Test modules named by the configured file glob and methods named by the configured method glob.
- An MCP server declaration and bootable application container for MCP integration tests.

## Module learning path

- [Testing MCP tools in process](mcp-testing.md)
- [Results, configuration, and reference](results-and-reference.md)
- [Writing and running tests](writing-and-running-tests.md)

Continue with: [foundation](../../../foundation/docs/en/README.md) · [mcp](../../../mcp/docs/en/README.md).

Examples that require bootstrap, a request, or external services state that context. Verification for this reconstruction is distinct from historical notes; a production integration is not assumed to have been executed.
