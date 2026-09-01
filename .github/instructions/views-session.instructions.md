---
name: "Orionis Views, Session and Flash"
description: "Use when working with Orionis views: async Jinja2 environment, template globals, filters and extensions, PendingView, bytecode cache, and with sessions, flash namespaces (old input, errors, messages), previous URL tracking and CSRF tokens."
applyTo: "orionis/view/**,orionis/session/**,resources/views/**,**/*.html"
---

# Views, session and flash

## Read the module docs first

| Topic | Manual |
|---|---|
| `ViewEnvironment`, `Jinja2Engine`, `ViewFactory`, `PendingView`, `OrionisBytecodeCache`, `CsrfExtension`, the full list of globals/filters, `ErrorBag`, config keys | `orionis/view/docs/README.md` (`.es.md`) |
| `Session`, `SessionManager`, the 4 stores, `SessionRecord`, flash helpers, cookie attributes | `orionis/session/docs/README.md` (`.es.md`) |

Those manuals carry the exact signatures and executed examples. **Do not restate
them here and do not guess an API without checking them.** What follows are the
invariants and traps that the docs do not enforce.

## View invariants

- The pipeline is `ViewEnvironment` → `Jinja2Engine` → `ViewFactory` →
  `PendingView` → `HTMLResponse` (header `X-Orionis-Render: SSR`).
- `ViewEnvironment` is the **only** class allowed to touch the
  `jinja2.Environment` directly, and it builds it exactly once at boot.
  `enable_async=True` is always forced — there is no config flag for it.
- `Jinja2Engine.render()` must always use `render_async`, never Jinja's sync
  `render()`.
- `PendingView.render()` re-raises `ViewTemplateNotFoundException` **before** the
  generic `except Exception` that wraps everything else in `ViewRenderException`.
- Globals live in `orionis/view/globals/` (one file per category, each exposing a
  `_global_*` builder), filters in `orionis/view/filters/`, extensions in
  `orionis/view/extensions/`. `ViewServiceProvider.boot()` assembles the dicts by
  calling each builder — there is no `buildViewGlobals()` helper any more.
- Adding a global means updating `_EXPECTED_GLOBALS` in
  `tests/view/test_provider.py`.
- Cache keys must stay collision-free: the bytecode cache appends 8 hex of sha1 to
  the readable stem, because the plain `/`→`.` transform made `mail/welcome.html`
  and `mail/welcome.j2` share one file.

**Async templates.** With `enable_async=True`, Jinja wraps every call in
`await auto_await(...)`, and `auto_await` passes non-awaitables through. That is
why a global that is an *object with async methods* works with natural syntax:

```jinja
{% if errors.any() %}{{ errors.first('email') }}{% endif %}
{{ old('email') }}
```

## Session invariants

- `SessionManager` is **not registered by any provider** — the container
  autoconstructs it in `KernelHTTP.boot()` while building
  `StartSessionMiddleware`, so there is exactly one instance per process.
- Sessions exist only in the **web** pipeline; API routes have none.
- The `Session` facade is pinned/unpinned **per request** inside
  `StartSessionMiddleware`. Concurrent code must read `request.state.session`.
- `StartSessionMiddleware.__storeCurrentUrl()` records
  `setPreviousUrl(request.url)` for GET/HEAD, non-AJAX, non-3xx responses — that
  is what makes "redirect back" work.
- The session is not lazy in practice: `CSRFTokenMiddleware` writes to it on every
  web request, so anonymous visitors do get a cookie (same as Laravel). Do not
  document it as "zero cost".

## Flash: three namespaces, one writer and one reader each

| Namespace | Key | Write | Read |
|---|---|---|---|
| Old input | `_old_input` | `flashInput()` / `Response.withInput()` | `getOldInput()` / global `old()` |
| Errors | `_errors` | `flashErrors()` / `Response.withErrors()` | `getErrors()` / global `errors` |
| Messages | free | `flash(key, value)` / `withFlash(key, value)` | `getFlash(key)` / global `flash()` |

- `SENSITIVE_INPUT_FIELDS` (`password`, `password_confirmation`,
  `current_password`, `new_password`, `_csrf`, `csrf_token`) are **never** flashed.
- `getFlash()` reads `_flash_new` before `_flash_old` — that is what makes
  re-render without redirect work. It is the **only** flash reader; `getOld()` and
  `hasFlash()` were deliberately removed.
- Route reserved keys through `apply_flash(session, data)`; iterating
  `session.flash(k, v)` manually overwrites the reserved bags instead of merging.
- `normalize_errors()` accepts a `Mapping`, `exc.errors` or `exc.failure`
  (duck-typed so `session` never imports `schemas`).

## Traps

- `await response.view(...)`; **never** `await response.redirect(...)` — a
  redirect is already a real `Response` and awaiting it raises `TypeError`.
- File-backed stores must write through a **uniquely named** temp file
  (`f"{name}.{secrets.token_hex(8)}.tmp"`) plus a lock and retries around
  `replace()`; a fixed `.tmp` name corrupts concurrent writes and fails on Windows.
- Session expiry is stored as a whole-second epoch `int` (`BigInteger` column):
  do not write floats there.
