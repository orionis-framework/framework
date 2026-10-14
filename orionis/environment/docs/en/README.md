# Environment and process configuration

## Overview

The package-level API is `Env` plus the `env()` lookup helper. Both delegate to a process-wide `DotEnv` singleton. On first use, it resolves `.env` from the working directory, creates it if absent, loads it into `os.environ` with file values taking precedence, and caches the file entries for `all()`.

Values may use explicit prefixes such as `int:`, `bool:`, `list:`, `path:`, or `base64:`. Unprefixed values still recognize nulls, booleans, and safe Python literals. `EnvironmentCaster` owns the typed serialization/parsing rules.

## Requirements

- Python 3.14 or newer.
- `python-dotenv>=1.2.3,<2.0`, installed by Orionis.
- Read/write access to the selected `.env` file for persistent `set`, `unset`, and `reload` workflows.
- Uppercase variable names matching `[A-Z][A-Z0-9_]*`.

## Module learning path

- [Persistence, reloads, and Env reference](operations-and-reference.md)
- [Reading and writing environment configuration](typed-configuration.md)

Continue with: [foundation](../../../foundation/docs/en/README.md) · [encrypter](../../../encrypter/docs/en/README.md).

Examples that require bootstrap, a request, or external services state that context. Verification for this reconstruction is distinct from historical notes; a production integration is not assumed to have been executed.
