# Tasks after the response

A background task belongs to the serving process and runs after response delivery. Use it for short side effects whose loss is acceptable; the queues module covers work requiring persistence and retries.

## Learning path

1. [Running actions after responding](response-tasks.md): prerequisites, progressive usage, configuration, integration, failures, and public reference.

The response construction examples defer execution. To run their background tasks, use a booted Orionis application with the providers required by the logger facade.

Related: [http](../../../http/docs/en/README.md) · [queues](../../../queues/docs/en/README.md) · [logging](../../../logging/docs/en/README.md)
