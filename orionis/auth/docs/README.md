# Authentication and authorization

`orionis/auth/` answers two different questions and keeps them apart on
purpose:

| Question | Layer | Entry point |
|---|---|---|
| Who is this user? | Authentication | `Guard` → `AuthenticationContext` |
| What may this user do? | Authorization | `Authorizer` → `AuthorizationSnapshot` |

## Table of contents

- [Functional description](#functional-description)
  - [Where it fits](#where-it-fits)
  - [Request pipeline](#request-pipeline)
  - [File map](#file-map)
  - [Design decisions](#design-decisions)
- [API reference](#api-reference)
  - [Configuration](#configuration)
  - [Identity mixins](#identity-mixins)
  - [Identity provider](#identity-provider)
  - [Guards](#guards)
  - [Authentication context](#authentication-context)
  - [Authorization snapshot](#authorization-snapshot)
  - [Authorizer and policies](#authorizer-and-policies)
  - [Permission registrar](#permission-registrar)
  - [Personal access tokens](#personal-access-tokens)
  - [Auth facade](#auth-facade)
  - [Middleware](#middleware)
  - [Exceptions and HTTP statuses](#exceptions-and-http-statuses)
  - [Service provider](#service-provider)
- [Usage examples](#usage-examples)
  - [Preparing the identity model](#preparing-the-identity-model)
  - [Web login and logout](#web-login-and-logout)
  - [Protecting routes](#protecting-routes)
  - [Issuing and using an API token](#issuing-and-using-an-api-token)
  - [Declaring a policy](#declaring-a-policy)
- [Performance and concurrency](#performance-and-concurrency)
- [Compatibility](#compatibility)
- [Security boundaries](#security-boundaries)
- [Out of scope in this version](#out-of-scope-in-this-version)

## Functional description

### Where it fits

The module sits between the HTTP kernel and your controllers. It reuses
the pieces the framework already owns instead of duplicating them:

| Concern | Owner |
|---|---|
| Password hashing | `orionis/hashing/` (`IHashManager`) |
| Session storage and cookies | `orionis/session/` |
| Queries and migrations | `orionis/orm/`, `orionis/database/` |
| Request scope | `Container.beginScope()` (`contextvars`) |
| Error responses | `orionis/failure/` and `orionis/http/` |

### Request pipeline

For a web request:

```text
Request → SessionGuard → Session → Identity → AuthenticationContext → Controller
```

For an API request:

```text
Request → TokenGuard → PersonalAccessToken → Identity → AuthenticationContext → Controller
```

The rest of the framework works with the authenticated identity without
knowing which guard produced it.

### File map

```text
orionis/auth/
├── contracts/          Interfaces every piece depends on
├── concerns/           Mixins added to the application identity model
├── context/            Per request authenticated state
├── guards/             SessionGuard, TokenGuard
├── identity/           ModelIdentityProvider
├── authorization/      Snapshot, authorizer, policies, registrar, repository
├── tokens/             Secret generation, hashing and persistence
├── middleware/         Authentication and authorization route guards
├── entities/           GuardResult, AccessToken, NewAccessToken
├── manager.py          AuthManager, backing the Auth facade
├── provider.py         AuthProvider, registered in CORE_PROVIDERS
└── exceptions.py       AuthException and its subclasses
```

### Design decisions

- **The authenticated identity never lives on a singleton.** It lives in
  the container scope the HTTP kernel opens per request, which is backed
  by `contextvars`. Two concurrent requests can never see each other.
- **No coupling to a class named `User`.** The identity model travels as
  a dotted path in `config/auth.py` and is resolved lazily.
- **Opaque tokens, not JWT.** Only a SHA-256 digest of the secret is
  stored. A conditional usage update rejects revocation committed before
  identity publication; already-running requests are not cancelled.
- **Abilities intersect, never elevate.** The effective authorization is
  `identity permissions ∩ token abilities`.
- **The mixins are plain classes.** They are registered as virtual
  subclasses of their contracts, because inheriting from an `ABC` would
  clash with `ModelMeta`, the metaclass of every Orionis model.

## API reference

### Configuration

`config/auth.py` extends the `Auth` entity of the framework.

```python
@dataclass(frozen=True, kw_only=True)
class Auth(BaseEntity):
    default: Guards | str
    identity: Identity | dict
    session: SessionAuth | dict
    tokens: Tokens | dict
```

| Key | Meaning | Default |
|---|---|---|
| `auth.default` | Guard used when none is named | `session` |
| `auth.identity.model` | Dotted path of the identity model | `app.models.user.User` |
| `auth.identity.username` | Attribute used to look an identity up | `email` |
| `auth.session.key` | Session key holding the identifier | `_auth_identifier` |
| `auth.session.redirect_to` | Page guests are sent to, or `None` | `None` |
| `auth.tokens.table` | Table storing the tokens | `personal_access_tokens` |
| `auth.tokens.expiration` | Default lifetime in minutes, or `None` | `None` |
| `auth.tokens.secret_bytes` | Random bytes behind a token secret | `40` |

Nothing is duplicated from `config/session.py` or `config/hashing.py`.
Submitted credentials always use the `password` key. `getAuthPassword()` selects
the stored hash; the mixin reads `AUTH_PASSWORD`, which may name another column.

### Identity mixins

```python
class Authenticatable:
    AUTH_PASSWORD: ClassVar[str] = "password"

    def getAuthIdentifierName(self) -> str: ...
    def getAuthIdentifier(self) -> object: ...
    def getAuthPassword(self) -> str: ...

class Authorizable:
    AUTHORIZABLE_TYPE: ClassVar[str | None] = None

    def getAuthorizableType(self) -> str: ...
    def getAuthorizableId(self) -> object: ...
```

`getAuthIdentifierName()` reads the primary key from the model metadata,
so a UUID key works without any extra configuration.

### Identity provider

```python
class IIdentityProvider(ABC):
    async def retrieveById(self, identifier: object) -> IAuthenticatable | None: ...
    async def retrieveByCredentials(self, credentials: Mapping[str, object]) -> IAuthenticatable | None: ...
    async def validateCredentials(self, identity: IAuthenticatable | None, credentials: Mapping[str, object]) -> bool: ...
```

`ModelIdentityProvider` implements it on top of the Orionis ORM.
It restores integer, string and UUID keys using model metadata, and honours
global scopes and soft deletes. Unknown identities still perform hashing work
to reduce enumeration signals, without promising equal timing across algorithms
or historical costs. The hashing module runs the cost on a worker thread, so
verification never blocks the event loop.

### Guards

```python
class IGuard(ABC):
    @property
    def name(self) -> str: ...
    async def resolve(self, request: Request) -> GuardResult | None: ...

class ISessionGuard(IGuard):
    async def attempt(self, request: Request, credentials: Mapping[str, object], *, remember: bool = False) -> IAuthenticatable | None: ...
    def login(self, request: Request, identity: IAuthenticatable) -> None: ...
    async def logout(self, request: Request) -> None: ...
```

`SessionGuard.login()` requires a persisted scalar identity, requests a session
ID rotation and immediately rotates CSRF using the existing HTTP configuration.
The identity key is stored as canonical text. `await logout()` revokes persistent
login and invalidates the session. `await Auth.attempt(credentials, remember=True)`
opts into an independent, revocable cookie, requiring HTTPS by default. The
`remember_token` column stores an expiring digest; each new remembered login
replaces the previous device's grant. Restoration rotates the token without
extending its original deadline. Password changes invalidate the credential.
Persistence, old-ID deletion and cookies belong to `StartSessionMiddleware` and
`SessionManager`; Auth has no parallel session system.

`TokenGuard` reads `Authorization: Bearer <token>`, verifies owner type and ID,
then updates `last_used_at` only while the token is unexpired and unrevoked.
Corrupt non-null timestamps or abilities reject the credential.
The scheme is case-insensitive. Duplicate Authorization headers are rejected.

### Authentication context

```python
class IAuthenticationContext(ABC):
    @property
    def identity(self) -> IAuthenticatable | None: ...
    @property
    def guard(self) -> str | None: ...
    @property
    def abilities(self) -> frozenset[str] | None: ...
    @property
    def credentialId(self) -> object | None: ...
    @property
    def isAuthenticated(self) -> bool: ...
    @property
    def isGuest(self) -> bool: ...
    def identifier(self) -> object | None: ...
    async def authorization(self) -> IAuthorizationSnapshot: ...
```

Two module level helpers move the context in and out of the scope:

```python
def current_auth_context() -> IAuthenticationContext: ...
def bind_auth_context(context: IAuthenticationContext) -> None: ...
```

Outside a request `current_auth_context()` returns the shared
`GUEST_CONTEXT`, and `bind_auth_context()` raises `AuthException`.
`AuthProvider` also binds `IAuthenticationContext` as `SCOPED`: controllers may
inject a guest context before resolution. Authentication publishes a new context.
Bound contexts become anonymous after replacement, scope closure, or access from
another scope. Do not retain them in a singleton.

One request-local lock serializes guard resolution, login, logout and current
token revocation. Repeating a guard reuses its context, including guest results;
another guard cannot silently replace an authenticated identity. Detached tasks
must open a new scope after the owning request ends.

### Authorization snapshot

```python
class AuthorizationSnapshot(IAuthorizationSnapshot):
    def __init__(self, permissions, roles, abilities=None) -> None: ...

    @property
    def permissions(self) -> frozenset[str]: ...
    @property
    def roles(self) -> frozenset[str]: ...
    @property
    def abilities(self) -> frozenset[str] | None: ...
    def can(self, permission: str) -> bool: ...
    def hasRole(self, role: str) -> bool: ...
```

The snapshot is resolved at most once per request, under a lock owned by
the context, and answers every later check without touching the database.

### Authorizer and policies

```python
class IAuthorizer(ABC):
    async def can(self, context, permission: str) -> bool: ...
    async def canAny(self, context, permissions: Iterable[str]) -> bool: ...
    async def canAll(self, context, permissions: Iterable[str]) -> bool: ...
    async def hasRole(self, context, role: str) -> bool: ...
    async def allows(self, context, ability: str, resource: object) -> bool: ...
    def registerPolicy(self, resource: type, policy: type[IPolicy]) -> None: ...
```

A policy declares one method per ability, plus an optional `before` hook:

```python
class Policy(IPolicy):
    async def before(self, identity: object, ability: str) -> bool | None: ...
```

Policy class lookups follow the resource MRO and are cached. Instances are built
through DI for each evaluation, never cached globally, so request dependencies
remain local. A restricted token must include the exact policy method name in
its abilities before the hook runs, and the policy must also allow the operation.
Only literal `True` grants access. Private methods and `before` are not public
abilities. Missing policies or methods raise `PolicyNotFoundException`.

### Permission registrar

```python
class PermissionRegistrar:
    async def createPermission(self, name: str) -> object: ...
    async def createRole(self, name: str) -> object: ...
    async def givePermissionTo(self, authorizable, *permissions: str) -> None: ...
    async def revokePermissionFrom(self, authorizable, *permissions: str) -> None: ...
    async def assignRole(self, authorizable, *roles: str) -> None: ...
    async def removeRole(self, authorizable, *roles: str) -> None: ...
    async def grantToRole(self, role: str, *permissions: str) -> None: ...
    async def revokeFromRole(self, role: str, *permissions: str) -> None: ...
```

Names have one namespace: unique, non-empty, unpadded, at most 255 characters.
Composite pivot keys make assignment idempotent. Insert conflicts are isolated
in a transaction or savepoint and only absorbed when the identical row exists;
other SQL failures propagate. Wrap multiple registrar operations in an application
transaction when they must commit or roll back together.

### Personal access tokens

```python
class IAccessTokenRepository(ABC):
    async def create(self, tokenable, name: str, *, abilities=None, expires_at=None) -> NewAccessToken: ...
    async def findByPlainText(self, plain_text: str) -> AccessToken | None: ...
    async def touch(self, token_id: object) -> bool: ...
    async def revoke(self, token_id: object) -> bool: ...
    async def revokeAll(self, tokenable) -> int: ...
    async def purgeExpired(self) -> int: ...
```

The secret is available only through the issuance result's `plain_text` attribute.
`repr()` and `NewAccessToken.toDict()` omit it. Return the attribute explicitly
once; never log it. Generic introspection or `dataclasses.asdict()` is not a
redaction API.

`None` abilities means unrestricted; an empty collection permits no abilities.
Malformed values are rejected, not coerced. Dates are normalized to UTC.
`touch()` returns `False` if expiry or revocation won. Issuance recovers the ID
by unique digest when a schemaless driver does not return the generated key.

### Auth facade

`Auth` is pinned during boot, so its synchronous methods can be called
without `await`, including from templates.

| Method | Awaitable | Purpose |
|---|---|---|
| `Auth.user()` | no | Authenticated identity, or `None` |
| `Auth.identifier()` | no | Identifier of the identity |
| `Auth.check()` / `Auth.guest()` | no | Authentication state |
| `Auth.context()` | no | Full authentication context |
| `Auth.guard(name)` | no | Configured guard |
| `Auth.attempt(credentials)` | yes | Web login from credentials |
| `Auth.login(identity)` / `Auth.logout()` | yes | Session lifecycle |
| `Auth.can(...)` / `cannot` / `canAny` / `canAll` | yes | Permission checks |
| `Auth.hasRole(role)` | yes | Role check |
| `Auth.authorize(permission)` | yes | Require a permission |
| `Auth.allows(ability, resource)` / `denies` | yes | Policy checks |
| `Auth.authorizeResource(ability, resource)` | yes | Require a policy |
| `Auth.createToken(name, ...)` | yes | Issue an access token |
| `Auth.revokeCurrentToken()` | yes | Revoke the presented token |
| `Auth.registerPolicy(resource, policy)` | no | Bind a policy |

### Middleware

| Class | Effect |
|---|---|
| `ResolveIdentityMiddleware` | Binds the context and lets guests continue |
| `ResolveSessionIdentityMiddleware` | Kernel default for web routes; resolves the session and allows guests |
| `ResolveTokenIdentityMiddleware` | Kernel default for API routes; resolves Bearer tokens and allows guests |
| `AuthenticateMiddleware` | Requires an identity using the request guard, or the configured default before resolution |
| `AuthenticateSessionMiddleware` | Same, pinned to the session guard |
| `AuthenticateTokenMiddleware` | Same, pinned to the token guard |
| `GuestMiddleware` | Guests continue; authenticated browsers leave guest-only routes |
| `RequirePermissionMiddleware` | Requires the declared permissions |
| `RequireRoleMiddleware` | Requires the declared roles |
| `RequirePolicyMiddleware` | Requires a policy ability on a resource class |

The Orionis router attaches middleware **classes**, not parameterised
instances, so requirements are declared by subclassing. A real class also
keeps the compiled route cache valid, which a dynamically generated class
could not do.
The HTTP kernel establishes identity before application and route middleware:

```text
Web: StartSession → CSRFToken → ResolveSessionIdentity → route middleware → handler
API: ResolveTokenIdentity → route middleware → handler
```

These defaults apply to every matched route, including controller and view routes.
Public routes need no authentication middleware to use `Auth.user()`, `Auth.check()`
or template auth directives. Missing or unusable credentials leave a guest context;
they do not restrict access. APIs never start a session or read session credentials.
OPTIONS/preflight and failures before route dispatch do not resolve identity.

Keep `AuthenticateSessionMiddleware` or `AuthenticateTokenMiddleware` on protected
route groups, `GuestMiddleware` on login/registration, and permission/role/policy
requirements on the resources they protect. Installing these restrictions on every
route would also restrict public endpoints. Repeated resolution through the same
guard reuses the context, including guest results; it does not repeat repository I/O.

The kernel pins guards by route kind, independently of `auth.default`. Unpinned
`ResolveIdentityMiddleware` and `AuthenticateMiddleware` reuse that request guard;
before any resolution they still use `auth.default`. Explicitly pinned guards keep
their meaning and cannot replace an already authenticated context with another guard.
Core kernel middleware is outside route `.withOutMiddleware()` exclusions.

`GuestMiddleware.redirect_to` overrides `auth.session.home` (fallback `/home`);
authenticated JSON/AJAX callers receive 403. Role membership is informational:
role-only middleware rejects
restricted tokens because it declares no capability to intersect with abilities.

Anonymous credential-free requests perform no authentication repository I/O.
Authenticated web requests retrieve the session's identity; usable API credentials
also require token lookup and a usage update. Permission snapshots remain lazy.
Identity resolution alone does not set cache headers: public handlers that return
personalized data must set suitable `Cache-Control`, for example `private, no-store`.
Protected routes retain the headers set by `AuthenticateMiddleware`.

### Exceptions and HTTP statuses

```python
class AuthException(Exception): ...
class AuthConfigurationException(AuthException): ...
class AuthenticationException(AuthException): ...
class AuthorizationException(AuthException): ...
class GuardNotFoundException(AuthException): ...
class IdentityProviderException(AuthException): ...
class PolicyNotFoundException(AuthException): ...
class TokenException(AuthException): ...
```

Two of them are mapped in `orionis/failure/base/handler.py`:

| Exception | Status | Meaning |
|---|---|---|
| `AuthenticationException` | `401` | No valid authenticated identity |
| `AuthorizationException` | `403` | Authenticated, but not allowed |

Browsers get the standard HTML error page and API clients get JSON,
because the handler honours `request.wantsJson()`. When
`auth.session.redirect_to` is configured, `AuthenticateMiddleware`
returns a redirect only for session-guard browser requests. Token routes reject
guests with 401 even without `Accept`, and emit `WWW-Authenticate: Bearer`.
Auth exception subclasses retain 401/403 semantics. Content negotiation still
selects HTML or JSON through the standard handler.

### Service provider

`AuthProvider` is listed in `CORE_PROVIDERS` and is **not** deferrable:
`Auth.check()` is synchronous, so the facade must already be pinned when
the first template renders.

```python
class AuthProvider(ServiceProvider):
    def register(self) -> None: ...
    async def boot(self) -> None: ...
```

| Lifetime | Components | Reason |
|---|---|---|
| `SINGLETON` | Manager, guards, provider, authorizer, repositories, registrar | No current identity or policy instance is retained |
| `SCOPED` | Context, operation/snapshot locks and bound Session | State belongs to the request |
| Per evaluation | Policy instance | Constructor injection uses the current scope |

`Auth` pins its stateless manager at boot. `Session` uses `ScopedFacade`, which
reads directly from the active scope without a process-wide pin.

## Usage examples

### Preparing the identity model

```python
from typing import ClassVar
from orionis.auth import Authenticatable, Authorizable
from orionis.orm import BigInteger, Boolean, DateTime, Model, String

class User(Model, Authenticatable, Authorizable):
    hidden: ClassVar[list[str]] = ["password", "remember_token"]
    fillable: ClassVar[list[str]] = ["name", "email", "password"]

    id = BigInteger().primary().autoIncrement()
    name = String(255)
    email = String(255).unique()
    password = String(255)
    active = Boolean().default(value=True)
```

### Web login and logout

```python
from orionis.http import HttpResponse, response
from orionis.http.base import BaseController
from orionis.support.facades import Auth

class LoginController(BaseController):

    async def login(self, payload: LoginSchema) -> HttpResponse:
        """Authenticate the visitor and open a session."""
        granted = await Auth.attempt({
            "email": payload.email,
            "password": payload.password,
        })
        if not granted:
            return response.redirect("/login").withErrors({
                "email": "These credentials do not match our records.",
            })
        return response.redirect("/dashboard")

    async def logout(self) -> HttpResponse:
        """Close the session of the current visitor."""
        await Auth.logout()
        return response.redirect("/login")
```

### Protecting routes

```python
from orionis.auth.middleware import (
    AuthenticateSessionMiddleware,
    RequirePermissionMiddleware,
)

class CanManageUsers(RequirePermissionMiddleware):
    """Route guard requiring the user management permissions."""

    permissions = ("users.view", "users.update")

Route.get("/users", [UserController, "index"]).middleware(
    AuthenticateSessionMiddleware,
    CanManageUsers,
)
```

### Issuing and using an API token

```python
from orionis.support.facades import Auth

# Inside a controller, for the authenticated identity.
issued = await Auth.createToken("mobile-app", abilities=["users.view"])
plain_text = issued.plain_text          # shown once, never stored

# The client then sends it on every request:
#     Authorization: Bearer <plain_text>
#
# Even if the identity also owns "users.delete", the token cannot use it:
#     await Auth.can("users.view")      -> True
#     await Auth.can("users.delete")    -> False
```

Protect the API routes with the token guard:

```python
from orionis.auth.middleware import AuthenticateTokenMiddleware

Route.get("/api/v1/users", [UserController, "index"]).middleware(
  AuthenticateTokenMiddleware,
)
```

### Declaring a policy

```python
from orionis.auth import Policy
from orionis.support.facades import Auth

class PostPolicy(Policy):
    """Authorize operations performed on a single post."""

    async def update(self, identity: object, post: Post) -> bool:
        """Allow the update only for the author of the post."""
        return post.user_id == identity.getAuthIdentifier()

# Register it once, during boot.
Auth.registerPolicy(Post, PostPolicy)

# Then, inside a controller:
await Auth.authorizeResource("update", post)
```

## Performance and concurrency

- Session authentication adds one identity SELECT after restoring the session.
  Saving an activated session renews server and cookie expiry together.
- A PAT requires three statements: digest lookup, identity lookup and conditional
  usage UPDATE. It does not run a password hash.
- The first RBAC check adds one UNION SELECT for direct grants, roles and inherited
  grants. Twelve concurrent snapshot requests are tested to issue exactly one
  SELECT. Later checks reuse the immutable sets without additional SQL.
- Policies add DI construction and their own application logic. They load RBAC
  only when needed; reflection metadata is cached by the existing container.
- Guest authorization does no SQL. Web middleware can still create a guest
  session for CSRF and navigation.
- Session updates require a live record. SQL uses UPDATE, files use `filelock`
  across workers, and cache uses atomic replacement or aiocache CAS. Old requests
  cannot recreate deleted sessions through the manager's save path.
- No global permission cache exists. Successful snapshots stay fixed for their
  context; subsequent contexts observe permission changes.

## Compatibility

- Python `>= 3.14`, in line with the rest of the framework.
- Databases: the module ships the `personal_access_tokens` migration and
  reuses the `permissions`, `roles`, `model_has_permissions`,
  `model_has_roles` and `role_has_permissions` tables already created by
  the framework migrations.
- Roles, permissions and tokens use `table.id()`; pivots use composite keys.
  Owner IDs are canonical `VARCHAR(255)` for integer, string and UUID identities.
  The SQL compiler gives
  auto-incrementing `BIGINT` primary keys a SQLite variant, because
  SQLite only aliases a single-column primary key to `ROWID` when its
  declared type is literally `INTEGER`. PostgreSQL still gets `BIGSERIAL`
  and MySQL still gets `BIGINT AUTO_INCREMENT`.
- `filelock` is a base dependency for cross-process file persistence locks.
- After enabling the module, clear `storage/framework/bootstrap` (or run
  `reactor optimize:clear`): the compiled bootstrap cache is not
  invalidated by changes inside `orionis/`.

Breaking changes: remove `auth.identity.password` and `guard_name` arguments.
`touch()` and session-store `delete()` now return booleans. Custom session stores
must implement atomic `update()`; cache repositories need atomic `replace()`.
`NewAccessToken.toDict()` is redacted. Policies are built per evaluation and only
explicit `True` grants access. Abilities also restrict policies. PAT-authenticated
requests cannot issue PATs through `Auth.createToken()`.
`Auth.revokeCurrentToken()` also clears the current authentication context.

Existing databases need a reviewed migration: merge duplicate role/permission
names and pivot references before removing `guard_name`, convert owner IDs to
text, add token expiry/revocation indexes and the role-to-permission lookup index.
Rebuilding is suitable only for
disposable alpha databases. Editing applied migration files does not alter their
tables. Back up real data; this review never resets the application database.

## Security boundaries

- Require HTTPS and Secure/HttpOnly session cookies in production. Rate-limit
  login and token issuance with the application's existing HTTP controls.
- `Auth.attempt()` starts a session only when `identity.active is True`.
  Missing, null and false values are rejected after password verification.
- Revocation does not cancel already-authorized work. Strict business operations
  must revalidate at their own transaction boundary. Read isolation is determined
  by the configured database engine.
- Polymorphic owners have no FK to one global user table. Revoke tokens and detach
  grants before permanently deleting an owner; never recycle its type/key pair.
  Role/permission FKs are restrictive: detach pivots first. Enable SQLite FKs.
- File locks require filesystem support for the OS locks used by `filelock`;
  network filesystems need deployment validation. Memory sessions are single-process.
  General concurrent payload writes remain last-writer-wins, not a merge of carts
  or flash bags.
- SQL errors omit driver details and values to avoid credential logging. Application
  code must also avoid logging passwords, session cookies and raw PATs.
- Tests execute SQLite files, separate connections, ASGI/RSGI adapters and real DI.
  Live PostgreSQL/MySQL/Oracle/SQL Server, Redis/Memcached and separate OS workers
  require deployment-level certification.

## Out of scope in this version

Deliberately not implemented, and designed so they can be added without
rewriting the core: JWT, OAuth, OpenID Connect, LDAP, basic
authentication, generic API keys, SSO, WebSocket authentication, MFA,
social login, password reset, email verification, magic links,
impersonation and authentication specific multi-tenancy.

Role hierarchies and role inheritance are also intentionally absent: a
role is nothing more than a group of permissions.
