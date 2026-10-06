# orionis.auth

> `orionis.auth` authenticates HTTP requests through sessions or personal access tokens and evaluates permissions, roles, and resource policies in a request-scoped context.

## Overview

This module supplies Orionis's identity and authorization layer. Application code normally uses the `Auth` facade, adds `Authenticatable` and `Authorizable` to its identity model, declares `Policy` subclasses, and protects routes with middleware from `orionis.auth.middleware`.

The HTTP kernel resolves either the session or token guard and binds an `AuthenticationContext` to the current container scope. The singleton auth manager and middleware read that scoped context, so `Auth.user()`, permission checks, token abilities, and policies all refer to the current request. Supporting services persist permissions, roles, personal access tokens, remember-me credentials, and password-reset tokens through the ORM.

## Requirements

- Python 3.14 or newer.
- A normal Orionis installation; authentication has no optional installation extra.
- The configured identity must be an Orionis model implementing `IAuthenticatable`; add `Authorizable` when it owns permissions, roles, or personal access tokens.
- Session login requires an active HTTP request with session middleware. Token and authorization persistence require the auth migrations and a configured database connection.
- Password verification uses Orionis hashing. Remember-me login requires an identity column named `remember_token`, and its secure mode requires HTTPS.

## Quick start

Inside a booted Orionis request, the facade exposes the resolved identity and authorization snapshot:

```python
from orionis.support.facades.auth import Auth


async def profile_summary() -> dict[str, object]:
    if Auth.guest():
        return {"authenticated": False}

    return {
        "authenticated": True,
        "identifier": Auth.identifier(),
        "can_edit": await Auth.can("profile.edit"),
    }
```

The HTTP kernel establishes the context before the controller runs. `Auth.guest()` and `Auth.identifier()` are synchronous context reads; authorization checks are asynchronous because they may load a permission snapshot from the database.

Validation: **Import-validated only** on CPython 3.14.6; execution requires a booted application and active request scope.

## Core concepts

### Identity, guard, and context

An identity implements `IAuthenticatable`. A guard extracts credentials from a request and returns a `GuardResult`: the session guard reads the configured session key, while the token guard parses a Bearer token. `ResolveIdentityMiddleware` converts that result into an `AuthenticationContext` stored in the current container scope. A guest context has no identity and an empty authorization snapshot.

### Authentication versus authorization

Authentication answers who made the request. Authorization combines the identity's stored permissions and roles with an optional set of token abilities. Token abilities only narrow access:

```text
effective permission = identity permission AND (unrestricted token OR matching ability)
```

A restricted token cannot use role-only middleware, because capability authorization must be explicit.

### Permissions, roles, and policies

Permissions name capabilities such as `posts.update`; roles group permissions. Policies bind a resource class to methods such as `view`, `create`, or `update`. `Policy.before(identity, ability)` may return `True` or `False` to short-circuit an ability; its default `None` delegates to the named method. Policy classes are resolved through the container for each evaluation, so their constructors may request dependencies.

### Session and token credentials

Session login stores the identity identifier in the current request's session. Personal access tokens consist of stored metadata plus a secret returned only at creation. The repository stores a digest, not the plain secret; `NewAccessToken.toDict()` intentionally omits `plain_text`.

## Module structure

| Area | Responsibility |
|---|---|
| `manager.py`, `provider.py` | Facade-backed application API and container registration. |
| `context/`, `guards/`, `identity/` | Request-scoped identity state, session/token credential resolution, and model lookup. |
| `authorization/` | Permission/role snapshots, database repository, policy registry, authorizer, and registrar. |
| `middleware/` | Optional identity resolution and required authentication, permission, role, policy, or guest access. |
| `tokens/`, `entities/` | Personal access-token generation, hashing, persistence, metadata, and redacted issuance result. |
| `passwords/`, `remember.py` | Password-reset lifecycle and persistent browser login. |
| `concerns/`, `contracts/`, `exceptions.py` | Model mixins, extension interfaces, and module exception hierarchy. |

## Public API

### `Auth` facade and `AuthManager`

Use `from orionis.support.facades.auth import Auth`. `AuthProvider` binds `IAuthManager` as a singleton and pins the facade during boot. The main operations are:

| Operation | Result |
|---|---|
| `context()` | Current `IAuthenticationContext`. |
| `user()`, `identifier()` | Current identity or its identifier; `None` for guests. |
| `check()`, `guest()` | Synchronous authentication-state checks. |
| `guard(name=None)` | Named guard or configured default; raises `GuardNotFoundException` if missing. |
| `attempt(credentials, remember=False)` | Verify credentials and begin a session; returns `bool`. |
| `login(identity)`, `logout()` | Start or invalidate session authentication in the active request. |
| `authorization()` | Immutable authorization snapshot. |
| `can`, `cannot`, `canAny`, `canAll`, `hasRole` | Async permission and role queries. |
| `authorize(permission)` | Require a permission; raises 401/403-oriented exceptions. |
| `allows`, `denies`, `authorizeResource` | Evaluate or require a policy ability. |
| `registerPolicy(resource, policy)` | Bind a policy class to a resource type. |
| `createToken(...)` | Issue a personal access token for an authorizable identity. |
| `revokeCurrentToken()` | Revoke the credential used by this request, if any. |

`attempt`, `login`, and `logout` always use the session guard and require an active HTTP request. `createToken` accepts `name`, optional `tokenable`, `abilities`, and `expires_at`; token-authenticated requests may not mint another token.

### `Authenticatable` and `Authorizable`

Import these mixins from `orionis.auth`. `Authenticatable` derives the identifier attribute from ORM model metadata and reads the hash from `AUTH_PASSWORD`, which defaults to `"password"`. Override the class variable when the model uses a different column.

`Authorizable` supplies the polymorphic owner type and identifier used by permission, role, and token tables. `AUTHORIZABLE_TYPE` defaults to the model's dotted class path and may be overridden with a stable application-specific value. Both mixins are registered as virtual implementations of their contracts to avoid a metaclass conflict with `Model`.

### `Policy`

Subclass `Policy`, implement ability methods, and register the pair with `Auth.registerPolicy(Resource, ResourcePolicy)`. Ability methods receive the authenticated identity first and the resource instance or class second; they may be synchronous or asynchronous. Override `before` for a global decision.

### `AuthorizationSnapshot`

```text
AuthorizationSnapshot(
    permissions: Iterable[str],
    roles: Iterable[str],
    abilities: Iterable[str] | None = None,
)
```

The snapshot stores three immutable collections. `can(permission)` applies the token-ability intersection, while `hasRole(role)` checks roles directly. `abilities=None` means the credential does not narrow identity permissions; an empty iterable allows none.

### Route middleware

Import middleware from `orionis.auth.middleware`:

- `ResolveSessionIdentityMiddleware` and `ResolveTokenIdentityMiddleware` establish identity but allow guests.
- `AuthenticateMiddleware` uses the current/default guard; the session/token subclasses pin one guard.
- `GuestMiddleware` admits guests and redirects authenticated browsers to `auth.session.home`.
- `RequirePermissionMiddleware`, `RequireRoleMiddleware`, and `RequirePolicyMiddleware` are configured by subclassing and setting class attributes.

Protected responses receive `Cache-Control: no-store, private`. Session guests may be redirected to `auth.session.redirect_to`; JSON/AJAX clients and token routes receive an authentication exception instead.

### Tokens and supporting types

`AccessToken` is immutable metadata and `NewAccessToken` pairs it with the one-time `plain_text` credential. `AccessTokenRepository` exposes `create`, `findByPlainText`, `touch`, `revoke`, `revokeAll`, and `purgeExpired`. `generate_token_secret` and `hash_token_secret` are public helpers, but applications normally issue tokens through `Auth.createToken`.

### Extension contracts

Contracts under `orionis.auth.contracts` cover the manager, guards, identity provider, permission repository, token repository, policy, context, snapshots, and authenticatable/authorizable identities. Replace a service by binding your implementation to its contract in the container before dependent services are built.

## Common workflows

### Authenticate a browser session

Accept credentials in an HTTP handler and call `await Auth.attempt(credentials, remember=...)`. On success, the session guard rotates the session, stores the identity identifier, optionally issues the persistent credential, and the manager rebinds the current context. On failure it returns `False` without authenticating the request.

### Protect a route

Use `AuthenticateSessionMiddleware` or `AuthenticateTokenMiddleware` when any valid identity is sufficient. For a concrete capability, subclass `RequirePermissionMiddleware` and declare `permissions`; set `requires_all=False` to accept any. Declare middleware as a real class so compiled route caches can reference it.

### Authorize a loaded resource

Register its policy once during application setup, load the resource in the controller, and call `await Auth.authorizeResource("update", resource)`. Class-level abilities such as `create` or `viewAny` can use a `RequirePolicyMiddleware` subclass.

### Issue and revoke a personal token

Call `await Auth.createToken(...)` from a session-authenticated request, show `plain_text` once, and store only metadata in later responses. Clients send `Authorization: Bearer <plain_text>`. A token-authenticated request can revoke itself with `await Auth.revokeCurrentToken()`.

## Examples

### Apply token abilities to permissions

This executable example demonstrates that abilities narrow, but never expand, identity permissions:

```python
from orionis.auth import AuthorizationSnapshot


snapshot = AuthorizationSnapshot(
    permissions={"posts.read", "posts.update"},
    roles={"editor"},
    abilities={"posts.read"},
)

print(snapshot.can("posts.read"))    # True
print(snapshot.can("posts.update"))  # False
print(snapshot.hasRole("editor"))    # True
```

Validation: **Executed successfully** on CPython 3.14.6.

### Define an authenticatable model and policy

The model supplies authentication and authorization identifiers; the policy accepts both sync and async abilities:

```python
from orionis.auth import Authenticatable, Authorizable, Policy
from orionis.orm import Integer, Model, String


class User(Model, Authenticatable, Authorizable):
    id = Integer().primary().autoIncrement()
    email = String(255).unique()
    password = String(255)


class UserPolicy(Policy):
    async def update(self, identity: User, user: User) -> bool:
        return identity.getAuthIdentifier() == user.getAuthIdentifier()
```

Register it during application setup with `Auth.registerPolicy(User, UserPolicy)`.

Validation: **Import-validated only** on CPython 3.14.6; no database operation was executed.

### Declare permission middleware

Middleware requirements live in subclasses rather than constructor arguments:

```python
from orionis.auth.middleware import RequirePermissionMiddleware


class CanPublishPosts(RequirePermissionMiddleware):
    permissions = ("posts.create", "posts.publish")
    requires_all = True
```

Attach `CanPublishPosts` to a route. Guests raise `AuthenticationException`; authenticated identities missing either permission raise `AuthorizationException`.

Validation: **Import-validated only** on CPython 3.14.6; route execution requires an application request pipeline.

### Serialize token metadata without leaking the secret

`NewAccessToken` excludes its usable credential from `repr` and `toDict`:

```python
from orionis.auth import AccessToken, NewAccessToken


issued = NewAccessToken(
    access_token=AccessToken(
        id=1,
        tokenable_type="app.models.user.User",
        tokenable_id=7,
        name="automation",
    ),
    plain_text="1|example-secret",
)

print(issued.toDict()["access_token"]["name"])  # automation
print("example-secret" in repr(issued))          # False
```

The application must deliver `issued.plain_text` once over a protected channel.

Validation: **Executed successfully** on CPython 3.14.6.

## Configuration

The bootstrap application reads these environment variables into the `auth` configuration:

| Configuration | Environment variable | Bootstrap default |
|---|---|---|
| `auth.default` | `AUTH_GUARD` | `session` |
| `auth.identity.model` | `AUTH_MODEL` | `app.models.user.User` |
| `auth.identity.username` | `AUTH_USERNAME` | `email` |
| `auth.session.key` | `AUTH_SESSION_KEY` | `_auth_identifier` |
| `auth.session.redirect_to` | `AUTH_REDIRECT_TO` | `/login` |
| `auth.session.home` | `AUTH_HOME` | `/home` |
| `auth.tokens.table` | `AUTH_TOKEN_TABLE` | `personal_access_tokens` |
| `auth.tokens.expiration` | `AUTH_TOKEN_EXPIRATION` | `None` (no automatic expiry) |
| `auth.tokens.secret_bytes` | `AUTH_TOKEN_SECRET_BYTES` | `40` (allowed: 32–128) |
| `auth.passwords.expiration` | `AUTH_PASSWORD_RESET_EXPIRATION` | `60` minutes |
| `auth.passwords.throttle` | `AUTH_PASSWORD_RESET_THROTTLE` | `60` seconds |
| `auth.passwords.table` | `AUTH_PASSWORD_RESET_TABLE` | `password_reset_tokens` |
| `auth.remember.cookie` | `AUTH_REMEMBER_COOKIE` | `orionis_remember` |
| `auth.remember.lifetime` | `AUTH_REMEMBER_LIFETIME` | `43200` minutes |
| `auth.remember.secure` | `AUTH_REMEMBER_SECURE` | `True` |

The default guard accepts only `session` or `token`. Configuration entities validate non-empty names, positive expiration/throttle values, and token-secret bounds during bootstrap. The remember cookie name must differ from the session cookie name.

## Integration with Orionis

`AuthProvider` registers a scoped `IAuthenticationContext`; singleton identity provider, permission repository, authorizer, token repository, and guards; and the singleton `IAuthManager`. It then pins the `Auth` facade eagerly because synchronous facade operations must be immediately callable.

The HTTP kernel installs the appropriate identity resolver for web and API routes and opens the container scope that isolates authentication state. The module integrates with ORM/database storage, the hashing manager, sessions, response cookies, the router's middleware pipeline, and the framework exception handler. Auth migrations create the permission, role, personal-token, and reset-token structures used by the repositories.

## Errors and edge cases

- `AuthException` is the base for configuration, authentication, authorization, missing-guard, identity-provider, missing-policy, and token failures.
- Session login/logout outside an active HTTP request raises `AuthException`.
- `authorize` and `authorizeResource` raise `AuthenticationException` for guests and `AuthorizationException` for denied authenticated requests.
- An unknown guard raises `GuardNotFoundException` and includes the registered names.
- Empty middleware requirements raise `AuthConfigurationException`; a missing resource policy raises `PolicyNotFoundException`.
- Token creation requires an `IAuthorizable` owner. Token-authenticated requests cannot issue nested personal tokens.
- Token secrets are validated, digested, compared with constant-time library helpers, and never recoverable from stored metadata. Invalid, expired, revoked, malformed, or inactive-owner credentials fail closed.
- A restricted token can grant only the intersection of identity permissions and abilities; it cannot grant absent permissions or pass role middleware.
- Remember-me credentials fail closed on HTTP when secure mode is enabled, malformed/expired cookies, password changes, inactive identities, or failed rotation.

## Performance and concurrency

Authentication state is stored in the container's request scope, while managers, guards, middleware, and repositories are stateless singletons. Context binding therefore isolates concurrent requests without copying singleton services.

Authentication mutations use an async lock associated with the active context. Authorization snapshots are loaded lazily and cached on the request context; their `frozenset` data is immutable and can be shared by coroutines in that request. Policy class lookup is cached, but policy instances are freshly resolved in the current scope.

Password hashing runs through the hashing manager outside the event-loop thread. Database writes arbitrate personal-token, remember-token, and password-reset races; the password reset consumes its token and conditionally updates the password inside a transaction. Remember credentials rotate without extending their original deadline.

## Compatibility

The project declares Python 3.14+; validation used CPython 3.14.6 on Windows. Authentication itself is platform independent. It relies on the framework's declared SQLAlchemy/async database, hashing, HTTP, session, and container dependencies and has no optional package extra. Database-driver extras may still be required by the configured database backend.

## Verification notes

Package exports, manager, provider, contexts, guards, middleware, authorization, tokens, identity, remember/password flows, auth configuration, migrations, direct integrations, and `tests/auth` were inspected. All 359 auth tests passed through the Orionis runner on CPython 3.14.6. The snapshot and redaction examples were executed; the facade, model/policy, and middleware examples were import-validated because full execution requires application/request or database state.
