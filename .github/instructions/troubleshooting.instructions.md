---
name: "Orionis Troubleshooting"
description: "Use when debugging unexpected Orionis behaviour: a facade returns _FacadeDispatch, a service or command is not registered, TypeError about ABCMeta, dependency injected as str, missing __slots__ leaking __dict__, stale storage/framework/bootstrap cache, corrupted concurrent file writes, PermissionError on Windows, sqlite :memory: concurrency, dialect-dependent float truncation, module shadowing from __init__.py, or a check-then-act race across an await."
---

# Troubleshooting Orionis

Known failure modes and their real root cause. Check this list **before**
theorising, then confirm the intended behaviour in the module's own manual
(`orionis/<module>/docs/README.md`, or `orionis/orm/README.es.md`). `database`,
`failure`, `foundation`, `http` and `metadata` have no manual — read their code.

## Startup and compiled cache

| Symptom | Root cause | Fix |
|---|---|---|
| A facade returns `_FacadeDispatch`, a new command is "not found", `TypeError: X.__init__() got an unexpected keyword argument` | `storage/framework/bootstrap` is stale. `compiled_invalidation_paths` covers `app`, `bootstrap`, `config`, `resources`, `routes` and `.env` — **not `orionis/`** | Delete `storage/framework/bootstrap` (or run `reactor optimize:clear`) after touching a provider, a core command or a config entity |
| A route registered ad hoc in a script does not exist | With `compiled=True` the `RouteLoader` reads the disk cache | Declare it in `routes/web.py` (that invalidates by mtime) and `await Route.pin()` |
| `await app.make(IThing)` fails in a standalone script | `boot()` of eager providers only runs in `Application.__onStartup()` (HTTP/CLI runtime). `import bootstrap.app` creates but does not start the app | Resolve the manager contract explicitly, or `await Facade.pin()` |
| Importing anything from `orionis.*` creates/writes `.env` in the CWD | `core_config.py` builds `App()` at module level and `App.__post_init__` generates `APP_KEY` | In probes, `os.chdir(tempdir)` **before** the import |

## Dependency injection

| Symptom | Root cause | Fix |
|---|---|---|
| A dependency arrives as `str` / `'str' object has no attribute 'basePath'` | The class uses `from __future__ import annotations`; reflection treats annotations as string forward refs | Remove the future import; import constructor types at runtime with `# ruff: noqa: TC001` |
| `TypeError: Argument 'concrete' must be a class type, got 'ABCMeta' instead.` | A constructor parameter is typed with an ABC that has no explicit binding | Register `self.app.singleton(IThing, Thing)` in the provider **before** whatever consumes it |
| `'coroutine' object has no attribute 'set'` / a coroutine stored as if it were a service | A facade was used while still unpinned, inside something built during startup | Inject the contract through the constructor instead of using the facade |
| A singleton is constructed more than once, or a deferred provider registers twice | check-then-act across an `await` | Guard with the container creation lock pattern (double-checked locking + recursion guard) |

## Classes and layout

| Symptom | Root cause | Fix |
|---|---|---|
| Instances still have `__dict__` despite declaring `__slots__` | The ABC in `contracts/` does not declare `__slots__ = ()` | Add it — verify with `hasattr(obj, "__dict__") is False` |
| An `abstractmethod` "works" when called via `super()` | The abstract method has a body (dead code) | Empty it |
| `import a.b.c as x` returns a function instead of the module | `__init__.py` exports a symbol whose name matches a sibling submodule, permanently shadowing it | Rename the module (this is why `response.py` → `responses.py` and `env.py` → `facade.py`) |

## Concurrency and files

| Symptom | Root cause | Fix |
|---|---|---|
| Mixed/corrupted file contents, `FileNotFoundError` on replace | Fixed-name temp file (`path.with_suffix(".tmp")`) shared by concurrent writers | `f"{name}.{secrets.token_hex(8)}.tmp"` + `except OSError: tmp.unlink(missing_ok=True); raise` |
| `PermissionError [WinError 5 / 32]` on `Path.replace()` | Windows limitation when the destination is being replaced concurrently | `threading.Lock` around the rename plus a few 5 ms retries; assert **integrity**, not "all writes succeed" |
| Concurrency test passes/fails nonsensically on sqlite | `:memory:` uses `StaticPool` — all tasks share one DBAPI connection, so one task's `ROLLBACK` undoes another's `INSERT` | Use a temp **file** database for concurrency tests |
| Sub-second TTLs or lock leases expire immediately (PostgreSQL only, fine on sqlite) | A float stored in a `BigInteger` column is truncated silently by PG | Use a `Double` column, and update the real migration too — `createTable` is `IF NOT EXISTS` |

## HTTP and views

| Symptom | Root cause | Fix |
|---|---|---|
| `TypeError: Route handler must return a Response object` | A `PendingView` was returned without `await` | `await response.view(...)`; do **not** await `response.redirect(...)` |
| Redirect-back loses errors/old input, or lands on `/` | Under RSGI the URL was built from `scope["server"]` instead of the `Host` header, so the redirect changed origin and the browser dropped the session cookie | Resolve the host from the `Host` header (already fixed — do not regress) |
| A security rejection raises `TypeError` instead of returning 400 | `DefaultResponses.error()` was called with `description=` | The parameter is `content=` and it is required |
| A template-not-found error surfaces as a generic render error | A broad `except Exception` wrapped it | Re-raise `ViewTemplateNotFoundException` before the generic handler |
| CSRF failure hits the generic 500 page | Missing mapping | `CSRFTokenMismatchException` maps to 419 `PAGE_EXPIRED` |

## Console and scheduler

| Symptom | Root cause | Fix |
|---|---|---|
| `TypeError: cannot pickle 'mappingproxy' object` when scheduling | The job callable is a bound method, so APScheduler pickles `self` → `Schedule` → `Application` | Use a module-level function resolvable as `module:function` |
| `ConflictingIdError` on the second `schedule:work` run | Persistent job store plus `replace_existing=False` | Keep `replace_existing=True` |
| Jobs get cancelled when one registration fails | `scheduler.start()` ran before the registration loop | Start after registering |
| A CLI flag such as `--fail-fast=0` is ignored | `cli_args.get(x) or app.config(...)` | Compare with `is None`; absent flags are filtered out by the `MISSING` sentinel |
| A suite with ERRORED tests exits 0 | Status compared against lowercase strings instead of the `TestStatus` enum | Compare enums |

## Fast diagnostic checklist

1. Is `storage/framework/bootstrap` stale? Delete it.
2. Is the app actually **booted** (HTTP/CLI) or just imported?
3. Is the facade pinned? Is its provider deferrable when it should be eager?
4. Does the failing class use `from __future__ import annotations`?
5. Does the ABC declare `__slots__ = ()`?
6. Is there a check-then-act across an `await`?
7. Is a fixed-name temp file involved?
8. Are you running with `.\.venv\Scripts\python.exe` and `PYTHONIOENCODING=utf-8`?
