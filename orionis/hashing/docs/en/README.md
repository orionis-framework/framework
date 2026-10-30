# Passwords

A password workflow consists of validation, hashing, storing the result, and verification on the next login. Cost policy and algorithm migration belong to the same workflow.

## Learning path

1. [Storing, verifying, and upgrading passwords](password-storage.md): prerequisites, progressive usage, configuration, integration, failures, and public reference.

Isolated examples use minimal application objects; facades require an initialized Orionis application and its providers. Source and contracts determine the documented capabilities.

Related: [auth](../../../auth/docs/en/README.md) · [encrypter](../../../encrypter/docs/en/README.md)

## Bounded execution and performance

Argon2 and bcrypt now share a dedicated bounded executor: two active calls and 14 queued calls per process, separate from the loop's default executor. Cryptographic parameters are unchanged. `WorkQueueFullError` reports overload explicitly; apply the application's admission/response policy rather than lowering the hashing cost. Running native work retains capacity through cancellation until it completes.

For a different host budget, inject `executor=BoundedExecutor(max_workers, max_pending=...)` into either hasher; sharing that instance preserves a combined budget. The caller owns and closes a custom pool. Budget Argon2 memory and native lanes per active operation, and account for multiple server processes.
