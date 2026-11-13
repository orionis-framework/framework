# Environment and process configuration

## Overview

The package-level API is `Env` plus the `env()` lookup helper. Both delegate to a process-wide `DotEnv` singleton. On first use, it resolves `.env` from the working directory, creates it if absent, loads it into `os.environ` with file values taking precedence, and caches the file entries for `all()`.

Values may use explicit prefixes such as `int:`, `bool:`, `list:`, `path:`, or `base64:`. Unprefixed values still recognize nulls, booleans, and safe Python literals. `EnvironmentCaster` owns the typed serialization/parsing rules.

## Requirements

- Python 3.14 or newer.
- `python-dotenv>=1.2.3,<2.0`, installed by Orionis.
- Read access to the selected `.env` file for initial loading and `reload`; write access for file creation, persistent `set`, and persistent `unset`.
- Public lookup and mutation keys matching `[A-Z][A-Z0-9_]*`.

## Module learning path

- [Persistence, reloads, and Env reference](operations-and-reference.md)
- [Reading and writing environment configuration](typed-configuration.md)

Continue with: [foundation](../../../foundation/docs/en/README.md) · [encrypter](../../../encrypter/docs/en/README.md).

The examples run without application bootstrap or external services. Run them in a temporary working directory: even the first process-only operation initializes the singleton and loads its selected `.env`.
