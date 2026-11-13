# Async execution

Loop centralizes loop creation, callable dispatch, and synchronous bridges. Start by deciding whether your code already runs inside an event loop: that determines which operation to use.

## Learning path

1. [Connecting synchronous and asynchronous code](async-execution.md): prerequisites, progressive usage, configuration, integration, failures, and public reference.

The examples use `Loop` directly without booting an application. Distinguish borrowed loops from owned loops before choosing how to close resources.

Related: [background](../../../background/docs/en/README.md) · [foundation](../../../foundation/docs/en/README.md)
