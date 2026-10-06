# orionis.encrypter

> `orionis.encrypter` provides synchronous, application-keyed AES encryption and decryption with portable Base64 JSON envelopes.

## Overview

The module exposes one concrete package-level class, `Encrypter`, and the internal `IEncrypter` contract. It supports AES-128 and AES-256 in CBC or GCM mode. Every encrypted value carries its IV, ciphertext, optional GCM tag, and cipher identifier inside a Base64-encoded JSON envelope.

Applications normally use the pinned `Crypt` facade. Direct construction is useful for extensions and isolated tests when an application-like object can provide `app.key` and `app.cipher`.

## Requirements

- Python 3.14 or newer.
- `cryptography>=46.0.3,<47.0.0` and `msgspec>=0.20.0,<0.21.0`, installed by Orionis.
- An exact 16-byte key for AES-128 or 32-byte key for AES-256.
- A booted Orionis container when using the `Crypt` facade.

## Quick start

```python
from orionis.encrypter import Encrypter


class App:
    def config(self, name: str):
        return {
            "app.key": b"k" * 32,
            "app.cipher": "AES-256-GCM",
        }[name]


crypt = Encrypter(App())
token = crypt.encrypt("private value")
assert token != "private value"
assert crypt.decrypt(token) == "private value"
print("round trip ok")
```

Validation: **Executed successfully** on CPython 3.14.6; output was `round trip ok`.

## Core concepts

### Cipher selection

One `Encrypter` instance is fixed to the configured cipher and key. Supported identifiers are `AES-128-CBC`, `AES-256-CBC`, `AES-128-GCM`, and `AES-256-GCM`. A payload can only be decrypted by an instance configured with the same cipher and key.

### Envelope format

`encrypt()` UTF-8 encodes the text, creates a fresh random IV, encrypts it, serializes `iv`, `value`, `tag`, and `cipher` as JSON, then Base64-encodes the JSON. Binary fields are themselves Base64 strings. The format is transportable text, not a hash.

### Authentication

GCM authenticates the ciphertext and rejects modification through its 16-byte tag. CBC uses PKCS7 padding but this implementation does not add a MAC; prefer GCM for new security-sensitive data. Never expose, log, or commit the application key.

## Module structure

| Path | Responsibility |
|---|---|
| `encrypter.py` | Key/cipher validation, envelope encoding, AES-CBC and AES-GCM operations. |
| `contracts/encrypter.py` | `IEncrypter` abstract `encrypt`/`decrypt` interface. |
| `provider.py` | Singleton binding and synchronous facade pinning. |
| `__init__.py` | Public `Encrypter` export. |

## Public API

### `Encrypter(app)`

Reads `app.key` as bytes and `app.cipher` as a supported string. Construction raises `ValueError` for an unsupported cipher or an incorrect key length. Constants such as `SUPPORTED_CIPHERS`, key sizes, IV sizes, and tag size describe the accepted wire format.

### `encrypt(plaintext: str) -> str`

Accepts a non-empty string and returns a new Base64 envelope. A random IV means encrypting the same plaintext twice should produce different tokens. Invalid input raises `TypeError` or `ValueError`; cryptographic failures are wrapped in `RuntimeError`.

### `decrypt(payload: str) -> str`

Decodes and validates the envelope, requires its cipher to match configuration, checks IV/tag sizes, decrypts, and UTF-8 decodes the result. It rejects empty/non-string input, malformed envelopes, mismatched ciphers, bad padding, invalid tags, and authentication failures.

### `IEncrypter`

The contract declares only synchronous `encrypt` and `decrypt`. Import it from `orionis.encrypter.contracts` when typing a container-resolved dependency.

## Common workflows

### Encrypt application values

Use `Crypt.encrypt(value)` after application boot, persist the returned token as opaque text, and call `Crypt.decrypt(token)` only at the trust boundary that needs plaintext.

### Rotate a key or cipher

Old tokens do not decrypt under a new key or a different configured cipher. A safe rotation therefore needs a versioned key strategy or a controlled read-old/write-new migration before configuration changes.

### Test a service directly

Supply a small app double whose `config()` returns normalized bytes and a cipher string. This avoids global facade state and makes round-trip and failure cases deterministic except for token bytes.

## Examples

### Exercise every supported cipher

```python
from orionis.encrypter import Encrypter


class App:
    def __init__(self, cipher: str) -> None:
        size = 16 if cipher.startswith("AES-128") else 32
        self.values = {"app.key": b"k" * size, "app.cipher": cipher}

    def config(self, name: str):
        return self.values[name]


for cipher in sorted(Encrypter.SUPPORTED_CIPHERS):
    service = Encrypter(App(cipher))
    assert service.decrypt(service.encrypt("Orionis")) == "Orionis"

print("four ciphers ok")
```

Validation: **Executed successfully** on CPython 3.14.6; output was `four ciphers ok`.

### Inspect envelope metadata

```python
import base64
import json
from orionis.encrypter import Encrypter


class App:
    def config(self, name: str):
        return {"app.key": b"k" * 32, "app.cipher": "AES-256-GCM"}[name]


token = Encrypter(App()).encrypt("inspect me")
envelope = json.loads(base64.b64decode(token))
assert envelope["cipher"] == "AES-256-GCM"
assert envelope["tag"] is not None
print(sorted(envelope))
```

Validation: **Executed successfully** on CPython 3.14.6; fields were `cipher`, `iv`, `tag`, and `value`.

### Reject a modified GCM value

```python
import base64
import json
from orionis.encrypter import Encrypter


class App:
    def config(self, name: str):
        return {"app.key": b"k" * 32, "app.cipher": "AES-256-GCM"}[name]


crypt = Encrypter(App())
envelope = json.loads(base64.b64decode(crypt.encrypt("sealed")))
changed = bytearray(base64.b64decode(envelope["value"]))
changed[0] ^= 1
envelope["value"] = base64.b64encode(changed).decode()
tampered = base64.b64encode(json.dumps(envelope).encode()).decode()

try:
    crypt.decrypt(tampered)
except RuntimeError:
    print("tampering rejected")
```

Validation: **Executed successfully** on CPython 3.14.6; GCM authentication rejected the change.

### Use the application facade

```python
from orionis.support.facades import Crypt

token = Crypt.encrypt("private value")
plaintext = Crypt.decrypt(token)
assert plaintext == "private value"
```

Validation: **Import-only** on CPython 3.14.6; calls require the application container and pinned facade.

## Configuration

`config/app.py` supplies the settings:

| Setting | Environment | Meaning |
|---|---|---|
| `app.cipher` | `APP_CIPHER` | One of the four supported AES identifiers; default is `AES-256-CBC`. |
| `app.key` | `APP_KEY` | Raw text or `base64:`-prefixed key with exactly the cipher's required byte length. |

The validated application config converts the key to bytes. If no key is configured, `SecureKeyGenerator` creates a random Laravel-compatible `base64:` value, persists it through `Env.set`, and normalizes it. Persist a stable production key: losing it makes existing ciphertext unrecoverable.

## Integration with Orionis

`EncrypterProvider` is a core, non-deferred provider. It binds `IEncrypter` to `Encrypter` as a singleton, then pins `Crypt` during async boot so synchronous calls do not return a deferred dispatcher.

`Stringable.encrypt/decrypt`, registration flows, view globals, and MCP state use the service or facade. Dependency-injected code can request `IEncrypter`; ordinary application code can import `Crypt` from `orionis.support.facades`.

## Errors and edge cases

- Empty plaintext and payload strings raise `ValueError`; non-strings raise `TypeError`.
- Unsupported ciphers and wrong key sizes fail at construction.
- Invalid outer Base64/JSON or typed fields raise `ValueError`.
- Payload cipher mismatch and invalid IV size raise `ValueError` before decryption.
- GCM requires a 16-byte tag; authentication failures surface as wrapped `RuntimeError`.
- CBC rejects empty ciphertext and invalid PKCS7 padding, but it does not authenticate metadata or ciphertext.
- The plaintext must be valid UTF-8 text; this API is not a raw-byte encryption interface.

## Performance and concurrency

The implementation is synchronous and CPU-bound. GCM caches one immutable `AESGCM` object per service; CBC creates a cipher context per call. Payload encoding uses reusable `msgspec` structures/decoder. Each call keeps data local and obtains a fresh IV from `os.urandom`, so the singleton can serve concurrent callers without mutable per-operation state.

Token size includes JSON and two Base64 layers plus IV/tag overhead. Avoid using encryption as a streaming format for large files; use a purpose-built streaming scheme and authenticated mode instead.

## Compatibility

Orionis declares Python 3.14+, `cryptography` 46.x, and `msgspec` 0.20.x. Validation used CPython 3.14.6 on Windows. The envelope records its exact cipher but not a key version; all readers must share compatible configuration.

## Verification notes

Validation used CPython 3.14.6. Package exports, contract, implementation, provider, facade, app configuration, key normalization, integrations, and `tests/encrypter` were inspected. All 61 encrypter tests passed through the Orionis runner. Four direct programs were executed successfully, and the facade example was import-validated only because it requires application boot.
