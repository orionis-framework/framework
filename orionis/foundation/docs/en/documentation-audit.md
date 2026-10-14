# Phase 1 documentation audit

Reviewed on October 14, 2026 against Orionis `0.901.0` in the `framework/` Git root. This phase rebuilds manuals and proposes navigation; it does not publish the Astro portal. The following matrix comes from the final inventory, not planned page counts. Counts include each language README and this report.

## Coverage by module

| Module | ES | EN | Parity | Status | Covered capabilities |
|---|---:|---:|---|---|---|
| [aio](../../../aio/docs/en/README.md) | 2 | 2 | Verified | Complete | Event loops, execution, and sync/async bridging |
| [auth](../../../auth/docs/en/README.md) | 5 | 5 | Verified | Complete | Identity, guards, authorization, remember, and recovery |
| [background](../../../background/docs/en/README.md) | 2 | 2 | Verified | Complete | Post-response tasks, ordering, and failures |
| [cache](../../../cache/docs/en/README.md) | 4 | 4 | Verified | Complete | Values, stores, locks, and source artifacts |
| [console](../../../console/docs/en/README.md) | 5 | 5 | Verified | Complete | Commands, arguments, output, and scheduler |
| [container](../../../container/docs/en/README.md) | 4 | 4 | Verified | Complete | Bindings, invocation, scopes, providers, and facades |
| [database](../../../database/docs/en/README.md) | 6 | 6 | Verified | Complete | Connections, SQL, transactions, schema, migrations, and seeders |
| [encrypter](../../../encrypter/docs/en/README.md) | 2 | 2 | Verified | Complete | AES ciphers, keys, portable format, and authenticity |
| [environment](../../../environment/docs/en/README.md) | 3 | 3 | Verified | Complete | Types, persistence, reloads, and keys |
| [failure](../../../failure/docs/en/README.md) | 3 | 3 | Verified | Complete | Reporting, dispatch, HTTP/CLI policy, and extension |
| [foundation](../../../foundation/docs/en/README.md) | 8 | 8 | Verified | Complete | Installation, creation, lifecycle, config, paths, and deployment |
| [hashing](../../../hashing/docs/en/README.md) | 2 | 2 | Verified | Complete | Algorithms, verification, and rehashing |
| [http](../../../http/docs/en/README.md) | 10 | 10 | Verified | Complete | Routing, requests, uploads, responses, middleware, SSE, and WebSocket |
| [introspection](../../../introspection/docs/en/README.md) | 3 | 3 | Verified | Complete | Reflection, signatures, dependencies, and discovery |
| [localization](../../../localization/docs/en/README.md) | 2 | 2 | Verified | Complete | Catalogs, locale selection, and concurrency |
| [logging](../../../logging/docs/en/README.md) | 3 | 3 | Verified | Complete | Channels, rotation, lifecycle, and failures |
| [mail](../../../mail/docs/en/README.md) | 4 | 4 | Verified | Complete | Declarations, MIME composition, attachments, transport, and results |
| [mcp](../../../mcp/docs/en/README.md) | 6 | 6 | Verified | Complete | Servers, tools, schemas, resources, prompts, transports, and extensions |
| [metadata](../../../metadata/docs/en/README.md) | 1 | 1 | Verified | Complete | Identity, release, and Python compatibility |
| [orm](../../../orm/docs/en/README.md) | 7 | 7 | Verified | Complete | Models, attributes, queries, relationships, events, scopes, and factories |
| [queues](../../../queues/docs/en/README.md) | 4 | 4 | Verified | Complete | Dispatch, drivers, workers, reservations, retries, and failures |
| [realtime](../../../realtime/docs/en/README.md) | 4 | 4 | Verified | Complete | RPC hubs, remote methods, and per-worker limits |
| [schemas](../../../schemas/docs/en/README.md) | 5 | 5 | Verified | Complete | Declarations, conversion, rules, errors, and async validation |
| [session](../../../session/docs/en/README.md) | 4 | 4 | Verified | Complete | Stores, cookies, flash, rotation, and concurrency |
| [storage](../../../storage/docs/en/README.md) | 4 | 4 | Verified | Complete | Disks, files, directories, streaming, and cloud drivers |
| [support](../../../support/docs/en/README.md) | 4 | 4 | Verified | Complete | Collections, strings, entities, dates, and utilities |
| [test](../../../test/docs/en/README.md) | 4 | 4 | Verified | Complete | Async cases, DI, discovery, results, and MCP client |
| [view](../../../view/docs/en/README.md) | 4 | 4 | Verified | Complete | Jinja templates, contexts, autoescaping, and extensions |

All 28 modules have rebuilt official manuals. Parity covers files, chapters, imports, principal examples, and reviewed warnings; all 204 Python blocks per language are identical; automated code-shape checks complement editorial review. The `http/default` directory supplies two auxiliary indexes, one per language, pointing to HTTP rather than a separate manual.

## Files and previous material

Each module receives `docs/es/README.md`, `docs/en/README.md`, and the following chapters with matching filenames. Previous manuals were reviewed, valid technical content was migrated, and API discrepancies were corrected. Implementation references complement rather than replace tutorials.

- `aio`: `async-execution.md`.
- `auth`: `account-recovery.md`, `authorization.md`, `identity-and-session.md`, `personal-access-tokens.md`.
- `background`: `response-tasks.md`.
- `cache`: `caching-values.md`, `source-artifacts.md`, `stores-and-locks.md`.
- `console`: `built-in-commands.md`, `commands-and-arguments.md`, `output-and-programmatic-execution.md`, `task-scheduling.md`.
- `container`: `bindings-and-invocation.md`, `providers-and-facades.md`, `scopes-and-concurrency.md`.
- `database`: `connections.md`, `dialects-and-production.md`, `migrations-and-seeders.md`, `schema.md`, `transactions.md`.
- `encrypter`: `encrypting-values.md`.
- `environment`: `operations-and-reference.md`, `typed-configuration.md`.
- `failure`: `handling-exceptions.md`, `policies-and-reference.md`.
- `foundation`: `application-lifecycle.md`, `configuration.md`, `deployment-and-reference.md`, `documentation-audit.md`, `getting-started.md`, `installation.md`, `paths-and-caching.md`.
- `hashing`: `password-storage.md`.
- `http`: `default-responses.md`, `forms-and-uploads.md`, `middleware-and-security.md`, `request-lifecycle.md`, `requests-and-validation.md`, `responses.md`, `routing.md`, `streaming-and-sse.md`, `websockets.md`.
- `introspection`: `dependencies-and-discovery.md`, `reflection.md`.
- `localization`: `translating-content.md`.
- `logging`: `rotation-and-lifecycle.md`, `writing-logs.md`.
- `mail`: `composing-mail.md`, `sending-and-results.md`, `transports-and-extensions.md`.
- `mcp`: `advanced-workflows.md`, `resources-and-prompts.md`, `responses-and-content.md`, `servers-and-tools.md`, `transports-and-configuration.md`.
- `metadata`: single manual in `README.md`.
- `orm`: `events-and-scopes.md`, `factories-and-testing.md`, `models-and-attributes.md`, `querying.md`, `relationships.md`, `schema-and-type-reference.md`.
- `queues`: `drivers-and-configuration.md`, `jobs-and-dispatch.md`, `workers-and-failures.md`.
- `realtime`: `groups-and-deployment.md`, `hubs-and-methods.md`, `protocol-and-streaming.md`.
- `schemas`: `application-rules.md`, `constraints-and-reference.md`, `declaring-schemas.md`, `validation-and-errors.md`.
- `session`: `configuration-and-security.md`, `state-and-flash.md`, `stores-and-concurrency.md`.
- `storage`: `disks-and-drivers.md`, `files-and-directories.md`, `streaming-and-uploads.md`.
- `support`: `collections-and-strings.md`, `entities-and-structures.md`, `facades-and-runtime-utilities.md`.
- `test`: `mcp-testing.md`, `results-and-reference.md`, `writing-and-running-tests.md`.
- `view`: `configuration-and-extensions.md`, `rendering-templates.md`, `template-language.md`.

Previous README paths provide compatibility. Two justified exceptions remain: Mail retains its 13-example catalog because `tests/mail/test_docs.py` consumes it, and the historical Spanish `http/default` benchmark report is retained with an explicit historical notice. Neither is a new-menu chapter or evidence of current testing. No additional `history/` copies were created.

## Verification performed

Checks used system CPython 3.14.3 with existing `.venv/Lib/site-packages` dependencies and `-B`. The `.venv` Python launcher could not start its interpreter under sandbox permissions; no dependencies were installed. Suites used an isolated container pinned to the Application facade without importing the real bootstrap.

| Check | Result |
|---|---|
| Metadata, schemas, container, environment, failure, introspection, and support | 3,025 tests passed |
| HTTP, auth, session, realtime, and MCP, selection without real services | 1,732 tests passed |
| Database, ORM, console, and queues, 18 focused modules | 442 tests passed |
| Mail documentation compatibility | 2 tests passed |
| Total approved selections | 5,201 tests, no failures or errors |
| Reproducible foundation programs | 40 standalone programs plus 3 real smokes: provider/facade, HTTP policy, and MCP client |
| Infrastructure | 48 executed snippets; additional background, four-template, and complete file-mail smokes |
| Web and protocol | 21 operational examples and three additional MCP progress/elicitation round trips |
| Persistence | Seven SQLite scenarios: CRUD, joins/aggregates/pagination, relationships/eager loading, factories/transactions, events/soft deletes, blueprint, and migration/seeder/rollback |
| Documentation Python | 408 compiled occurrences, including fragments requiring async context |
| Framework imports | 736 occurrences resolved against installed/local implementation |
| Direct-call signatures | 608 checked for argument compatibility; 44 additional calls on typed parameters checked |
| Local links | 1172 targets checked; no missing destinations |

Compiling a block or executing a function/class definition does not execute its handler. External services, real HTTP transport, SMTP, Redis, Memcached, cloud, and SQL dialects other than SQLite were checked statically. Those integrations were not certified. Three Realtime cases remained outside the approved selection: one needed real providers, and two Granian tests reached timeout/WinError32 during sandbox cleanup; their processes were identified and closed. These results are not attributed to a framework regression.

## Documented findings and limitations

- Constructing `Schema` does not validate external input; use `Validator`. Unknown fields require the appropriate rejection option.
- `Response.json`, `Tool(name=..., handler=...)`, `Cache.put`, and `Collection.toList` are not these APIs. Examples now use `JSONResponse`, `Tool` subclasses, `set(..., ttl=...)`, and `all()`.
- `Application.compile()` returns `None`. Creation, eager boot, and HTTP readiness are separate stages; scopes clear references rather than closing arbitrary resources.
- Application debug/production flags are cached at creation; runtime config changes do not universally reconfigure existing managers.
- `SeederRunner.seed()` has no class-selection or `force` arguments; timestamps and soft deletes require explicit columns. `Model.create()` returns an instance even when an event vetoes `save()`.
- Bulk update/delete do not run per-instance events or apply read limits. Pivot has no `updateExistingPivot`; `sync()` does not automatically open a transaction.
- MIME preparation and attachment reads are sequential and complete in memory; file transport STORED is not SMTP delivery.
- `Tool` handlers return `McpResponse`; a raw return value may compile without working in dispatch. The default email verification link encrypts identity without a dedicated expiry, and default registration may expose `str(exception)`; both need application policy.
- Locale is shared state; select it explicitly per request. Default Realtime and MCP event buses are worker-local.
- CBC and GCM have different guarantees; locks/leases, file expiry, cloud spooling, scheduler, and retries have limits explained in their manuals.
- `Stringable.toHtmlString()` uses `html.escape`; `forPage(page, number)` normalizes page values below 1. Tests do not automatically roll back cache or database data.

Potential implementation issue for tools: `inspect.signature(AuthorizationSnapshot)` fails because `Iterable` is imported only under `TYPE_CHECKING` in [snapshot.py](../../../auth/authorization/snapshot.py). The `NameError` was reproduced; `annotation_format=annotationlib.Format.STRING` and direct construction work. The implementation was not changed.

## Navigation and Phase 2 readiness

[documentation-menu.proposal.json](../../../../documentation-menu.proposal.json) is in the actual Git root. It contains 11 main sections, 115 conceptual pages with ES/EN sources, and two explicitly unpublished localized auxiliary-index files. The default locale is `en`; proposed public paths share the same suffix after `/en/` and `/es/`. Validation checks IDs, order, parentId, unique slugs, existing sources, parity, and complete coverage without orphaned publishable pages.

Manuals use portable Markdown and remain in their modules. Astro was not changed: no content was copied, nothing was installed, and no routes or i18n were activated. Phase 2 must transform relative cross-module links to public routes and resolve source/test links through repository URLs or a resource policy; the JSON is a proposal rather than active Astro configuration. Markdown does not require MDX or portal-specific components.

[Return to foundations](README.md).
