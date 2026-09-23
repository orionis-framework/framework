# Default response service

`DefaultResponses` renders built-in pages through the injected `IViewEngine` and
serves allowlisted packaged assets. See [the performance review](README.es.md)
for the measured findings, implementation trade-offs and validation results.

## Lifetime and cache policy

The HTTP kernel retains its bootstrapped service for routes whose controller is
exactly `DefaultResponses`. Other controllers are still constructed per request.
Each call creates a new response with its own mutable headers, flash state and,
for files, stream iterator.

Health HTML retains up to two immutable encoded bodies. Maintenance is read on
each call. Changes to application name or locale invalidate both bodies. A
suspended render only publishes its result if those labels still match. Every
engine invocation receives a separate context dictionary. Error and exception
pages are rendered per request; their payloads and tracebacks are not cached.

Asset paths are cached only after an exact allowlist lookup, with at most six
entries. Files are stat-validated on every response construction. Neither file
contents, stat results nor failed existence checks are cached. Known content types
are passed explicitly to `FileResponse`; there is no MIME inference or separate
existence precheck. The actual file open and reads happen when consuming the stream.

Public favicon, robots and sitemap routes retain their selected path until it
becomes unavailable or the selection is explicitly removed. Creating a new
higher-priority public file requires deleting the corresponding cache entry
(`favicon`, `robots_txt` or `sitemap_xml`) or restarting the service. Existing
selected files still reflect content and size changes. Missing selected files
trigger candidate selection again, with the configured packaged fallback or 404.

## Internal metadata

Fixed header dictionaries are private response inputs; the response constructor
copies their entries. Error cache policy is checked against the already-normalized
response headers, preserving caller mappings and case-insensitive overrides.
Template names and runtime versions are precomputed. Environment, debug state,
interface and timezone remain live exception context values.

The class and its ABC both declare slots. Subclasses can declare additional fields
when needed. Methods follow camelCase, module functions follow snake_case, and
Python protocol methods retain their required special names.

## Verification

The targeted suites pass: 25 default-page tests, 52 kernel tests, five HTTP
convention tests and 89 failure-handling tests. The full HTTP run passes 705 of
706 tests; the existing `Router.auth` / `IRouter.auth` signature mismatch is
independent of this service. Ruff and the local SonarPython analyzer report no
issues in the six reviewed files; the latter ran 398 active Python rules.

Benchmarks compare the previous and current service with the real official engine
on CPython 3.14.3 / Windows 11. They measure construction, excluding DI, middleware,
network and file streaming. Local diagnostic artifacts and reproduction commands
are in `storage/framework/default-responses-review/`. Do not interpret these
microbenchmarks as end-to-end HTTP throughput or free-threaded concurrency claims.
