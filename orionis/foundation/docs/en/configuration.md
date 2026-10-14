# Typed configuration and runtime values

## Configuration

Foundation builds independent native defaults, merges explicit `withConfig...` data, then merges discovered frozen configuration dataclasses. Thus application `config/*.py` entities are the normal final source of section values. After validation, the bootstrap snapshot is deeply frozen.

Core sections are:

| Section | Principal concern |
|---|---|
| `app`, `auth`, `session` | Identity, environment, encryption, guards, cookies, sessions. |
| `http`, `mcp`, `realtime` | HTTP/security limits, protocol origins, realtime limits. |
| `database`, `cache`, `queue`, `scheduler` | Persistence connections, stores, workers, scheduled-state stores. |
| `filesystems`, `mail`, `logging`, `view` | External storage, delivery, channels, templates. |
| `hashing`, `testing` | Password algorithms and test runner behavior. |

Entities are frozen dataclasses and normalize nested dicts/enums into validated objects. Environment variables are read by their field default factories; see each subsystem module for the complete option set.

## Examples

### Validate native application configuration

```python
from orionis.foundation.config.app import App, Cipher, Environments

config = App(
    name="Docs",
    env=Environments.TESTING,
    debug=False,
    cipher=Cipher.AES_256_GCM,
    key=b"k" * 32,
)
assert config.env == "testing"
assert config.cipher == "AES-256-GCM"
assert config.key == b"k" * 32
print(config.name, config.env, config.cipher)
```

## Precedence and the scope of changes

Sections are merged using `dict.update`: native defaults → `withConfig...` values → discovered dataclasses. This is not a universal recursive merge. When replacing a nested dictionary, supply its required options or use the corresponding native entity. Application dataclasses in `config/` are applied last and may override bootstrap values.

`config(key, value)` accepts `None` explicitly because it distinguishes omitted arguments using a sentinel. Changes live in the current process and are not written to `.env`, dataclasses, or other workers. An existing manager may have captured its options: changing `config()` does not promise to reconfigure it. To change an encryption key, connection, or driver, configure startup and restart processes according to the service's operation.

`isProduction()` and `isDebug()` are calculated at creation; do not use them to test whether a later `config()` update propagated. For example, `BaseExceptionHandler` reads `app.debug` in its error path, whereas other components may use snapshots.

## Your own configuration

A frozen dataclass declared in `config/payments.py` is discovered as the `payments` section. Keep this configuration free of network I/O: it is imported and constructed during startup. The section name comes from the module, not the class name. This is the complete file; after `create()`, read it with `app.config("payments.currency")`.

```python
from dataclasses import dataclass

@dataclass(frozen=True, kw_only=True)
class Payments:
    currency: str = "USD"
    receipt_limit: int = 100
```

## Evidence and next steps

[application.py](../../application.py) · [core_config.py](../../core_config.py) · [app.py](../../config/app/entities/app.py)

[Return to the module index](README.md).
