# Orionis Encrypter (`orionis.encrypter`)

> Synchronous, AES-based symmetric encryption service exposed through the
> `IEncrypter` contract and the `Crypt` facade.
>
> 🇪🇸 Versión en español: [README.es.md](README.es.md)

## Table of contents

- [Functional description](#functional-description)
  - [Where it fits](#where-it-fits)
  - [Module map](#module-map)
  - [Payload format](#payload-format)
  - [Design notes](#design-notes)
- [API reference](#api-reference)
  - [`IEncrypter`](#iencrypter)
  - [`Encrypter`](#encrypter)
    - [Class attributes](#class-attributes)
    - [`Encrypter.__init__()`](#encrypter__init__)
    - [`Encrypter.encrypt()`](#encrypterencrypt)
    - [`Encrypter.decrypt()`](#encrypterdecrypt)
    - [Internal helpers](#internal-helpers)
  - [`EncrypterProvider`](#encrypterprovider)
  - [`Crypt` facade](#crypt-facade)
- [Usage examples](#usage-examples)
  - [Encrypting with the application configuration](#encrypting-with-the-application-configuration)
  - [Choosing a cipher explicitly](#choosing-a-cipher-explicitly)
  - [Handling errors](#handling-errors)
  - [Resolving the service and the facade](#resolving-the-service-and-the-facade)
- [Performance and concurrency considerations](#performance-and-concurrency-considerations)
- [Compatibility notes](#compatibility-notes)

## Functional description

`orionis.encrypter` turns a string into a self-describing, base64-encoded
envelope and back again, using AES in CBC or GCM mode. The key and the mode
come from the application configuration (`app.key` and `app.cipher`), so
callers never handle key material, initialisation vectors, PKCS7 padding or
authentication tags themselves.

### Where it fits

| Component | Relationship |
|---|---|
| `orionis.foundation.contracts.application.IApplication` | Read at construction time through `app.config("app.key")` and `app.config("app.cipher")`. |
| `orionis.foundation.config.app.enums.ciphers.Cipher` | Source of `Encrypter.SUPPORTED_CIPHERS`. |
| `orionis.container.providers` | `EncrypterProvider` extends `ServiceProvider` and `DeferrableProvider`. |
| `orionis.support.facades.encrypter.Crypt` | Facade whose accessor is `IEncrypter`; pinned by `EncrypterProvider.boot()`. |
| `orionis.view.globals.bcrypt` | Builds the `encrypt` / `decrypt` template globals with `await app.make(IEncrypter)`. |
| `orionis.support.types.stringable.Stringable` | Its `encrypt()` / `decrypt()` methods delegate to the `Crypt` facade. |

### Module map

| File | Contents |
|---|---|
| `orionis/encrypter/__init__.py` | Exports `Encrypter` (`__all__ = ["Encrypter"]`). |
| `orionis/encrypter/encrypter.py` | `_Payload` (private `msgspec.Struct`) and `Encrypter`. |
| `orionis/encrypter/provider.py` | `EncrypterProvider`. |
| `orionis/encrypter/contracts/__init__.py` | Exports `IEncrypter` (`__all__ = ["IEncrypter"]`). |
| `orionis/encrypter/contracts/encrypter.py` | `IEncrypter` abstract contract. |

### Payload format

`encrypt()` returns `base64(json(_Payload))`. `_Payload` is a
`msgspec.Struct` declared with `gc=False` and four fields, in this order:

```python
class _Payload(msgspec.Struct, gc=False):
    iv: str
    value: str
    tag: str | None
    cipher: str
```

| Field | CBC | GCM |
|---|---|---|
| `iv` | base64 of 16 random bytes | base64 of 12 random bytes |
| `value` | base64 of the PKCS7-padded ciphertext | base64 of the ciphertext without its trailing tag |
| `tag` | `None` | base64 of the 16-byte authentication tag |
| `cipher` | the configured cipher name | the configured cipher name |

The envelope carries its own cipher name, but `decrypt()` still refuses any
payload whose `cipher` differs from the one currently configured.

### Design notes

- `Encrypter` declares `__slots__ = ("_aesgcm", "_is_gcm", "cipher", "key")`
  and `IEncrypter` declares `__slots__ = ()`, so instances carry no
  attribute dictionary.
- `_is_gcm` is computed once in `__init__` (`"GCM" in self.cipher`), so no
  substring scan happens per operation.
- The `AESGCM` object is built once in `__init__` for GCM ciphers and reused,
  so the key schedule is not recomputed per call. For CBC ciphers it stays
  `None` and a fresh `Cipher` object is built on every operation.
- `SUPPORTED_CIPHERS` is a `ClassVar[frozenset[str]]` derived from the
  `Cipher` enum, so membership checks are O(1) and the catalogue is immutable.
- `_Payload` is a typed `msgspec.Struct`, so a malformed envelope is rejected
  by schema validation before any cipher primitive is touched.
- `EncrypterProvider` binds `IEncrypter` as a **singleton**, so a whole
  application shares one instance (and therefore one `AESGCM` key schedule).
- `EncrypterProvider` is a plain `ServiceProvider`, not a deferred one, so its
  `boot()` runs at application startup and the `Crypt` facade is pinned before
  any request is served. Synchronous consumers depend on that.

## API reference

### `IEncrypter`

Location: `orionis/encrypter/contracts/encrypter.py`. Also re-exported from
`orionis.encrypter.contracts`.

```python
class IEncrypter(ABC):

    __slots__ = ()

    @abstractmethod
    def encrypt(self, plaintext: str) -> str: ...

    @abstractmethod
    def decrypt(self, payload: str) -> str: ...
```

Abstract members: `encrypt` and `decrypt`. Both are declared without a body,
so a subclass that does not implement them cannot be instantiated.

`__slots__ = ()` means subclasses declaring their own `__slots__` stay free
of a per-instance `__dict__`.

### `Encrypter`

Location: `orionis/encrypter/encrypter.py`. The only concrete implementation
of `IEncrypter` shipped by the framework.

```python
class Encrypter(IEncrypter):

    __slots__ = ("_aesgcm", "_is_gcm", "cipher", "key")
```

Instance attributes, all assigned in `__init__`:

| Attribute | Type | Meaning |
|---|---|---|
| `key` | `bytes` | Raw AES key, exactly as returned by `app.config("app.key")`. |
| `cipher` | `str` | Configured cipher name. |
| `_is_gcm` | `bool` | Whether the configured cipher runs in GCM mode. |
| `_aesgcm` | `AESGCM \| None` | Cached AEAD helper for GCM, `None` for CBC. |

#### Class attributes

| Name | Value | Used for |
|---|---|---|
| `AES_128_KEY_SIZE` | `16` | Key length demanded by `AES-128-*` ciphers. |
| `AES_256_KEY_SIZE` | `32` | Key length demanded by `AES-256-*` ciphers. |
| `CBC_IV_SIZE` | `16` | IV length generated and validated for CBC. |
| `GCM_IV_SIZE` | `12` | IV length generated and validated for GCM. |
| `GCM_TAG_SIZE` | `16` | Authentication tag length for GCM. |
| `PKCS7_BLOCK_SIZE` | `16` | Block size used for padding and its validation. |
| `SUPPORTED_CIPHERS` | `ClassVar[frozenset[str]]` | `{'AES-128-CBC', 'AES-128-GCM', 'AES-256-CBC', 'AES-256-GCM'}`, built from the `Cipher` enum. |

#### `Encrypter.__init__()`

```python
def __init__(
    self,
    app: IApplication,
) -> None:
```

| Parameter | Type | Description |
|---|---|---|
| `app` | `IApplication` | Object providing configuration access. Only `app.config("app.key")` and `app.config("app.cipher")` are read; there is no `isinstance` check, so any object exposing `config(path)` works. |

**Returns:** `None`.

**Raises:** `ValueError` when the configured cipher is not in
`SUPPORTED_CIPHERS`, when an `AES-128-*` cipher does not receive a 16-byte
key, or when an `AES-256-*` cipher does not receive a 32-byte key.

**Side effects:** builds and caches an `AESGCM` instance when the cipher runs
in GCM mode. No I/O, no container registration.

#### `Encrypter.encrypt()`

```python
def encrypt(
    self,
    plaintext: str,
) -> str:
```

| Parameter | Type | Description |
|---|---|---|
| `plaintext` | `str` | Text to encrypt. Encoded as UTF-8 before reaching the cipher. |

**Returns:** `str` — the base64-encoded envelope described in
[Payload format](#payload-format).

**Raises:**

| Exception | Condition |
|---|---|
| `TypeError` | `plaintext` is not a `str` (message: `Plaintext must be a string`). |
| `ValueError` | `plaintext` is empty (`Plaintext cannot be empty`). |
| `ValueError` | `plaintext.encode("utf-8")` fails, for example on an unpaired surrogate (`UTF-8 encoding error: ...`). |
| `RuntimeError` | Any failure raised by the cipher branch, wrapped as `Error during encryption: ...`. |

**Side effects:** draws a fresh IV from `os.urandom` on every call
(`CBC_IV_SIZE` or `GCM_IV_SIZE` bytes), so two calls with the same plaintext
never return the same payload. Instance state is not mutated.

#### `Encrypter.decrypt()`

```python
def decrypt(
    self,
    payload: str,
) -> str:
```

| Parameter | Type | Description |
|---|---|---|
| `payload` | `str` | Envelope previously produced by `encrypt()`. |

**Returns:** `str` — the recovered plaintext, decoded as UTF-8.

**Raises:**

| Exception | Condition |
|---|---|
| `TypeError` | `payload` is not a `str` (`Payload must be a string`). |
| `ValueError` | `payload` is empty (`Payload cannot be empty`). |
| `ValueError` | The outer base64 or the JSON envelope is malformed, or a mandatory field is missing (`Invalid payload: ...`). |
| `ValueError` | An inner base64 field cannot be decoded (`Error decoding payload data: ...`). |
| `ValueError` | The envelope was produced by another cipher (`Payload cipher '...' does not match configured cipher '...'`). |
| `ValueError` | The IV length does not match the mode (`Invalid IV for GCM: ...` / `Invalid IV for CBC: ...`). |
| `RuntimeError` | Everything raised from the decryption stage, wrapped as `Error during decryption: ...`. |

The four `ValueError` families above are raised by the validation stage,
before any cipher primitive runs. Once decryption starts, **every** failure
surfaces as `RuntimeError`, including the missing GCM tag, a tag of the wrong
size, invalid PKCS7 padding and a failed GCM authentication.

**Side effects:** none. No I/O and no instance state mutation.

#### Internal helpers

Private methods of `Encrypter`, listed because they determine which exception
type reaches the caller.

| Method | Stage | Raises |
|---|---|---|
| `__decodePayload(payload)` | Validation | `ValueError` — `Invalid payload: ...` |
| `__extractPayloadData(data)` | Validation | `ValueError` — `Error decoding payload data: ...` |
| `__validateCipherMatch(cipher)` | Validation | `ValueError` — cipher mismatch |
| `__validateIvSize(iv)` | Validation | `ValueError` — IV length mismatch |
| `__performDecryption(value, iv, tag)` | Decryption | `RuntimeError` — wraps everything below |
| `__encryptCBC(data)` | Encryption | `RuntimeError` — `Error in CBC encryption: ...` |
| `__decryptCBC(ct, iv)` | Decryption | `ValueError` for empty data and invalid PKCS7 padding, `RuntimeError` otherwise |
| `__encryptGCM(data)` | Encryption | `RuntimeError` — `Error in GCM encryption: ...` |
| `__decryptGCM(value, iv, tag)` | Decryption | `ValueError` when `tag` is `None`, `RuntimeError` otherwise |

`__decryptCBC` rejects a padding byte of `0`, a padding byte greater than
`PKCS7_BLOCK_SIZE`, and a padding block whose bytes are not all equal to the
declared length.

### `EncrypterProvider`

Location: `orionis/encrypter/provider.py`.

```python
class EncrypterProvider(ServiceProvider):

    def register(self) -> None: ...

    async def boot(self) -> None: ...
```

| Member | Behaviour |
|---|---|
| `register()` | Calls `self.app.singleton(IEncrypter, Encrypter)`. Nothing else. |
| `boot()` | Awaits `Crypt.pin()`, so later facade access skips container resolution. Registers no binding. |

The constructor comes from `ServiceProvider`: `EncrypterProvider(app)` stores
the container in `self.app`.

The provider is listed in `CORE_PROVIDERS`
(`orionis/foundation/core_providers.py`), so an application gets `IEncrypter`
bound without registering anything by hand. It is **not** a
`DeferrableProvider`: deferring it would leave the `Crypt` facade unpinned
until something resolved `IEncrypter`, and the first synchronous call of a
consumer such as `Stringable.encrypt()` would receive a `_FacadeDispatch`
object instead of a string.

### `Crypt` facade

Location: `orionis/support/facades/encrypter.py`.

```python
class Crypt(Facade):

    @classmethod
    def getFacadeAccessor(cls) -> type:
        return IEncrypter
```

The facade resolves `IEncrypter` from the container. `EncrypterProvider.boot()`
pins it during application startup, so under the CLI or HTTP runtime
`Crypt.encrypt(...)` and `Crypt.decrypt(...)` are plain synchronous calls —
which is what `Stringable.encrypt()` and `Stringable.decrypt()` rely on. In a
bare script that only imports `bootstrap.app`, startup has not run, the facade
is still unpinned, and attribute access returns a `_FacadeDispatch` object that
must be awaited. The `orionis/support/facades/encrypter.pyi` stub exists only
for editor completion and is never executed.

## Usage examples

### Encrypting with the application configuration

`Encrypter` reads `app.key` and `app.cipher` straight from the container, so
it can be built without registering the provider.

```python
from bootstrap.app import app
from orionis.encrypter.encrypter import Encrypter

crypt = Encrypter(app)

token = crypt.encrypt("card-4111111111111111")
print("cipher:", crypt.cipher)
print("token is a string:", isinstance(token, str))
print("recovered:", crypt.decrypt(token))
```

Output with the default configuration of this repository:

```text
cipher: AES-256-CBC
token is a string: True
recovered: card-4111111111111111
```

### Choosing a cipher explicitly

`__init__` only calls `config(path)`, so any object exposing that method can
supply the key and the cipher. This is the shape used by the unit tests.

```python
import base64

import msgspec.json

from orionis.encrypter.encrypter import Encrypter


class StaticConfig:
    """Any object exposing config(path) satisfies what Encrypter reads."""

    def __init__(self, key: bytes, cipher: str) -> None:
        self._values = {"app.key": key, "app.cipher": cipher}

    def config(self, path: str) -> object:
        return self._values[path]


crypt = Encrypter(StaticConfig(b"\x11" * 32, "AES-256-GCM"))

token = crypt.encrypt("Orionis")
envelope = msgspec.json.decode(base64.b64decode(token))

print("fields:", sorted(envelope))
print("cipher:", envelope["cipher"])
print("iv bytes:", len(base64.b64decode(envelope["iv"])))
print("tag bytes:", len(base64.b64decode(envelope["tag"])))
print("recovered:", crypt.decrypt(token))
print("payloads differ:", crypt.encrypt("Orionis") != token)
```

Output:

```text
fields: ['cipher', 'iv', 'tag', 'value']
cipher: AES-256-GCM
iv bytes: 12
tag bytes: 16
recovered: Orionis
payloads differ: True
```

### Handling errors

Validation failures raise `ValueError`; anything failing inside the cipher
stage raises `RuntimeError`.

```python
import base64

import msgspec.json

from orionis.encrypter.encrypter import Encrypter


class StaticConfig:
    """Any object exposing config(path) satisfies what Encrypter reads."""

    def __init__(self, key: bytes, cipher: str) -> None:
        self._values = {"app.key": key, "app.cipher": cipher}

    def config(self, path: str) -> object:
        return self._values[path]


cbc = Encrypter(StaticConfig(b"\x11" * 32, "AES-256-CBC"))
gcm = Encrypter(StaticConfig(b"\x11" * 32, "AES-256-GCM"))

# 1. Rejected before any cipher work happens.
try:
    cbc.encrypt("")
except ValueError as exc:
    print("empty ->", exc)

# 2. A payload produced by another cipher is refused.
try:
    cbc.decrypt(gcm.encrypt("Orionis"))
except ValueError as exc:
    print("mismatch ->", exc)

# 3. A malformed envelope never reaches the cipher.
try:
    cbc.decrypt("abcde")
except ValueError as exc:
    print("malformed ->", exc)

# 4. A tampered GCM ciphertext fails authentication.
token = gcm.encrypt("Orionis")
envelope = msgspec.json.decode(base64.b64decode(token))
envelope["value"] = base64.b64encode(b"\x00" * 7).decode()
tampered = base64.b64encode(msgspec.json.encode(envelope)).decode()

try:
    gcm.decrypt(tampered)
except RuntimeError as exc:
    print("tampered ->", exc)

# 5. Configuration errors surface when the service is built.
try:
    Encrypter(StaticConfig(b"\x11" * 16, "AES-256-CBC"))
except ValueError as exc:
    print("key length ->", exc)
```

Output:

```text
empty -> Plaintext cannot be empty
mismatch -> Payload cipher 'AES-256-GCM' does not match configured cipher 'AES-256-CBC'
malformed -> Invalid payload: Invalid base64-encoded string: number of data characters (5) cannot be 1 more than a multiple of 4
tampered -> Error during decryption: Error in GCM decryption: 
key length -> Key must be 32 bytes for AES-256
```

The `Error in GCM decryption:` line ends with an empty detail because the
underlying `InvalidTag` exception carries no message.

### Resolving the service and the facade

`EncrypterProvider` is booted by the framework, so `IEncrypter` is already
bound and the `Crypt` facade is pinned once the CLI or HTTP runtime has
started. The script below runs outside that runtime, so it awaits the facade;
inside a booted application the `await` is unnecessary.

```python
import asyncio

from bootstrap.app import app
from orionis.encrypter.contracts.encrypter import IEncrypter
from orionis.support.facades.encrypter import Crypt


async def main() -> None:
    service = await app.make(IEncrypter)
    print("resolved:", type(service).__name__)
    print("singleton:", service is await app.make(IEncrypter))

    token = await Crypt.encrypt("through the facade")
    print("facade returns:", type(token).__name__)
    print("recovered:", await Crypt.decrypt(token))


asyncio.run(main())
```

Output:

```text
resolved: Encrypter
singleton: True
facade returns: str
recovered: through the facade
```

## Performance and concurrency considerations

- The whole public API is **synchronous**. `encrypt()` and `decrypt()` never
  await, never touch the filesystem or the network, and never call into the
  container.
- Instances carry no `__dict__` (verified: `hasattr(encrypter, "__dict__")`
  is `False`), because `Encrypter` declares `__slots__` and `IEncrypter`
  declares `__slots__ = ()`.
- GCM builds its `AESGCM` helper once per instance; CBC builds a new
  `Cipher` object on every `encrypt()` and `decrypt()` call.
- Every `encrypt()` call reads fresh randomness from `os.urandom`
  (16 bytes for CBC, 12 for GCM).
- Payload encoding and decoding go through `msgspec.json`, and `_Payload`
  is declared with `gc=False`, so the struct is not tracked by the garbage
  collector.
- Both operations hold the full plaintext and the full ciphertext in memory
  at once; there is no streaming or chunked API.
- After `__init__`, `encrypt()` and `decrypt()` only read `key`, `cipher`,
  `_is_gcm` and `_aesgcm`; no method reassigns them.

> ⚠️ No thread-safety or concurrency guarantee is declared in the source
> code: the module uses no locks and no `asyncio` primitives.

## Compatibility notes

- **Python:** the project declares `requires-python = ">=3.14"` in
  `pyproject.toml`. The module uses `X | None` annotations evaluated lazily
  (PEP 649) and deliberately avoids `from __future__ import annotations`,
  which would break dependency injection when the container reflects
  `Encrypter.__init__`.
- **Third-party dependencies**, both already base requirements of the
  framework — nothing extra to install:
  - `cryptography~=48.0` — `Cipher`, `algorithms`, `modes`, `AESGCM`.
  - `msgspec>=0.21.1` — envelope encoding and schema validation.
- **Configuration:** `app.config("app.key")` must yield a bytes-like key of
  exactly 16 or 32 bytes, matching the family named by
  `app.config("app.cipher")`. `config/app.py` reads both from the `APP_KEY`
  and `APP_CIPHER` environment variables, and the `App` config entity
  generates a key with `SecureKeyGenerator` when `APP_KEY` is absent.
- **Cipher catalogue:** only the four names in `SUPPORTED_CIPHERS` are
  accepted, and they are derived from
  `orionis.foundation.config.app.enums.ciphers.Cipher`. Adding a member to
  that enum changes what `Encrypter` accepts.
- **Authentication:** only GCM payloads carry an authentication tag. CBC
  payloads store `tag: None`, and their integrity is checked solely through
  PKCS7 padding validation.
- **Payload portability:** a payload can only be decrypted by an instance
  configured with the same cipher name and the same key; the cipher check
  happens before the key is ever used.
- **Container wiring:** `EncrypterProvider` is part of `CORE_PROVIDERS`, so
  `IEncrypter` is bound as a singleton and the `Crypt` facade is pinned during
  application startup. Because the compiled bootstrap cache
  (`storage/framework/bootstrap`) is not invalidated by changes inside
  `orionis/`, an application that already cached its providers must clear that
  folder — or run `reactor optimize:clear` — to pick up this wiring.
