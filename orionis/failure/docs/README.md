# Authentication errors in the failure pipeline

`Catch.exception()` selects the current kernel from the container scope, reports
the exception through the configured handler and invokes its CLI or HTTP method.
`BaseExceptionHandler` maps exception classes and their ancestors to HTTP statuses.

| Exception family | Status |
|---|---|
| `AuthenticationException` | 401 |
| `AuthorizationException` | 403 |
| `CSRFTokenMismatchException` | 419 |
| Unmapped errors | 500 |

Auth failures use fixed public messages, not submitted credentials. Token-guard
authentication failures add `WWW-Authenticate: Bearer`. Standard content
negotiation still chooses HTML or JSON. Application subclasses preserve the
status of their mapped Auth ancestor.

Web Session middleware catches ordinary downstream exceptions before persisting
the response, so logout and flash changes survive an error response. Cancellation
is propagated after pending session revocation is persisted. The outer HTTP scope
always closes normally or exceptionally.

Query errors omit driver details and bound values at the database boundary.
Applications must also avoid putting passwords, raw tokens or cookies in custom
exception messages and logs. Debug pages must not be enabled in production.

See [Auth](../../auth/docs/README.md) for the authentication/authorization contract.
