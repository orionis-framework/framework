# Tasks after the response

A background task belongs to the serving process and runs after response delivery. Use it for short side effects whose loss is acceptable; the queues module covers work requiring persistence and retries.

## Learning path

1. [Running actions after responding](response-tasks.md): prerequisites, progressive usage, configuration, integration, failures, and public reference.

Isolated examples use minimal application objects; facades require an initialized Orionis application and its providers. Source and contracts determine the documented capabilities.

Related: [http](../../../http/docs/en/README.md) · [queues](../../../queues/docs/en/README.md) · [logging](../../../logging/docs/en/README.md)
