# Authentication and authorization

Orionis resolves the current identity through browser sessions or personal access tokens and evaluates permissions, roles and policies. Context belongs to a request; shared services do not retain a global user.

A retained context becomes a guest when replaced or when its request scope closes. Permission readers check that ownership again after waiting for another reader. Session operations queued behind another authentication transition also require a live request before invoking the guard.

Public contracts resolve lazily from `orionis.auth.contracts`. Direct module imports and package reexports retain the same type identities without circular guard/entity initialization.

1. [Identity and session login](identity-and-session.md): models, guards, login and logout.
2. [Permissions, roles and policies](authorization.md): protect capabilities and resources.
3. [Personal access tokens](personal-access-tokens.md): issue, restrict and revoke credentials.
4. [Remember-me and account recovery](account-recovery.md): persistent cookies, resets and default pages.

Requires Python 3.14+, a configured ORM identity model, hashing and framework authentication storage for persistence. Facade/repository examples require a booted application; snapshot examples are independent. Review [sessions](../../../session/docs/en/README.md), [HTTP](../../../http/docs/en/README.md) and [ORM](../../../orm/docs/en/README.md).

## Prepare authentication storage

For a new database, apply application migrations, prepare the internal auth tables, and then run application seeders:

```shell
python -B reactor migrate
python -B reactor auth:migrate
python -B reactor seed
```

`auth:migrate` creates roles, permissions, their three assignment tables, personal access tokens, and password-reset storage from core definitions. It uses the application's default SQL connection and honors its prefix, `AUTH_TOKEN_TABLE`, and `AUTH_PASSWORD_RESET_TABLE`. Repeated runs preserve existing records; the command does not create users, grant privileges, execute seeders, or write application migration history.

Keep the identity model and its migration, application-specific role/permission names, assignments, and resource policies in the application. See [framework storage preparation and upgrade precautions](../../../database/docs/en/migrations-and-seeders.md#prepare-framework-storage-tables).

## Bounded execution and performance

The native model provider and token repository combine the token and identity SELECT when they share a native connection, the key is integer/string, and scopes preserve a simple query shape. Scope filters, hydration, retrieved events and eager relations are retained. Token metadata is validated before identity events; the guard still issues its final conditional `last_used_at` update, rechecking revocation and expiration after identity resolution. The supported path uses two database statements rather than three and never caches an authentication decision.

Custom providers/repositories/connections, UUID keys, separate databases and complex scoped queries use the original lookup path. SQL casts of stored integer owner keys are guarded against malformed/out-of-range values. Backend SQL compilation does not replace integration testing against each deployed database engine.
