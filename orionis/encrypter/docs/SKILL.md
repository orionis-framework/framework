---
name: "orionis-encrypter"
description: >-
  Use when a task involves understanding, integrating, or troubleshooting
  the orionis.encrypter module, AES-CBC/AES-GCM payloads, IEncrypter service
  resolution, or Crypt facade calls. Consult the bundled documentation and
  inspect the local implementation to select verified APIs, respect behavioral
  constraints, and validate proposed usage.
---

# Work with orionis.encrypter

## Locate the implementation

Read [README.md](./README.md) or [README.es.md](./README.es.md) according to the
task's language. Use [module structure](./README.md#module-structure) to locate
the five Python files. Locate the module one level above this file's `docs/`
directory; do not assume another checkout, an installed copy or a differently
named module.

Inspect [Encrypter](../encrypter.py), [IEncrypter](../contracts/encrypter.py) and
[EncrypterProvider](../provider.py) before proposing usage or explaining errors.
Treat implementation as evidence; keep observed behavior distinct from
annotations and [docstring discrepancies](./README.md#docstring-discrepancies).

## Select verified APIs

Use `from orionis.encrypter import Encrypter` for direct construction,
`from orionis.encrypter.contracts import IEncrypter` for dependency injection,
and `from orionis.encrypter.provider import EncrypterProvider` only when working
on provider integration. Consult [API reference](./README.md#api-reference).

Use `from orionis.support.facades.encrypter import Crypt` for the adjacent
facade. Distinguish it from a module export. Do not import `_Payload`, private
helpers or imported cryptography names as new public Orionis APIs. Do not invent
rotation, streaming, TTL, HMAC, key-derivation or async encryption methods.

## Respect configuration and dispatch

- Read [requirements](./README.md#requirements). Supply raw byte keys of 16 or
  32 bytes and the exact matching cipher string; pass a cipher enum's `.value`
  for direct configuration. Do not pass an encoded `base64:` string directly
  to `Encrypter` or mistake its length check for a key-type validator.
- Read [Crypt integration](./README.md#crypt-integration). Await container
  resolution, then call service `encrypt` and `decrypt` synchronously. Use
  `await app.boot()` for headless eager startup when a real application is
  appropriate. Do not assume that `create()` or `make(IEncrypter)` pins Crypt.
- Await an unpinned facade dispatcher only after application creation. Call
  pinned `Crypt.encrypt` / `decrypt` without `await`; their strings are not
  awaitable. Preserve the provider's eager/core role for synchronous consumers.
- Check actual Stringable results before chaining: this implementation returns
  plain strings through Crypt despite the consumer's Stringable annotations.
- Do not mutate public `key` / `cipher` to switch modes or rotate keys. Their
  assignment does not rebuild `_is_gcm` / `_aesgcm`. Build independent,
  consistently configured instances for application-level reciphering.

## Diagnose payloads and errors

Consult [payload format](./README.md#payload-format) and
[error stages](./README.md#error-stages). Check input type and emptiness, typed
JSON fields, inner decoding, exact cipher match and IV size before attributing
a failure to the crypto backend.

Handle input `TypeError`, pre-validation `ValueError`, and cryptographic-stage
`RuntimeError` separately. Inspect chained causes without requiring stable
dependency messages. Missing or invalid GCM tags surface as RuntimeError on the
public path; do not invent EncryptionError or DecryptionError classes.

Do not treat successful CBC decryption as authentication. CBC has no MAC;
GCM uses a 16-byte tag and no additional authenticated data. Do not claim strict
base64, rejection of unknown JSON fields, nonce uniqueness or replay protection.
Use [actual error examples](./README.md#handling-actual-errors) for a local,
deterministic ciphertext-tampering check rather than random replacement data.

## Validate within scope

Read [compatibility notes](./README.md#compatibility-notes) and verify the actual
interpreter and dependency versions against project metadata. Keep the declared
Python 3.14+ floor separate from the versions tested or locked.

Extract complete scripts from [usage examples](./README.md#usage-examples).
Check syntax, then local import origins, then execute each in a fresh process.
Use temporary working roots before framework imports and application defaults;
do not load real credentials or services. Suppress bytecode, restore the working
directory, and close logging handlers before temporary cleanup on Windows.
Record success, failure or non-execution separately for each example.

When an explicit code-change request authorizes normal repository test output,
use the existing commands from the repository root in PowerShell:

```powershell
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe -B reactor test --start-dir="tests/encrypter" --verbosity=2
.\.venv\Scripts\python.exe -B -m ruff check --no-cache orionis/encrypter tests/encrypter
```

For documentation-only work with restricted writes, isolate a real application
root and use the native Orionis TestRunner on the existing tests; do not use a
plain unittest runner. Keep reports, configuration, logs and caches outside
the repository. Skip execution and state the precise limitation if startup
effects cannot be isolated. Verify nonzero discovery and raw failures/errors,
not just an exit code or printed summary. See
[verification and limitations](./README.md#verification-and-limitations).

Read [performance and concurrency](./README.md#performance-and-concurrency)
before sharing an instance. Synchronous crypto runs on the caller's thread;
module-level decoder reuse and singleton pinning do not establish cross-thread
safety, particularly with writable fields. Do not add unsupported guarantees.

Modify framework code only for an explicit change request and only within its
authorized scope. Report missing source, dependencies, execution capability or
conflicting evidence instead of substituting another module or silently changing
the implementation. Treat this file as a repository entry point with local
references, not automatic skill installation or registration.
