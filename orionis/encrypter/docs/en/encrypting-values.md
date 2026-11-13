# Protecting and recovering application values

Encryption lets you recover sensitive text using a stable application key. Choose a format and plan key custody before storing the first tokens.

## Requirements

- Python 3.14 or newer.
- `cryptography>=50.0.1,<51.0` and `msgspec>=0.21.1`, installed by Orionis.
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

## Prepare secret storage

The API encrypts non-empty text. Serialize structured documents first and store the complete opaque token in a sufficiently wide column. IV, tag, JSON, and two Base64 layers increase its size; a field sized for the original text may be too small. The library adds no expiration, associated context, key identifier, or replay protection.

Configuration defaults to `AES-256-GCM`. Only `AES-128-GCM` and `AES-256-GCM` are accepted; unauthenticated CBC configuration and CBC envelopes are rejected. Encryption also does not decide which user may recover a value: authorize access before calling `decrypt()`.

The `b"k" * 32` keys in examples are test fixtures. In production retain the random key in your secret management system and share a stable value across workers and deployments that must read the same tokens. Do not replace `APP_KEY` without a migration: there is no key ring or automatic lookup of previous keys.

### Controlled rotation

Migrate existing CBC records before upgrading: use the previous framework version in a controlled offline process with the original key to recover trusted records, then encrypt them using GCM and replace each record only after both operations succeed. This version provides no CBC fallback. Old CBC data has no authentication, so successful recovery alone cannot establish its integrity; verify it against an independent trusted source. An interrupted migration must resume without confusing versions; version markers and key custody belong to the application. Include backups in the same plan. Never indiscriminately try keys in a public endpoint.

## Core concepts

### Cipher selection

An `Encrypter` instance captures its cipher and key at construction. Supported identifiers are `AES-128-GCM` and `AES-256-GCM`. The legacy CBC enum members and size constants remain available for describing older data, but they do not enable CBC encryption or decryption. Recovering the original plaintext requires the same cipher and key. Create a new instance when changing configuration; mutating its key or cipher attributes does not rebuild cached cryptographic state.

### Envelope format

`encrypt()` UTF-8 encodes the text, creates a fresh random IV, encrypts it, serializes `iv`, `value`, `tag`, and `cipher` as JSON, then Base64-encodes the JSON. Binary fields are themselves Base64 strings. The format is transportable text, not a hash.

### Authentication

GCM verifies the ciphertext and nonce through its 16-byte authentication tag using the existing [`cryptography.AESGCM` primitive](https://cryptography.io/en/50.0.0/hazmat/primitives/aead/#cryptography.hazmat.primitives.ciphers.aead.AESGCM). The service never releases plaintext after an authentication failure. Never expose, log, or commit the application key.

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

print("two authenticated ciphers ok")
```


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


### Use the application facade

```python
from orionis.support.facades import Crypt

token = Crypt.encrypt("private value")
plaintext = Crypt.decrypt(token)
assert plaintext == "private value"
```

## Configuration

`config/app.py` supplies the settings:

| Setting | Environment | Meaning |
|---|---|---|
| `app.cipher` | `APP_CIPHER` | `AES-128-GCM` or `AES-256-GCM`; default is `AES-256-GCM`. |
| `app.key` | `APP_KEY` | Raw text or `base64:`-prefixed key with exactly the cipher's required byte length. |

The validated application config converts the key to bytes. If no key is configured, `SecureKeyGenerator` creates a random Laravel-compatible `base64:` value, persists it through `Env.set`, and normalizes it. Persist a stable production key: losing it makes existing ciphertext unrecoverable.

## Integration with Orionis

`EncrypterProvider` is a core, non-deferred provider. It binds `IEncrypter` to `Encrypter` as a singleton, then pins `Crypt` during async boot so synchronous calls do not return a deferred dispatcher.

`Stringable.encrypt/decrypt`, registration flows, view globals, and MCP state use the service or facade. Dependency-injected code can request `IEncrypter`; ordinary application code can import `Crypt` from `orionis.support.facades`.

## Errors and edge cases

- Empty plaintext and payload strings raise `ValueError`; non-strings raise `TypeError`.
- Unsupported ciphers and wrong key sizes raise `ValueError` at construction. Direct construction requires a `bytes` key; other key types raise `TypeError`.
- Invalid outer Base64/JSON or typed fields raise `ValueError`. Base64 validation rejects non-alphabet characters, including whitespace, in both the outer token and its binary fields.
- Payload cipher mismatch and invalid IV size raise `ValueError` before decryption.
- GCM requires a 16-byte tag; authentication failures surface as wrapped `RuntimeError`.
- CBC configuration is rejected before key generation or persistence; legacy CBC envelopes are rejected before decryption.
- The plaintext must be valid UTF-8 text; this API is not a raw-byte encryption interface.
- Cryptographic failures use the public messages `Encryption failed` or `Decryption failed`. The original exception remains available as `__cause__` for internal diagnostics; these causes and tracebacks are not intended for public responses.

## Performance and concurrency

The implementation is synchronous and CPU-bound. The service caches one `AESGCM` object per instance. Payload encoding uses reusable `msgspec` structures/decoder. Each call keeps data local and obtains a fresh IV from `os.urandom`, so the singleton can serve concurrent callers without mutable per-operation state while its configuration remains unchanged.

Token size includes JSON and two Base64 layers plus IV/tag overhead. Avoid using encryption as a streaming format for large files; use a purpose-built streaming scheme and authenticated mode instead.

## Public API

### `Encrypter(app)`

Reads `app.key` as bytes and `app.cipher` as a supported string. Construction raises `TypeError` for a key that is not `bytes`, or `ValueError` for an unsupported cipher or an incorrect key length. The application configuration layer performs text and `base64:` key normalization before this service is constructed. `SUPPORTED_CIPHERS`, AES key sizes, `GCM_IV_SIZE`, and `GCM_TAG_SIZE` describe the accepted format. `CBC_IV_SIZE` and `PKCS7_BLOCK_SIZE` describe legacy data only.

### `encrypt(plaintext: str) -> str`

Accepts a non-empty string and returns a new Base64 envelope. A random IV means encrypting the same plaintext twice should produce different tokens. Invalid input raises `TypeError` or `ValueError`; cryptographic failures are wrapped in `RuntimeError("Encryption failed")` with the original exception as their direct cause.

### `decrypt(payload: str) -> str`

Decodes and validates the envelope, requires its cipher to match configuration, checks IV/tag sizes, decrypts, and UTF-8 decodes the result. It rejects empty/non-string input, malformed envelopes, mismatched ciphers, legacy CBC envelopes, invalid tags, and authentication failures. Failures during cryptographic processing use `RuntimeError("Decryption failed")` with the original exception as their direct cause.

### `IEncrypter`

The contract declares only synchronous `encrypt` and `decrypt`. Import it from `orionis.encrypter.contracts` when typing a container-resolved dependency.

## Implementation reference for extensions

| Path | Responsibility |
|---|---|
| `encrypter.py` | Key/cipher validation, envelope encoding, authenticated AES-GCM operations. |
| `contracts/encrypter.py` | `IEncrypter` abstract `encrypt`/`decrypt` interface. |
| `provider.py` | Singleton binding and synchronous facade pinning. |
| `__init__.py` | Public `Encrypter` export. |

---

[Index](README.md) · [foundation](../../../foundation/docs/en/README.md) · [hashing](../../../hashing/docs/en/README.md)
