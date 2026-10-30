# Authentication and authorization

Orionis resolves the current identity through browser sessions or personal access tokens and evaluates permissions, roles and policies. Context belongs to a request; shared services do not retain a global user.

1. [Identity and session login](identity-and-session.md): models, guards, login and logout.
2. [Permissions, roles and policies](authorization.md): protect capabilities and resources.
3. [Personal access tokens](personal-access-tokens.md): issue, restrict and revoke credentials.
4. [Remember-me and account recovery](account-recovery.md): persistent cookies, resets and default pages.

Requires Python 3.14+, a configured ORM identity model, hashing and authentication migrations for persistence. Facade/repository examples require a booted application; snapshot examples are independent. Review [sessions](../../../session/docs/en/README.md), [HTTP](../../../http/docs/en/README.md) and [ORM](../../../orm/docs/en/README.md).

## Bounded execution and performance

The native model provider and token repository combine the token and identity SELECT when they share a native connection, the key is integer/string, and scopes preserve a simple query shape. Scope filters, hydration, retrieved events and eager relations are retained. Token metadata is validated before identity events; the guard still issues its final conditional `last_used_at` update, rechecking revocation and expiration after identity resolution. The supported path uses two database statements rather than three and never caches an authentication decision.

Custom providers/repositories/connections, UUID keys, separate databases and complex scoped queries use the original lookup path. SQL casts of stored integer owner keys are guarded against malformed/out-of-range values. Backend SQL compilation does not replace integration testing against each deployed database engine.
