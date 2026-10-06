---
name: "orionis-auth"
description: >-
  Use when understanding, integrating, or troubleshooting orionis.auth session
  and opaque-token authentication, scoped permissions and policies, remembered
  login, or password-reset credentials. Inspect the local implementation and
  bundled documentation to select verified APIs and validate proposed usage.
---

# Work With orionis.auth

## Establish Scope

Locate the module at this file's parent directory's parent, `orionis/auth`.
Read [README.md](README.md), or [README.es.md](README.es.md) for Spanish prose.
Use the [file map](README.md#module-structure) to identify the owning implementation.
Treat this skill as a repository-local entry point, not an installed or
automatically registered agent capability.

Expect VS Code's skill validator to flag the folder/name mismatch in this
requested layout and possibly interpret Markdown fragments as file paths.
Verify the actual target file and heading independently. Preserve the
module-derived name and authorized location when that layout is required;
do not change registration or editor configuration merely to silence it.

Modify framework source only when an explicit request authorizes that change,
and remain within that request's write scope. Do not turn a documentation or
explanation task into a source fix. Prefer implemented behavior over a conflicting
docstring and report the distinction.

## Select Verified APIs

Check [exports and imports](README.md#exports-and-imports) before choosing imports.
Use the actual `AuthManager` contract or the external
`orionis.support.facades.auth.Auth` facade; do not confuse that facade with the
foundation configuration entity named Auth. Import `PasswordBroker` from
`orionis.auth.passwords.broker`, not the empty passwords initializer.
Resolve facade timing from [AuthProvider](README.md#authprovider): register is not
boot, and synchronous facade calls need its manager pinned. Use the implemented
`Application.boot()` when a headless task requires eager-provider startup.

Compare the relevant [API reference](README.md#api-reference), declared contracts
and the linked source before proposing code. Preserve async/sync distinctions,
keyword-only arguments and raw defaults; do not evaluate missing TYPE_CHECKING
annotations to reconstruct signatures. Treat the declaration blocks as reference
fragments, not runnable scripts.

## Respect Behavioral Boundaries

- Consult [identity concerns](README.md#identity-concerns) and
  [ModelIdentityProvider](README.md#modelidentityprovider). Use the plain virtual
  mixins with ORM models; supply metadata/columns as well as the identity contract.
  Submit the password under `password`, even when AUTH_PASSWORD names another hash
  column. Do not assume username normalization or model-class cache invalidation.
- Consult [context and scope helpers](README.md#authenticationcontext-and-scope-helpers).
  Bind a fresh context in an active scope. Do not retain bound identity-bearing
  contexts in a singleton or move them between scopes. Preserve stale-context
  ownership checks and rechecks around awaited I/O. Distinguish an active scope
  from the Request binding required for manager session transitions.
- Consult [SessionGuard](README.md#sessionguard) and [RememberMe](README.md#rememberme).
  Start the request session first; password verification and activation are done
  by attempt, not direct login or every resolution path. Persistent issuance
  requires HTTPS by default and a nullable remember_token with provider CAS
  support. Keep the original expiry during rotation and apply queued response
  cookies through the web pipeline. Do not wrap an already-async hasher call in
  to_thread and accidentally leave its returned coroutine unawaited.
- Consult [AccessTokenRepository](README.md#accesstokenrepository),
  [TokenGuard](README.md#tokenguard) and [AuthManager](README.md#authmanager).
  Store only token digests; expose the issuance secret explicitly, never through
  logs or generic dataclass serialization. Preserve None-versus-empty abilities,
  exact ability membership and the conditional touch before publishing identity.
  Do not claim revocation cancels already-running work. Expect manager token
  issuance to reject a current non-null credential ID.
- Consult [authorization](README.md#authorizer-policy-and-policyregistry).
  Keep before hooks async and ability methods sync or awaitable. Require literal
  True to grant; check token abilities before hooks. Build policies per evaluation
  and cache only class lookups. Do not expect grants to refresh a loaded snapshot.
- Consult [middleware](README.md#middleware). Resolve identity before permission,
  role or policy gates; resolution alone permits guests. Declare real importable
  middleware subclasses with class-variable requirements. Do not assume role-only
  gates accept restricted tokens or that every gate adds Cache-Control.
- Consult [PasswordBroker](README.md#passwordbroker). Prepare the reset schema;
  recognize the hardcoded email lookup, normalized addresses, retained cooldown
  rows and one-use conditional consumption. Re-read the model after reset to see
  persisted changes; the returned instance is not refreshed. Treat password policy
  validation and email delivery as external responsibilities.

## Diagnose and Validate

Use [exceptions](README.md#exceptions) to distinguish authentication, authorization,
missing policy/guard, configuration and propagated database/hasher failures.
Check [requirements](README.md#requirements) for missing schema/session/settings
before treating a failure as an API defect. Use
[performance and concurrency](README.md#performance-and-concurrency) for lock
ownership, caches, materialization and conditional-write limits. Do not infer
thread safety or cross-loop reuse from an async declaration or a local lock.

Start with the relevant existing tests under `tests/auth`. Use the repository
venv and native Reactor runner from the repository root when its runtime writes
are authorized:

```powershell
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe -B reactor test --start-dir="tests/auth" --verbosity=2
```

Use file-name patterns, not file paths, with the runner's file-pattern option.
Require a nonzero expected discovery count and inspect FAILED and ERRORED results;
native status values are uppercase. For documentation-only checks, preserve the
write boundary by using a temporary application/test tree, temporary storage and
disabled test-result caching, as described under
[verification](README.md#verification-and-limitations). Close connections and log
handlers before deleting Windows temporary directories. Disable bytecode writes
when imports must not create repository artifacts.

Extract [usage examples](README.md#usage-examples) as independent scripts. Check
syntax, verify imported module paths point to the local code, execute isolated
assertions, and report those three checks separately. Never use real credentials,
remote services or production migrations as a documentation probe. Keep
temporary validation scripts and reports outside the repository. Run the
existing Ruff check only on authorized Python changes, without autofix, when a
future source-edit task requires it.

Consult [compatibility](README.md#compatibility-notes) before claiming support.
Distinguish declared constraints, locked versions and the interpreter actually
used. Report missing files/dependencies or unavailable services explicitly, and
label a contract gap, unavailable evidence and an unexecuted check separately.
Do not invent a substitute import, expected output, deployment guarantee or
successful validation result.
