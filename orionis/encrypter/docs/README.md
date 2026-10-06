# orionis.encrypter

> Synchronous AES-CBC and AES-GCM string encryption with typed JSON envelopes,
> an application-configured key, and an eager singleton service provider.

Spanish version: [README.es.md](README.es.md).

## Table of contents

- [Requirements](#requirements)
- [Functional overview](#functional-overview)
- [Module structure](#module-structure)
- [API reference](#api-reference)
- [IEncrypter](#iencrypter)
- [Encrypter](#encrypter)
- [Encrypter.__init__](#encrypter__init__)
- [Attributes and constants](#attributes-and-constants)
- [Encrypter.encrypt](#encrypterencrypt)
- [Encrypter.decrypt](#encrypterdecrypt)
- [Payload format](#payload-format)
- [Error stages](#error-stages)
- [EncrypterProvider](#encrypterprovider)
- [Crypt integration](#crypt-integration)
- [Usage examples](#usage-examples)
- [Standalone round trips](#standalone-round-trips)
- [Handling actual errors](#handling-actual-errors)
- [Application, container and facade](#application-container-and-facade)
- [Re-encrypting local records](#re-encrypting-local-records)
- [Design characteristics](#design-characteristics)
- [Performance and concurrency](#performance-and-concurrency)
- [Compatibility notes](#compatibility-notes)
- [Verification and limitations](#verification-and-limitations)
- [Source coverage](#source-coverage)
- [Validation record](#validation-record)
- [Docstring discrepancies](#docstring-discrepancies)
- [Scope and limits](#scope-and-limits)

## Requirements

Supply `app.config("app.key")` and `app.config("app.cipher")` before constructing
`Encrypter`; it supplies neither default. The key should be raw `bytes`, not an
encoded `base64:` string. Use one of the four exact cipher values below and a
matching key length. These reads and checks belong to
[Encrypter.__init__](../encrypter.py).

| Cipher value | Key bytes | IV bytes | Tag bytes |
|---|---|---|---|
| `AES-128-CBC` | 16 | 16 | None |
| `AES-256-CBC` | 32 | 16 | None |
| `AES-128-GCM` | 16 | 12 | 16 |
| `AES-256-GCM` | 32 | 12 | 16 |

The catalogue comes from
[orionis/foundation/config/app/enums/ciphers.py](../../foundation/config/app/enums/ciphers.py),
`Cipher`, aliased as `OrionisCipher` inside the implementation. The constructor
does not normalize case, separators or enum objects; pass the enum's `.value`
when supplying configuration directly.

The framework's
[App configuration entity](../../foundation/config/app/entities/app.py),
`App.__post_init__` / `App.__validateKey`, normalizes its cipher and key, decodes
explicit `base64:` keys and UTF-8-encodes ordinary string keys. When its key is
`None`, it generates one and persists `APP_KEY` through `Env.set`. This belongs
to configuration, not `Encrypter`. Constructing application defaults can
therefore write a local environment file; examples use temporary working roots.

Container and facade usage additionally requires application creation and
provider startup. `Application.create()` registers eager services;
`await Application.boot()` also awaits their `boot()` methods for headless
scripts. CLI/HTTP startup performs that provider boot phase as well. See
[Application.create / boot](../../foundation/application.py) and
[EncrypterProvider](#encrypterprovider). No encryption-specific optional extra
or external service is required; declared dependencies appear in
[Compatibility notes](#compatibility-notes).

## Functional overview

The module encrypts non-empty UTF-8 strings and recovers them from base64-wrapped
JSON envelopes. CBC uses PKCS7 padding; GCM uses an authentication tag. Both
branches generate an IV per encryption call and enforce the configured cipher
when decrypting ([Encrypter](../encrypter.py)).

`EncrypterProvider` binds `IEncrypter` to one application-managed `Encrypter` and
pins the `Crypt` facade. Direct construction needs only configuration access;
container resolution and facade dispatch are separate integration concerns
([provider.py](../provider.py), [Crypt](../../support/facades/encrypter.py)).

## Module structure

All five Python files below were inspected recursively. There are no runtime
non-Python resources inside this module.

| Repository path | Responsibility and owned public symbols |
|---|---|
| [orionis/encrypter/__init__.py](../__init__.py) | Re-exports `Encrypter`; `__all__ = ["Encrypter"]`. |
| [orionis/encrypter/encrypter.py](../encrypter.py) | `Encrypter`; private `_Payload`, shared `_PAYLOAD_DECODER` and nine private helpers. |
| [orionis/encrypter/contracts/__init__.py](../contracts/__init__.py) | Re-exports `IEncrypter`; `__all__ = ["IEncrypter"]`. |
| [orionis/encrypter/contracts/encrypter.py](../contracts/encrypter.py) | Abstract `IEncrypter` contract. |
| [orionis/encrypter/provider.py](../provider.py) | `EncrypterProvider`; no root-package re-export. |

## API reference

Declaration blocks in this section are reference fragments copied from source,
not complete scripts: signatures intentionally have no invented body or
ellipsis. Public imports are described separately. Exceptions listed here are
not exhaustive for arbitrary configuration objects or dependency failures.

### IEncrypter

Import `IEncrypter` from `orionis.encrypter.contracts` or
`orionis.encrypter.contracts.encrypter`. Source:
[contracts/encrypter.py](../contracts/encrypter.py).

```python
class IEncrypter(ABC):
```

```python
@abstractmethod
def encrypt(
    self,
    plaintext: str,
) -> str:
```

```python
@abstractmethod
def decrypt(
    self,
    payload: str,
) -> str:
```

These synchronous abstract methods declare string input/output and the same
`TypeError`, `ValueError` and `RuntimeError` families as the implementation.
Their bodies contain only docstrings, so they do not perform encryption or
validate a custom implementation. Implement both methods before instantiating
a subclass; otherwise the ABC machinery raises `TypeError`.

The contract declares `__slots__ = ()` and no explicit constructor. Subclasses
must also declare slots to avoid introducing their own instance dictionary.
The structural checks are in
[tests/encrypter/contracts/test_encrypter.py](../../../tests/encrypter/contracts/test_encrypter.py),
`TestIEncrypterDefinition` and `TestIEncrypterImplementations`.

### Encrypter

Import `Encrypter` from `orionis.encrypter` or
`orionis.encrypter.encrypter`. Source: [encrypter.py](../encrypter.py).

```python
class Encrypter(IEncrypter):
```

Implements the two contract methods. Its explicit constructor, constants and
writable attributes are documented below. It declares no public property,
iterator, context-manager protocol, overload or resource-closing method.

### `Encrypter.__init__`

Source: [encrypter.py](../encrypter.py), `Encrypter.__init__`.

```python
def __init__(
    self,
    app: IApplication,
) -> None:
```

- `app: IApplication` is required. Only `config("app.key")` and
  `config("app.cipher")` are invoked; no runtime `isinstance(app, IApplication)`
  check occurs. A minimal configuration object is used in the standalone
  examples, matching the doubles in the existing tests, not a new protocol.
- Returns `None`; stores the configuration results, validates cipher membership
  and key length, computes `_is_gcm`, and constructs `AESGCM(self.key)` for GCM.
  CBC leaves `_aesgcm` as `None`. The application object is not retained.
- Explicit `ValueError`: unsupported cipher or a key of the wrong length for
  the `AES-128` / `AES-256` family.
- Configuration callback errors propagate unchanged. There is no explicit key
  type check: `None` fails at `len(key)` with `TypeError`, and an unhashable
  cipher fails at membership with `TypeError`. GCM also delegates key validation
  to `AESGCM`. A length-correct string can pass CBC construction but fail during
  encryption; that is not a supported raw-byte key representation.

No key derivation or `base64:` decoding occurs here. No configuration reload,
resource ownership or container registration is performed by this constructor
itself. See `TestEncrypterInitialisation` in
[tests/encrypter/test_encrypter.py](../../../tests/encrypter/test_encrypter.py).

### Attributes and constants

Source: [encrypter.py](../encrypter.py), `Encrypter` and its constructor.
The six numeric constants have no declared type annotation; do not treat
their inferred `int` type as an annotation present in source.

```python
AES_128_KEY_SIZE = 16
AES_256_KEY_SIZE = 32
CBC_IV_SIZE = 16
GCM_IV_SIZE = 12
GCM_TAG_SIZE = 16
PKCS7_BLOCK_SIZE = 16
SUPPORTED_CIPHERS: ClassVar[frozenset[str]] = frozenset(
    cipher.value for cipher in OrionisCipher
)
```

These constants define byte lengths and the accepted catalogue in
[Requirements](#requirements). `SUPPORTED_CIPHERS` is computed at class
definition, not rebuilt on every lookup; its current four values come from
`OrionisCipher`. The frozenset value is immutable, but class attributes can
still be rebound by Python callers.

| Public attribute | Declared constructor annotation | Stored value |
|---|---|---|
| `key` | `bytes` | Result of `app.config("app.key")`, without copying or conversion. |
| `cipher` | `str` | Result of `app.config("app.cipher")`, without normalization. |

Both are ordinary writable slots, not validated properties. Assigning them
does not refresh `_is_gcm` or `_aesgcm`: GCM continues using the helper created
with the original key, while CBC builds its cipher from the current `key`.
The current `cipher` is used in envelopes and comparison. There is no public
reconfiguration method that coordinates these fields; construct a separate
instance with consistent configuration when using another key or mode.

### Encrypter.encrypt

Source: [encrypter.py](../encrypter.py), `Encrypter.encrypt`,
`__encryptCBC` and `__encryptGCM`.

```python
def encrypt(
    self,
    plaintext: str,
) -> str:
```

`plaintext: str` is required and must be non-empty. Whitespace, control
characters and multibyte text are not stripped. It is encoded as UTF-8 and
encrypted completely in memory. Returns a `str` containing the envelope
described in [Payload format](#payload-format), not raw ciphertext bytes.

| Exception reaching the caller | Condition |
|---|---|
| `TypeError` | Input is not a `str`: `Plaintext must be a string`. |
| `ValueError` | Empty input: `Plaintext cannot be empty`. |
| `ValueError` | UTF-8 encoding raises `UnicodeEncodeError`, such as for `"\ud800"`; the original error is chained. |
| `RuntimeError` | An `Exception` in the selected encryption branch is wrapped with `Error during encryption:` and chained. This includes primitive, randomness and envelope-encoding failures. |

Each call reads a new random IV using `os.urandom`. Repeated plaintext normally
gives different envelopes, but the implementation keeps no nonce registry and
does not guarantee uniqueness. The method does not change instance attributes,
write files, access the network or resolve services. Randomness and synchronous
cryptographic work still execute on the caller's thread. See
`TestEncrypterEncrypt` / `TestEncrypterRoundTrip` in
[tests/encrypter/test_encrypter.py](../../../tests/encrypter/test_encrypter.py).

### Encrypter.decrypt

Source: [encrypter.py](../encrypter.py), `Encrypter.decrypt` and the helpers in
[Error stages](#error-stages).

```python
def decrypt(
    self,
    payload: str,
) -> str:
```

`payload: str` is required and must be non-empty. Returns the recovered UTF-8
`str` after envelope decoding, cipher comparison, IV validation and decryption.
The payload's cipher does not select a new algorithm or configuration.

| Exception reaching the caller | Condition |
|---|---|
| `TypeError` | Input is not a `str`: `Payload must be a string`. |
| `ValueError` | Empty input: `Payload cannot be empty`. |
| `ValueError` | Outer base64 decoding or typed JSON decoding fails; handled decoder errors get the `Invalid payload:` prefix. Missing/wrongly typed fields are rejected by msgspec. |
| `ValueError` | Inner base64 decoding fails; handled `binascii.Error` gets the `Error decoding payload data:` prefix. |
| `ValueError` | Payload `cipher` is not exactly equal to the instance's current `cipher`. |
| `ValueError` | IV is not 16 bytes for CBC or 12 bytes for GCM. |
| `RuntimeError` | An `Exception` inside `__performDecryption` is wrapped with `Error during decryption:` and chained, including missing/wrong-sized GCM tag, authentication failure, malformed CBC ciphertext, padding failure or invalid recovered UTF-8. |

Python's base64 decoder uses its default, non-strict mode. Non-ASCII base64
strings can propagate a decoder `ValueError` without the module's prefix.
Checks do not form a canonical-base64 validator. Methods leave instance state
unchanged and hold no external resource requiring cleanup. See
`TestEncrypterDecryptPayloadValidation` / `TestEncrypterDecryptFailures` in
[tests/encrypter/test_encrypter.py](../../../tests/encrypter/test_encrypter.py).

### Payload format

Source: [encrypter.py](../encrypter.py), `_Payload`, `_PAYLOAD_DECODER`,
`__encryptCBC`, `__encryptGCM`, `__decodePayload` and `__extractPayloadData`.
`_Payload` is a private `msgspec.Struct` declared with `gc=False`, not a public
object callers need to construct. Its required fields are declared in this
order: `iv: str`, `value: str`, `tag: str | None`, `cipher: str`.

The outer representation is standard base64 of UTF-8 JSON; each binary field is
also standard base64, not URL-safe base64. JSON is emitted from the struct,
without an intermediate dictionary.

| Field | CBC | GCM |
|---|---|---|
| `iv` | 16 random bytes, encoded | 12 random bytes, encoded |
| `value` | Block-aligned ciphertext of PKCS7-padded UTF-8 bytes, encoded | Ciphertext excluding the final tag, encoded |
| `tag` | JSON `null` | 16-byte tag, encoded |
| `cipher` | Configured exact string | Configured exact string |

CBC always appends padding, including a full 16-byte block when plaintext bytes
are already block-aligned. Removal rejects empty decrypted bytes, padding length
zero or above 16, and non-uniform padding bytes. Correctly padded empty plaintext
can be accepted by `decrypt()` even though `encrypt("")` is rejected.

GCM calls `AESGCM.encrypt(iv, data, None)` and
`AESGCM.decrypt(iv, value + tag, None)`: no additional authenticated data is
supplied. Empty `tag` strings are converted to `None`; GCM rejects a missing
tag in the decryption stage. CBC does not use the decoded tag for authentication
and does not require it to be `null` when consuming an envelope.

msgspec requires all four fields, including `tag` even when its value is `null`;
unknown JSON fields are accepted by the configured decoder. Base64 decoding
does not pass `validate=True`, so some non-alphabet characters are discarded.
IV and GCM tag lengths are checked after decoding; there is no explicit maximum
payload size or expiry/replay check. Successful CBC decryption is not proof of
authenticity: there is no MAC or signature in that branch.

### Error stages

All helpers below are private implementation details in
[encrypter.py](../encrypter.py); they are included to explain public errors,
not as callable application APIs.

| Private symbol | Role and public effect |
|---|---|
| `__decodePayload` | Decode outer base64 and use the shared typed JSON decoder; handled decode errors become `ValueError`. |
| `__extractPayloadData` | Decode IV, ciphertext and truthy tag; handled `binascii.Error` becomes `ValueError`. |
| `__validateCipherMatch` | Reject a cipher mismatch with `ValueError`. |
| `__validateIvSize` | Reject wrong IV length with `ValueError`. |
| `__performDecryption` | Check GCM tag presence/size, call the mode helper, decode UTF-8; wrap `Exception` as `RuntimeError`. |
| `__encryptCBC` | Generate IV, pad, encrypt and serialize; wrap `Exception` as `RuntimeError`. |
| `__decryptCBC` | Decrypt and check padding; re-raise `ValueError`, wrap other `Exception`. The caller then wraps both as `RuntimeError`. |
| `__encryptGCM` | Generate IV, encrypt, split tag and serialize; wrap `Exception` as `RuntimeError`. |
| `__decryptGCM` | Join ciphertext/tag and authenticate; re-raise `ValueError`, wrap other `Exception`. The caller then wraps both as `RuntimeError`. |

The wrappers catch `Exception`, not all `BaseException` subclasses. Cause chains
are retained with `raise ... from ...`; a GCM `InvalidTag` can have an empty
message. Do not depend on a complete message being stable across dependencies.
There are no module-defined exceptions named `EncryptionError` or
`DecryptionError`.

### EncrypterProvider

Import from `orionis.encrypter.provider`. Source: [provider.py](../provider.py).

```python
class EncrypterProvider(ServiceProvider):
```

```python
def register(self) -> None:
```

```python
async def boot(self) -> None:
```

The constructor is inherited, not declared in this module. Its literal source
is [ServiceProvider.__init__](../../container/providers/service_provider.py):

```python
def __init__(
    self,
    app: IApplication,
) -> None:
```

- The inherited constructor stores `app` in `self.app`; it does not copy the
  application or validate its type.
- `register()` has no extra parameters, returns `None`, and calls
  `self.app.singleton(IEncrypter, Encrypter)`. It declares a binding; it does
  not itself construct an encryption service or pin a facade.
- `boot()` has no extra parameters; awaiting it returns `None` after
  `await CryptFacade.pin()`. This resolves/caches the service on the facade;
  it registers no additional binding.
- Neither override translates errors from the container or facade. In
  particular, configuration failures can propagate while pinning builds the
  service. Calling `boot()` on a provider double does not make that double the
  facade's application: `Facade.resolve()` uses its application reference.

The provider is eager, not a `DeferrableProvider`, and is present in
`CORE_PROVIDER_METADATA` / `CORE_PROVIDERS` in
[orionis/foundation/core_providers.py](../../foundation/core_providers.py).
`Application.create()` registers it; `Application.boot()` or CLI/HTTP provider
startup awaits it. This makes synchronous facade consumers usable after boot.
Existing provider tests are in
[tests/encrypter/test_provider.py](../../../tests/encrypter/test_provider.py),
including registration, eager/core membership and boot with a recording double.

### Crypt integration

`Crypt` is an adjacent facade, not an owned public export of this module.
Import it from `orionis.support.facades.encrypter`; source:
[Crypt.getFacadeAccessor](../../support/facades/encrypter.py).

```python
class Crypt(Facade):
```

```python
@classmethod
def getFacadeAccessor(cls) -> type:
```

The method returns the class `IEncrypter`, not a string. It takes no additional
arguments. The parallel [encrypter.pyi](../../support/facades/encrypter.pyi)
inherits `IEncrypter` and `IFacade`; it is editor/type-checking metadata, not a
runtime implementation of encryption.

Before pinning, `Crypt.encrypt(...)` produces an awaitable `_FacadeDispatch`;
await it only after the application is created. Resolving that eager service
alone does not boot its provider or automatically pin it. After provider boot
or `await Crypt.pin()`, `Crypt.encrypt(...)` and `Crypt.decrypt(...)` return
strings synchronously; awaiting those strings raises `TypeError`. Explicit
resolution before application creation raises `RuntimeError`. Evidence:
[Facade.resolve / pin / unpin](../../container/facades/facade.py) and
[FacadeMeta.__getattr__ / _FacadeDispatch](../../container/facades/meta.py).

For a stable calling shape during startup, use
`service = await app.make(IEncrypter)` followed by synchronous service methods.
[Stringable.encrypt / decrypt](../../support/types/stringable.py) delegate to
`Crypt` without `await`. The view builders
[_global_encrypt / _global_decrypt](../../view/globals/bcrypt.py) instead await
`app.make(IEncrypter)` inside their async callbacks, then call the service.

## Usage examples

Each Python block below is a complete independent script for Python 3.14+ with
the framework and its normal dependencies importable. Run each in a fresh
process: the integration example uses application/facade singleton state.
When running a script outside an installed checkout, place the repository root
on `PYTHONPATH` before launch. Each script changes to its own temporary working
directory before framework imports and restores the original directory.

Run the integration example with default Orionis environment settings.
Inherited OS variables can override unrelated application paths or services;
changing the working directory does not clear `os.environ`. Validation processes
did not inherit application/service variables or credentials.

Keys are generated locally for the demonstration and are not printed or kept.
These scripts do not load this checkout's application, credentials or services.
Expected output blocks omit random keys, IVs and ciphertext.

### Standalone round trips

Exercise every supported cipher and inspect its envelope. `SimpleNamespace`
provides only the configuration access consumed by the constructor; it is not
an `IApplication` subclass. Expected behavior is grounded in
[Encrypter.encrypt / decrypt](../encrypter.py) and the existing round-trip tests.

```python
import base64
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

previous_cwd = Path.cwd()
with TemporaryDirectory() as directory:
    try:
        os.chdir(directory)
        import msgspec.json as msjson
        from orionis.encrypter import Encrypter

        for cipher in sorted(Encrypter.SUPPORTED_CIPHERS):
            key_size = 16 if cipher.startswith("AES-128") else 32
            values = {"app.key": os.urandom(key_size), "app.cipher": cipher}
            crypt = Encrypter(SimpleNamespace(config=values.__getitem__))
            plaintext = "Orionis\ninvoice=42"
            payload = crypt.encrypt(plaintext)
            assert crypt.decrypt(payload) == plaintext
            assert not hasattr(crypt, "__dict__")
            envelope = msjson.decode(base64.b64decode(payload))
            assert set(envelope) == {"iv", "value", "tag", "cipher"}
            assert envelope["cipher"] == cipher
            if cipher.endswith("GCM"):
                assert len(base64.b64decode(envelope["iv"])) == 12
                assert len(base64.b64decode(envelope["tag"])) == 16
            else:
                assert len(base64.b64decode(envelope["iv"])) == 16
                assert envelope["tag"] is None
            print(f"{cipher}: round trip verified")
    finally:
        os.chdir(previous_cwd)
```

```text
AES-128-CBC: round trip verified
AES-128-GCM: round trip verified
AES-256-CBC: round trip verified
AES-256-GCM: round trip verified
```

### Handling actual errors

Distinguish input/envelope validation from a GCM authentication failure. Flip
one ciphertext byte while retaining the tag; do not infer failure from random
replacement bytes. Evidence: [Encrypter error stages](../encrypter.py).

```python
import base64
import os
from collections.abc import Callable
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace


def expect_error(
    exception_type: type[Exception],
    operation: Callable[[], object],
) -> Exception:
    """Return the expected exception and reject a successful operation."""
    try:
        operation()
    except exception_type as exc:
        return exc
    message = "The operation did not raise the expected exception."
    raise AssertionError(message)


previous_cwd = Path.cwd()
with TemporaryDirectory() as directory:
    try:
        os.chdir(directory)
        import msgspec.json as msjson
        from orionis.encrypter import Encrypter

        key = os.urandom(32)
        values = {"app.key": key, "app.cipher": "AES-256-GCM"}
        crypt = Encrypter(SimpleNamespace(config=values.__getitem__))
        expect_error(TypeError, partial(crypt.encrypt, 42))
        empty = expect_error(ValueError, partial(crypt.encrypt, ""))
        assert str(empty) == "Plaintext cannot be empty"
        expect_error(ValueError, partial(crypt.decrypt, "abcde"))
        cbc_values = {"app.key": key, "app.cipher": "AES-256-CBC"}
        cbc = Encrypter(SimpleNamespace(config=cbc_values.__getitem__))
        expect_error(ValueError, partial(cbc.decrypt, crypt.encrypt("record")))

        envelope = msjson.decode(base64.b64decode(crypt.encrypt("record")))
        ciphertext = bytearray(base64.b64decode(envelope["value"]))
        ciphertext[0] ^= 1
        envelope["value"] = base64.b64encode(ciphertext).decode("ascii")
        tampered = base64.b64encode(msjson.encode(envelope)).decode("ascii")
        failure = expect_error(RuntimeError, partial(crypt.decrypt, tampered))
        assert failure.__cause__ is not None
        assert str(failure).startswith("Error during decryption:")
        print("Input, envelope and cipher mismatch checks verified")
        print("Tampered GCM ciphertext: RuntimeError")
    finally:
        os.chdir(previous_cwd)
```

```text
Input, envelope and cipher mismatch checks verified
Tampered GCM ciphertext: RuntimeError
```

### Application, container and facade

Create a real application under a temporary root. First use the unpinned
dispatcher after `create()`, then await eager provider startup with `boot()`.
This exercises [Application](../../foundation/application.py),
[EncrypterProvider](../provider.py), [Crypt](../../support/facades/encrypter.py)
and the actual [Stringable consumer](../../support/types/stringable.py).
No server or external backend is started by this script.

```python
import asyncio
import inspect
import logging
import os
from pathlib import Path
from tempfile import TemporaryDirectory

previous_cwd = Path.cwd()
with TemporaryDirectory() as directory:
    try:
        os.chdir(directory)
        from orionis.encrypter.contracts import IEncrypter
        from orionis.foundation.application import Application
        from orionis.support.facades.encrypter import Crypt
        from orionis.support.types.stringable import Stringable

        app = Application(base_path=Path(directory))
        app.withConfigApp(key=os.urandom(32), cipher="AES-256-GCM")

        async def main() -> None:
            """Exercise the service before and after eager provider startup."""
            app.create()
            service = await app.make(IEncrypter)
            assert service is await app.make(IEncrypter)
            pending = Crypt.encrypt("deferred facade")
            assert inspect.isawaitable(pending)
            payload = await pending
            assert await Crypt.decrypt(payload) == "deferred facade"
            print("Created application: singleton and deferred facade verified")

            await app.boot()
            assert await Crypt.resolve() is service
            payload = Crypt.encrypt("pinned facade")
            assert isinstance(payload, str)
            assert Crypt.decrypt(payload) == "pinned facade"
            wrapped_payload = Stringable("string consumer").encrypt()
            assert isinstance(wrapped_payload, str)
            assert Stringable(wrapped_payload).decrypt() == "string consumer"
            print("Booted application: synchronous Crypt and Stringable verified")

        asyncio.run(main())
    finally:
        logging.shutdown()
        os.chdir(previous_cwd)
```

```text
Created application: singleton and deferred facade verified
Booted application: synchronous Crypt and Stringable verified
```

### Re-encrypting local records

Combine JSON serialization, temporary file storage, CBC decryption and GCM
encryption using two independent instances. This is application-level
composition of [encrypt / decrypt](../encrypter.py), not a module key-rotation
API. Keys live only in this process; files and any generated configuration
artifacts are removed with the temporary directory.

```python
import base64
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

previous_cwd = Path.cwd()
with TemporaryDirectory() as directory:
    try:
        os.chdir(directory)
        import msgspec.json as msjson
        from orionis.encrypter import Encrypter

        legacy_values = {
            "app.key": os.urandom(32),
            "app.cipher": "AES-256-CBC",
        }
        current_values = {
            "app.key": os.urandom(16),
            "app.cipher": "AES-128-GCM",
        }
        legacy = Encrypter(SimpleNamespace(config=legacy_values.__getitem__))
        current = Encrypter(SimpleNamespace(config=current_values.__getitem__))
        records = [{"id": index, "label": f"record-{index}"} for index in range(3)]
        old_payloads = [
            legacy.encrypt(msjson.encode(record).decode("utf-8"))
            for record in records
        ]
        legacy_path = Path(directory) / "legacy.json"
        current_path = Path(directory) / "current.json"
        legacy_path.write_bytes(msjson.encode(old_payloads))
        stored_payloads = msjson.decode(legacy_path.read_bytes())
        new_payloads = [
            current.encrypt(legacy.decrypt(payload)) for payload in stored_payloads
        ]
        current_path.write_bytes(msjson.encode(new_payloads))
        restored = [
            msjson.decode(current.decrypt(payload).encode("utf-8"))
            for payload in msjson.decode(current_path.read_bytes())
        ]
        assert restored == records
        for payload in new_payloads:
            envelope = msjson.decode(base64.b64decode(payload))
            assert envelope["cipher"] == "AES-128-GCM"
        print("3 local records re-encrypted and verified")
    finally:
        os.chdir(previous_cwd)
```

```text
3 local records re-encrypted and verified
```

## Design characteristics

- ABC contract with empty slots plus concrete slots -> `Encrypter` has no
  per-instance `__dict__`; only `_aesgcm`, `_is_gcm`, `cipher` and `key` are
  stored ([IEncrypter](../contracts/encrypter.py), [Encrypter](../encrypter.py)).
- One-time mode flag and GCM helper -> mode selection and GCM key helper are
  retained from construction, not recomputed when public slots are assigned.
- Private typed struct and shared decoder -> envelope field validation is
  separate from cryptographic validation. `_Payload(gc=False)` has no cyclic
  object graph in the fields used here; it is not a public schema API.
- Eager singleton provider plus process-level facade pin -> application-created
  services are reused, but direct `Encrypter(app)` constructions remain separate
  objects ([provider.py](../provider.py), [Facade](../../container/facades/facade.py)).
- Nested exception wrappers -> callers must distinguish pre-validation
  `ValueError` from cryptographic-stage `RuntimeError`, including its causes.
  The actual mechanisms are in [encrypter.py](../encrypter.py).

## Performance and concurrency

Evidence: [Encrypter and its helpers](../encrypter.py),
[provider.py](../provider.py), [facade state](../../container/facades/facade.py).

`encrypt()` / `decrypt()` are synchronous and contain no `await`, executor
dispatch, file/network access, generator or streaming API. Encoding, decoding,
padding, crypto and randomness run on the caller's thread; calling them inside
a coroutine does not make that work asynchronous. Provider boot and container
resolution are asynchronous integration operations, not encryption methods.

Inputs, ciphertext, JSON and base64 are fully materialized, with copies made by
encoding, concatenation and slicing. CBC adds 1 to 16 padding bytes and GCM
extracts a 16-byte tag. For plaintext byte length `n`, codec/cipher processing
and buffers grow with the whole message; there is no explicit input-size cap.
No throughput, constant-time property or allocation-free guarantee is claimed.

`AESGCM` is retained per GCM instance; CBC builds a fresh `Cipher` and context
per operation. `_PAYLOAD_DECODER` is shared at module scope and has no module
invalidation API. These observations do not establish a particular backend key
schedule or thread-safety guarantee. There is no payload/result cache.

Public methods do not reassign instance fields after initialization and do not
suspend midway for asyncio task interleaving. Public slots can nevertheless
be changed externally, and singleton/facade instances share those changes.
The module provides no locks around methods, decoder access or configuration.

> ⚠️ Not specified in the source code: concurrent cross-thread use of the shared
> decoder, GCM helper and writable singleton fields has no module-level safety
> contract. No cross-thread or multiprocess certification was performed here.

## Compatibility notes

- The project declares Python `>=3.14` in
  [pyproject.toml](../../../pyproject.toml); [uv.lock](../../../uv.lock) also
  declares `>=3.14`. Validation uses CPython **3.14.6 on Windows**. Other Python
  versions and operating systems were not executed for this documentation.
- The source uses `bytes | None`, `tuple[...]` and `ClassVar[frozenset[str]]`.
  This syntax alone does not declare support for an older runtime. The concrete
  constructor imports `IApplication` at runtime and does not use future string
  annotations; the contract and provider do use future annotations. Its actual
  constructor type is important to container reflection.
- Base dependencies in [pyproject.toml](../../../pyproject.toml) are
  `cryptography>=50.0.1,<51.0` and `msgspec>=0.21.1`. They are not optional
  encryption extras. [uv.lock](../../../uv.lock) resolves **cryptography 50.0.2**
  and **msgspec 0.22.0**; those are also the installed validation versions,
  not the minimum declared versions.
- Envelopes carry a cipher string but no key identifier, key derivation settings,
  expiry or automatic migration. Correct recovery needs matching cipher/key
  configuration. A wrong GCM key fails authentication; CBC has no key identity
  or authenticity check beyond decryption, padding and UTF-8 processing, so
  failure on every wrong key or tampering is not guaranteed
  ([Encrypter](../encrypter.py)).
- `Stringable.encrypt()` / `decrypt()` are annotated/documented as returning
  `Stringable`, but directly return `Crypt` results without wrapping. With this
  pinned implementation the observed result is `str`, not a newly constructed
  `Stringable` ([stringable.py](../../support/types/stringable.py)).

## Verification and limitations

### Source coverage

All five module Python files, both export lists, three public classes, seven
declared public methods (including the explicit constructor), seven public
constants and two public attributes were inventoried and documented. The
provider's inherited constructor is attributed to its actual base class.
There are no owned public free functions, aliases, exceptions, enums,
properties, overloads or special consumer protocols beyond that constructor.

`_Payload`, `_PAYLOAD_DECODER` and nine private helpers are described only where
they explain envelope layout, state or error boundaries. Nineteen import
statements are dependencies/re-exports, not nineteen additional owned public
APIs. In particular, `msgspec`, cryptography's `Cipher`, `algorithms`, `modes`,
`AESGCM`, `OrionisCipher`, `IApplication`, `ServiceProvider` and `CryptFacade`
are not encryption-module APIs to adopt as new exports.

The four existing test files were inspected:
[test_encrypter.py](../../../tests/encrypter/test_encrypter.py) (43 methods),
[test_provider.py](../../../tests/encrypter/test_provider.py) (8),
[test_package.py](../../../tests/encrypter/test_package.py) (2) and
[contracts/test_encrypter.py](../../../tests/encrypter/contracts/test_encrypter.py)
(8). They provide 61 concrete test methods, not universal security guarantees.

### Validation record

The four examples were extracted verbatim from this README and executed in
independent processes using the repository virtual environment: CPython 3.14.6,
Windows, cryptography 50.0.2 and msgspec 0.22.0. Each imported Orionis module's
file was checked against this local repository, not an installed second copy.

| Example | Status | Completed checks |
|---|---|---|
| Standalone round trips | Executed successfully | Syntax, local imports, four ciphers, envelope dimensions, round trips and exact expected output. |
| Handling actual errors | Executed successfully | Syntax, local imports, input/envelope/cipher validation, ciphertext tampering, cause chain and exact expected output. |
| Application, container and facade | Executed successfully | Syntax, local imports, actual creation/boot, singleton identity, unpinned/pinned facade, Stringable and exact expected output. |
| Re-encrypting local records | Executed successfully | Syntax, local imports, temporary file I/O, CBC-to-GCM composition, recovered records and exact expected output. |

Fifteen additional focused cases confirmed missing/non-byte keys, enum and
unhashable cipher inputs, unknown JSON fields, non-strict/non-ASCII base64,
missing/null/empty tags, ignored CBC tag, padded empty CBC plaintext, cached
GCM key after public assignment and App's base64 key normalization.

All **61 existing tests passed**, with **0 failures, 0 errors and 0 skips**.
They were loaded from their original local files and run through
[orionis.test.executors.runner.TestRunner](../../test/executors/runner.py) after
booting a real application under a temporary root. Both raw runner outcomes and
reported statuses were checked; this was not a plain `unittest` run or a full
framework test run. Reactor was not launched against this checkout's bootstrap.

Execution used bytecode suppression, temporary working/configuration roots,
closed logging handlers before cleanup, a filesystem audit barrier rejecting
writes outside the external temporary area, and a network barrier. The only
socket exception was Python's own Windows asyncio socket-pair initialization,
identified by the standard-library helper's code object, not a general
permission for local services. No repository execution artifact was permitted.

### Docstring discrepancies

- [Encrypter.__performDecryption](../encrypter.py) lists `ValueError` for tag
  checks, but its enclosing `except Exception` wraps them as `RuntimeError`.
- [Encrypter.__decryptGCM](../encrypter.py) describes authentication failure as
  `ValueError`; the installed backend raises `InvalidTag`, which the helper
  wraps as `RuntimeError` and the public path wraps again.
- [Crypt.getFacadeAccessor](../../support/facades/encrypter.py) describes a
  string/unit-test accessor and a `str` result; the signature is `-> type` and
  the implementation returns `IEncrypter`.
- [Stringable.encrypt / decrypt](../../support/types/stringable.py) call this
  implementation through `Crypt` despite their placeholder prose and
  `Stringable` result description. The pinned runtime returns a plain `str`.
- `TestEncrypterInitialisation.testGcmModeCachesTheAuthenticatedCipherHelper` in
  [test_encrypter.py](../../../tests/encrypter/test_encrypter.py) refers to a
  once-computed key schedule in its docstring, but its assertions establish
  only the mode flag and helper type. This manual makes no backend key-schedule
  claim.

These are implementation-versus-description observations, not code changes or
recommendations to refactor.

### Scope and limits

No benchmarks, external services, real credentials, dependency changes,
source/test edits or security audit are part of this documentation. Validation
scripts and evidence remain outside the repository. This manual describes the
inspected implementation and locally executed cases, not an independent
cryptographic protocol or deployment certification.
