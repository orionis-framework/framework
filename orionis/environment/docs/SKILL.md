---
name: "orionis-environment"
description: >-
  Use when a task involves understanding, integrating, or troubleshooting
  the orionis.environment module: Env and env lookups, DotEnv file selection
  and reloads, typed environment values, validators, or application keys.
  Consult the bundled documentation and inspect the local implementation
  to select verified APIs, respect behavioral constraints, and validate usage.
---

# Work with orionis.environment

## Locate and verify

1. Locate this skill inside `orionis/environment/docs` and resolve the module
   through [its package initializer](../__init__.py). Read the repository's
   applicable instructions before changing anything.
2. Consult [README.md](README.md) or [README.es.md](README.es.md) according to the
   task's language. Start with the [functional overview](README.md#functional-overview)
   and [module structure](README.md#module-structure).
3. Select public imports from the [API reference](README.md#api-reference).
   Import `Env` and `env` from `orionis.environment`; import `DotEnv`,
   `EnvironmentCaster`, the two contracts and `SecureKeyGenerator` from their
   concrete files. Import `EnvironmentValueType` from `orionis.environment.enums`
   and both validators from `orionis.environment.validators`.
4. Reinspect the linked local implementation before asserting behavior.
   Preserve literal names, decorators, keyword-only markers and annotations;
   do not invent `environment.env`, container bindings, `pin()`, reset, close
   or file-switch methods. Treat `ValidateKeyName` as an alias and `ValidateTypes`
   as a callable object, not a constructor.

## Diagnose the actual storage view

- Follow [initialization and import effects](README.md#initialization-and-import-effects).
  Do not repeat the obsolete assumption that a simple environment import creates
  `.env` and `APP_KEY`. Inspect current package/config loading and distinguish
  import from configuration construction. The first environment operation still
  initializes the file service, including process-only writes and missing reads.
- Select `DotEnv(path)` before first construction when a custom file is needed.
  Ensure its parent directory exists; subsequent arguments are ignored and
  `reload()` preserves identity/path. Review [DotEnv](README.md#dotenv).
- Use the [process/cache/file table](README.md#process-cache-and-file-views) to
  diagnose stale values. `get()` reads `os.environ`; `all()` decodes the cached
  file snapshot. Process-only set/unset and external file edits affect different
  views. Return missing-key defaults verbatim; do not parse the default.
- Expect reload to overwrite present file keys without removing absent process
  keys. Distinguish bare file keys from empty assignments. Check the installed
  dependency's interpolation and `PYTHON_DOTENV_DISABLED` behavior before
  diagnosing a discrepancy between loading and cached enumeration.

## Respect conversion and failure rules

- Apply `ValidateKeyName` to explicit get/set/unset names: uppercase ASCII letter
  first, then uppercase ASCII letters, digits or underscores. Do not normalize
  a rejected name silently.
- Compare the entry routes under [EnvironmentCaster](README.md#environmentcaster)
  and [ValidateTypes](README.md#validatetypes). DotEnv prefix recognition is exact
  and unstripped; caster construction and `parseTyped` normalize prefixes;
  `to()` requires an exact lowercase string or enum member; hinted `Env.set`
  normalizes case through the validator but does not strip hint whitespace.
- Preserve demonstrated parser differences: fast `bool:maybe` is `False`, full
  boolean parsing raises `ValueError`; fast `str:` is empty text, full parsing
  fails. Keep container literals in Python syntax, not invented JSON semantics.
- Do not assume a hint proves value compatibility. Hinted writes reject `None`,
  `bytes` and `Path` before conversion; unhinted writes are more permissive than
  their annotation. Direct caster serialization accepts a different input set.
- Decode a serialized result with a new caster or `parseTyped`. `to()` changes
  the existing instance's hint but retains the original raw value and references,
  including after some conversion failures. Do not share this mutable state
  without considering the [concurrency limits](README.md#performance-and-concurrency).
- Preserve actual exceptions: invalid names and conversions use `ValueError`,
  incompatible categories use `TypeError`, unknown textual write hints use
  `RuntimeError`; full reload failures are chained `RuntimeError`, not `False`.
  Keep filesystem/dependency errors visible and account for partial store updates.
- Read path/Base64 limitations before treating either codec as normalization or
  encryption. Paths do not resolve `..`; relative `~` is joined before expansion.
  Base64 decoding returns text or bytes, while encoding rejects non-UTF-8 bytes
  and preserves already-valid encoded text.
- Use [SecureKeyGenerator](README.md#securekeygenerator) with the real `Cipher`
  values and size mapping. Never log generated key material or assume `Env.get`
  always returns bytes for `APP_KEY`. Verify the [real App integration](README.md#integrating-with-app-configuration)
  when investigating defaults, generated-key persistence or frozen config values.

## Validate within the authorized scope

1. Use the repository virtual environment and compare
   [declared and resolved versions](README.md#compatibility-notes).
   Do not install dependencies or alter lockfiles merely to run a probe.
2. Run each [complete example](README.md#usage-examples) in its own fresh process,
   changing to a temporary working directory before imports. Restore environment
   and working directory in `finally`; keep bytecode, reports and application
   resources outside the checkout when write isolation is required. Confirm
   loaded module paths point to the inspected local code.
3. Separate syntax, real import resolution and execution results. Copying literal
   reference headers into a script does not supply their missing bodies. Assert
   types, identities and stable results; do not benchmark or infer concurrency
   guarantees from unrelated checks.
4. Follow [verification and limitations](README.md#verification-and-limitations)
   for evidence and test counts. Use the framework's native runner, not direct
   `unittest`. When checkout runtime writes are authorized, the existing commands
   from the repository root are:

```powershell
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -B reactor test --start-dir="tests/environment" --verbosity=2
.\.venv\Scripts\python.exe -B -m ruff check --no-cache orionis/environment tests/environment
```

5. If writes must stay outside the checkout, use a temporary `Application` with
   the native `TestingEngine` and unchanged copied tests as described in the
   README's [executable checks](README.md#executable-checks). Inspect raw failures,
   errors and the expected nonzero discovery count, not only printed summaries.
   Review test and bootstrap effects before executing; block unauthorized writes
   and external services. Close logging handlers before deleting a booted
   temporary application on Windows.
6. Report missing sources, dependencies or execution capability precisely. Mark
   checks as executed, failed or not executed and distinguish unspecified
   contracts from unavailable evidence. Do not convert installed dependency
   observations into promises for every version in the allowed range.
7. Modify framework implementation only for an explicit change request and only
   inside its authorized scope. Preserve preexisting work; do not refactor code
   while performing a documentation-only task.

Keep this file as an operational entry point. Its location does not install,
register or package the skill automatically.
