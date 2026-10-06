---
name: "orionis-container"
description: >-
  Use when a task involves understanding, integrating, or troubleshooting
  the orionis.container module, service lifetimes, dependency injection,
  callable plans, deferred provider readiness, or global and scoped facades.
  Consult the bundled documentation and inspect the local implementation
  to select verified APIs, respect behavioral constraints, and validate usage.
---

# Work with orionis.container

Use this repository-local entry point with [README.md](README.md) or
[README.es.md](README.es.md). It does not install or register a platform skill.
Modify framework source only for an explicit request within its authorized scope.

## Locate the actual API

1. Start with [imports](README.md#imports-and-exports) and the
   [module map](README.md#module-structure). Import Container from
   `orionis.container.container`; the package root is empty. Use defining modules
   for ScopedFacade, metaclasses, scope classes and invocation-plan helpers.
2. Consult [literal declarations](README.md#literal-declarations), then inspect
   the linked implementation. Distinguish declared annotations, generated
   dataclass constructors, inherited methods and executed behavior. Do not invent
   Container.bind, reset, unbind, or disposal APIs.
3. Inspect [../container.py](../container.py),
   [../entities/invocation.py](../entities/invocation.py), and
   [../context/manager.py](../context/manager.py) for the controlling operation,
   rather than inferring behavior from an application/provider forwarding method.

## Preserve resolution semantics

- Follow [registration](README.md#container-identity-and-registration) and
  [dispatch](README.md#container-resolution-and-invocation). Container is singleton
  per subclass; a repeated constructor is not an empty registry. Registration
  aliases are stripped, lookup aliases are not. Global singleton hits precede
  scope hits. Override clears the global service cache, not old scopes/pins.
- Use make for lifetime resolution and build for the supplied concrete class.
  Build does not substitute a bound implementation or return the service cache;
  a class's own singleton __new__ remains its own behavior.
- Read [parameter injection](README.md#injected-parameters-and-schemas).
  Preserve explicit positional/keyword values, including None, before providers,
  schemas and typed bindings. Ordinary args/kwargs names remain injectable.
  Default-derived metadata and unresolved typing/str hints need separate handling.
- Verify available runtime types and constructor namespaces before diagnosing
  future annotations. Available module-global hints and class-local constructor
  references are supported; unknown hints are rejected, not injected as str.
- Inspect [plans](README.md#invocationplan-and-plan-functions). Bound method plans
  use underlying functions without retaining the receiver. Warm-up creates no
  controller. Callable/constructor replacement changes keys; mutating the same
  metadata object does not guarantee invalidation. Do not assume every callable
  object or partial passes reflection, or a sync-returned coroutine is awaited.

## Respect scopes, providers and facades

- Read [scopes](README.md#scopemanager-and-scopedcontext). ContextVar bindings are
  context-local, but children inherit the same mutable scope object. Enter managers
  once, restore tokens in the owning context, and check activity when lifetime
  matters. Raw current-scope access can return a closed object.
- Own cleanup explicitly. Clear/exit do not cancel tasks, close coroutines or
  dispose services. Scope get awaits Tasks, not every Future; a cancelled waiter
  can cancel a shared Task, and a late result cannot be published after closure.
- Consult [providers](README.md#serviceprovider-and-deferred-lifecycle).
  ServiceProvider.register and boot are no-ops by default; provides raises until
  overridden. Populate deferred metadata through actual Application configuration.
  Multicontract readiness uses provider identity; successful register is retained
  for boot retry, not rolled back. Do not publish an async register hook.
- Distinguish [Facade](README.md#facade-and-facademeta) from
  [ScopedFacade](README.md#scopedfacade-and-scopedfacademeta). Global dispatch needs
  a prepared application; unpinned calls require await or async-with. Pin retains
  the service on the class. Scoped dispatch requires an already-bound exact key
  in an active ScopeManager; its pin only validates availability.
- Use a sync method returning an async context manager for unpinned async-with.
  That path does not await a coroutine to obtain the manager. Do not chain pending
  dispatch objects as service proxies or infer request isolation from global pins.
- Consult [concurrency](README.md#task-scope-loop-and-thread-boundaries).
  Same-loop creation locks do not make registration or injected services safe
  across threads/loops. No global wait graph, transactional override, timeout,
  or automatic teardown is provided.

## Validate and report evidence

Read [verification](README.md#verification-and-limitations) and use the existing
[../../../tests/container](../../../tests/container). Standard project commands:

```powershell
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe -B reactor test --start-dir="tests/container" --verbosity=2
.\.venv\Scripts\python.exe -B -m ruff check --no-cache orionis/container tests/container
```

Review bootstrap/log/cache effects first. Under a read-only repository boundary,
use native TestingEngine/TestRunner with a temporary booted Application,
disabled result caching and correctly rooted discovery. Do not run the checkout
bootstrap when its writes cannot be isolated. Check nonzero discovery plus raw
failures/errors/skips. Preserve existing tests and changes outside the request.

Compile examples, verify imports point to the inspected checkout, and execute
them independently with bytecode disabled and temporary resources outside the
repo. Close logging handlers and restore cwd before Windows temporary cleanup.
Keep any write barrier compatible with asyncio's internal socketpair without
allowing arbitrary service connections. Compare ignored/untracked files too,
and preserve/report unrelated concurrent changes instead of reverting them.

State missing dependencies, files, configuration, services or execution capacity
precisely. Separate source contracts, observed behavior, executed cases, declared
version ranges and lockfile resolutions. Use the README uncertainty categories;
do not conceal a failed check or convert one-loop tests into universal guarantees.
