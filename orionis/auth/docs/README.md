# orionis.auth

> Resolve session and opaque-token identities, scoped authorization, persistent login, and password-reset credentials.

Spanish version: [README.es.md](README.es.md). Agent entry point: [SKILL.md](SKILL.md).

## Table of contents

- [Requirements](#requirements)
- [Functional overview](#functional-overview)
- [Module structure](#module-structure)
- [API reference](#api-reference)
- [Exports and imports](#exports-and-imports)
- [Identity concerns](#identity-concerns)
- [AuthenticationContext and scope helpers](#authenticationcontext-and-scope-helpers)
- [AuthorizationSnapshot](#authorizationsnapshot)
- [ModelIdentityProvider](#modelidentityprovider)
- [SessionGuard](#sessionguard)
- [RememberMe](#rememberme)
- [TokenGuard](#tokenguard)
- [Token functions and entities](#token-functions-and-entities)
- [AccessTokenRepository](#accesstokenrepository)
- [Authorizer, Policy and PolicyRegistry](#authorizer-policy-and-policyregistry)
- [PermissionRegistrar and DatabasePermissionRepository](#permissionregistrar-and-databasepermissionrepository)
- [AuthManager](#authmanager)
- [Middleware](#middleware)
- [PasswordBroker](#passwordbroker)
- [AuthProvider](#authprovider)
- [Exceptions](#exceptions)
- [Contracts](#contracts)
- [Usage examples](#usage-examples)
- [Design characteristics](#design-characteristics)
- [Performance and concurrency](#performance-and-concurrency)
- [Compatibility notes](#compatibility-notes)
- [Verification and limitations](#verification-and-limitations)

## Requirements

Auth has no dedicated installation extra. The database-backed operations require
a configured Orionis connection, a compatible identity model, and existing tables.
Session operations additionally require a request carrying `request.state.session`.
The pure mixins, entities, snapshots and context helpers need no database setup.

| Area | Additional preparation and evidence |
|---|---|
| Identity | Configure `auth.identity.model`; supply ORM metadata and the authentication mixin or contract. See [ModelIdentityProvider](../identity/provider.py). |
| Web login | Start the session before resolving identity. The [HTTP kernel](../../http/kernel.py) builds `StartSessionMiddleware`, CSRF middleware and `ResolveSessionIdentityMiddleware` in that order. |
| Persistent login | Supply a nullable `remember_token` column and provider compare-and-replace support. HTTPS is required when `auth.remember.secure` is true. See [RememberMe](../remember.py). |
| RBAC | Create `permissions`, `roles`, `model_has_permissions`, `model_has_roles` and `role_has_permissions`, including unique names and composite pivot keys. See [registrar](../authorization/registrar.py) and [repository](../authorization/repository.py). |
| Access tokens | Create the configured token table; the supplied [migration](../../../database/migrations/m0000000011_create_personal_access_tokens_table.py) defaults to `personal_access_tokens`. A digest must be unique. |
| Password reset | Create the configured reset table. The [schema](../../../database/schemas/password_reset_tokens_v1.py) declares `email` as the primary key, nullable `token`, `user_id`, `password_fingerprint` and `created_at`. The [migration](../../../database/migrations/m0000000012_create_password_reset_tokens_table.py) creates it. |

Managers, repositories and brokers do not create these tables. Database drivers
and hashing backends are dependencies of their corresponding Orionis services,
not alternative authentication engines. Dependency constraints are listed under
[Compatibility notes](#compatibility-notes).

The following defaults are fallback values, not a promise about a configured
application. The configuration entities read environment variables and may be
overridden through application configuration.

| Key | Fallback | Source and verified restriction |
|---|---|---|
| `auth.default` | `"session"` | [Auth](../../foundation/config/auth/entities/auth.py): normalizes supported guard names. `AuthManager` selects the session guard if the value is falsy. |
| `auth.identity.model` | `"app.models.user.User"` | [Identity](../../foundation/config/auth/entities/identity.py): nonempty dotted class path; [provider](../identity/provider.py) imports it lazily. |
| `auth.identity.username` | `"email"` | [Identity](../../foundation/config/auth/entities/identity.py): nonempty string. Submitted passwords still use the literal key `"password"`. |
| `auth.session.key` | `"_auth_identifier"` | [SessionAuth](../../foundation/config/auth/entities/session.py): nonempty string. The guard also stores a password fingerprint under this key plus `"_password"`. |
| `auth.session.redirect_to` | `None` | [SessionAuth](../../foundation/config/auth/entities/session.py): string or `None`; guest-browser redirect target, not post-login home. |
| `auth.session.home` | `"/home"` | [SessionAuth](../../foundation/config/auth/entities/session.py): nonempty string, used by `GuestMiddleware`. |
| `auth.tokens.table` | `"personal_access_tokens"` | [Tokens](../../foundation/config/auth/entities/tokens.py): nonblank string. |
| `auth.tokens.expiration` | `None` | [Tokens](../../foundation/config/auth/entities/tokens.py): positive integer minutes, excluding booleans, or `None`. |
| `auth.tokens.secret_bytes` | `40` | [Tokens](../../foundation/config/auth/entities/tokens.py): integer from 32 to 128, excluding booleans. |
| `auth.remember.cookie` | `"orionis_remember"` | [RememberAuth](../../foundation/config/auth/entities/remember.py): nonempty ASCII letters, digits, underscores or hyphens; must differ from `session.cookie`. |
| `auth.remember.lifetime` | `43200` | [RememberAuth](../../foundation/config/auth/entities/remember.py): positive integer minutes, excluding booleans. |
| `auth.remember.secure` | `True` | [RememberAuth](../../foundation/config/auth/entities/remember.py): boolean; security-prefixed cookie names require true. |
| `auth.passwords.table` | `"password_reset_tokens"` | [PasswordReset](../../foundation/config/auth/entities/password_reset.py): nonblank string. |
| `auth.passwords.expiration` | `60` | [PasswordReset](../../foundation/config/auth/entities/password_reset.py): positive integer minutes, excluding booleans. |
| `auth.passwords.throttle` | `60` | [PasswordReset](../../foundation/config/auth/entities/password_reset.py): positive integer seconds, excluding booleans. |

`SessionGuard` separately reads `http.csrf.session_key` and
`http.csrf.token_length`, falling back to `"_csrf_token"` and `32`.
Only the entity constructors perform the configuration validation described above;
several concrete services accept an application-like object and read raw values.
`RememberMe` and `PasswordBroker` explicitly construct their settings entities.

## Functional overview

Guards turn request credentials into identities and `GuardResult` values.
`AuthenticationContext` publishes that result within a container scope; its lazy
snapshot combines identity permissions with credential restrictions.
`AuthManager` exposes these services and session transitions; the separate
`RememberMe` and `PasswordBroker` manage persistent and reset credentials.

Direct collaborators are `IHashManager`, Orionis ORM/query builders, container
scopes and the HTTP/session pipeline. The [Auth facade](../../support/facades/auth.py)
resolves `IAuthManager`; it is outside this module, rather than a root Auth export.
The [kernel](../../http/kernel.py) resolves session identities for web routes and
token identities for API routes before application/route middleware. Resolution
allows guests; protection is a separate middleware or manager operation.

## Module structure

All 53 Python files, including the 11 package initializers, were inspected.
No non-Python runtime resource is present inside this module.

| Files or package | Responsibility and principal symbols |
|---|---|
| [__init__.py](../__init__.py) | Sixteen lazy root exports and package attribute discovery. |
| [exceptions.py](../exceptions.py) | Eight public authentication exceptions. |
| [manager.py](../manager.py), [provider.py](../provider.py) | `AuthManager`, `AuthProvider`. |
| [remember.py](../remember.py) | `RememberMe`, `apply_remember_cookie`. |
| [concerns/authenticatable.py](../concerns/authenticatable.py), [authorizable.py](../concerns/authorizable.py), [functions.py](../concerns/functions.py), [must_verify_email.py](../concerns/must_verify_email.py), [initializer](../concerns/__init__.py) | Identity mixins, key normalization, email-verification marker. |
| [context/context.py](../context/context.py), [functions.py](../context/functions.py), [initializer](../context/__init__.py) | `AuthenticationContext`, `GUEST_CONTEXT`, binding and transition lock. |
| [authorization/authorizer.py](../authorization/authorizer.py), [policy.py](../authorization/policy.py), [registry.py](../authorization/registry.py), [repository.py](../authorization/repository.py), [registrar.py](../authorization/registrar.py), [snapshot.py](../authorization/snapshot.py), [initializer](../authorization/__init__.py) | Policy evaluation, lookup cache, RBAC reads/writes and snapshots. |
| [guards/session_guard.py](../guards/session_guard.py), [token_guard.py](../guards/token_guard.py), [initializer](../guards/__init__.py) | Session and personal access token guards. |
| [identity/provider.py](../identity/provider.py), [initializer](../identity/__init__.py) | `ModelIdentityProvider`. |
| [entities/access_token.py](../entities/access_token.py), [guard_result.py](../entities/guard_result.py), [new_access_token.py](../entities/new_access_token.py), [initializer](../entities/__init__.py) | Credential metadata and guard/issuance results. |
| [tokens/functions.py](../tokens/functions.py), [repository.py](../tokens/repository.py), [initializer](../tokens/__init__.py) | Random token secret, digest and persistence. |
| [middleware/authenticate.py](../middleware/authenticate.py), [authorize.py](../middleware/authorize.py), [guest.py](../middleware/guest.py), [policy.py](../middleware/policy.py), [resolve_identity.py](../middleware/resolve_identity.py), [initializer](../middleware/__init__.py) | Ten public middleware classes. |
| [passwords/broker.py](../passwords/broker.py), [initializer](../passwords/__init__.py) | `PasswordBroker`; the initializer is empty. |
| [contracts initializer](../contracts/__init__.py) and its twelve files linked under [Contracts](#contracts) | Abstract interfaces, including optional remember-token support. |

## API reference

The declaration blocks below reproduce source signatures, decorators, fields and
defaults. Bodies are omitted: these are reference fragments, not executable
scripts. Annotation names retain their spelling even when imported only under
`TYPE_CHECKING`. Executable scripts appear exclusively under [Usage examples](#usage-examples).
No overloads, public enums or public type aliases are declared in this module.

Exceptions described below include explicit failures and inspected propagated
failures; they are not exhaustive when a dependency, callback, import or database
operation participates.

### Exports and imports

The [root initializer](../__init__.py) lazily exports `AccessToken`,
`AuthConfigurationException`, `AuthException`, `Authenticatable`,
`AuthenticationContext`, `AuthenticationException`, `Authorizable`,
`AuthorizationException`, `AuthorizationSnapshot`, `GuardNotFoundException`,
`IdentityProviderException`, `MustVerifyEmail`, `NewAccessToken`, `Policy`,
`PolicyNotFoundException` and `TokenException`.
Its `__getattr__` delegates to [resolve_export](../../_exports.py), which imports
and caches the requested object in the package namespace. Unknown names raise
`AttributeError`; `__dir__` includes loaded attributes and declared exports.

| Importable package | Additional reexports |
|---|---|
| `orionis.auth.authorization` | `PolicyRegistry`, `EMPTY_SNAPSHOT`, `Policy`, `AuthorizationSnapshot`. The authorizer and SQL collaborators require file-level imports. |
| `orionis.auth.concerns` | `Authenticatable`, `Authorizable`, `MustVerifyEmail`, `model_primary_key`. |
| `orionis.auth.context` | `AuthenticationContext`, `GUEST_CONTEXT`, `bind_auth_context`, `current_auth_context`. |
| `orionis.auth.entities` | `AccessToken`, `GuardResult`, `NewAccessToken`. |
| `orionis.auth.guards` | `SessionGuard`, `TokenGuard`. |
| `orionis.auth.identity` | `ModelIdentityProvider`. |
| `orionis.auth.tokens` | `AccessTokenRepository`, `generate_token_secret`, `hash_token_secret`. |
| `orionis.auth.middleware` | All ten middleware classes listed below. |
| `orionis.auth.contracts` | All twelve contracts listed below. |

Use `orionis.auth.context.functions.authentication_lock`,
`orionis.auth.concerns.functions.authorizable_key`,
`orionis.auth.passwords.broker.PasswordBroker`, `orionis.auth.remember.RememberMe`,
`orionis.auth.manager.AuthManager` and `orionis.auth.provider.AuthProvider` from
their defining files. These names are not root reexports.

### Identity concerns

Sources: [Authenticatable](../concerns/authenticatable.py),
[Authorizable](../concerns/authorizable.py), [helpers](../concerns/functions.py),
[MustVerifyEmail](../concerns/must_verify_email.py).
Import paths are `orionis.auth.concerns.authenticatable`,
`orionis.auth.concerns.authorizable`, `orionis.auth.concerns.functions` and
`orionis.auth.concerns.must_verify_email`, respectively.

```python
class Authenticatable:
    AUTH_PASSWORD: ClassVar[str] = "password"
    def getAuthIdentifierName(self) -> str:
    def getAuthIdentifier(self) -> object:
    def getAuthPassword(self) -> str:

class Authorizable:
    AUTHORIZABLE_TYPE: ClassVar[str | None] = None
    def getAuthorizableType(self) -> str:
    def getAuthorizableId(self) -> object:

class MustVerifyEmail:

def authorizable_key(identity: object) -> tuple[str, str]:
def model_primary_key(instance: object) -> str:
```

`Authenticatable.getAuthIdentifierName()` uses the class metadata's nonempty
primary key name or `"id"`; the identifier accessor returns that attribute or
`None`. `getAuthPassword()` reads `AUTH_PASSWORD` and returns an empty string for
missing or non-string hashes. No password hashing is performed by the mixin.

`Authorizable.getAuthorizableType()` returns the explicit class value when it is
not `None`, otherwise the actual class module and qualified name.
`getAuthorizableId()` uses the same metadata/fallback lookup. Renaming a class
can therefore change its derived persisted owner type. The mixins register as
virtual subclasses of `IAuthenticatable` and `IAuthorizable`; they do not inherit
`ABCMeta` or add model storage themselves.

`authorizable_key()` accepts duck-typed callable owner accessors. It returns
owner type and canonical textual ID, each nonempty and at most 255 characters.
IDs must be `int`, `str` or `UUID`, excluding booleans. It raises `AuthException`
for invalid shapes/keys; exceptions from the object's accessors propagate.
Neither helper queries storage or strips values. `MustVerifyEmail` is an empty
marker class, not a verification sender, token issuer or middleware.

### AuthenticationContext and scope helpers

Sources and imports: `orionis.auth.context.context`
([implementation](../context/context.py)), `orionis.auth.context.functions`
([helpers](../context/functions.py)). Contract: `IAuthenticationContext`.

```python
class AuthenticationContext(IAuthenticationContext):
    def __init__(
        self,
        identity: IAuthenticatable | None = None,
        guard: str | None = None,
        abilities: Iterable[str] | None = None,
        repository: IPermissionRepository | None = None,
        credential_id: object | None = None,
    ) -> None:
    @property
    def identity(self) -> IAuthenticatable | None:
    @property
    def guard(self) -> str | None:
    @property
    def abilities(self) -> frozenset[str] | None:
    @property
    def credentialId(self) -> object | None:
    @property
    def isAuthenticated(self) -> bool:
    @property
    def isGuest(self) -> bool:
    def identifier(self) -> object | None:
    async def authorization(self) -> IAuthorizationSnapshot:
    def __repr__(self) -> str:

GUEST_CONTEXT: AuthenticationContext = AuthenticationContext()

def authentication_lock() -> asyncio.Lock:
def current_auth_context() -> IAuthenticationContext:
def bind_auth_context(context: IAuthenticationContext) -> None:
```

The constructor retains identity/repository references and materializes abilities
as a `frozenset`, or preserves `None`. It does not validate individual ability
names. Public properties have no setter/deleter. `identifier()` calls the current
identity's `getAuthIdentifier()` or returns `None`.

`bind_auth_context()` requires an active `ScopeManager`, assigns the context under
`IAuthenticationContext`, and binds built-in contexts other than `GUEST_CONTEXT`
to that scope. Reusing a built-in context in another scope raises `AuthException`.
Once bound, the identity and credential ID become `None` when that context is
replaced, the scope closes, or a different scope reads it. Guard/abilities remain
visible. An unbound context has no owner check; construction alone does not make
it scope-local. Custom contract implementations do not acquire the built-in
ownership checks through this helper.

`current_auth_context()` returns the current binding, or the shared guest when
no active scope/binding exists. An active scope is sufficient; it need not be an
HTTP request. `authentication_lock()` returns a scope-stored `asyncio.Lock` or
raises `AuthException` without an active scope. It serializes cooperating auth
operations, not arbitrary direct writes by application code.

`authorization()` returns `EMPTY_SNAPSHOT` for stale contexts, guests or missing
repositories. Otherwise it lazily calls `repository.loadFor(identity)`, caches an
`AuthorizationSnapshot`, and rechecks ownership after awaiting I/O. A context-owned
lock and a second cache check share a successful load among cooperating tasks.
Failed loads propagate and are not cached; a later call can retry. There is no
public refresh/invalidation method. `repr()` exposes guest state or guard and ID,
not password or token material. Private `_fork()` is lifecycle support, not a
public propagation API; it creates fresh ownership/cache/lock state.

### AuthorizationSnapshot

Import `orionis.auth.authorization.snapshot.AuthorizationSnapshot` and
`EMPTY_SNAPSHOT`; both are reexported by `orionis.auth.authorization`.
Source: [snapshot.py](../authorization/snapshot.py).

```python
class AuthorizationSnapshot(IAuthorizationSnapshot):
    def __init__(
        self,
        permissions: Iterable[str],
        roles: Iterable[str],
        abilities: Iterable[str] | None = None,
    ) -> None:
    @property
    def permissions(self) -> frozenset[str]:
    @property
    def roles(self) -> frozenset[str]:
    @property
    def abilities(self) -> frozenset[str] | None:
    def can(self, permission: str) -> bool:
    def hasRole(self, role: str) -> bool:
    def __repr__(self) -> str:

EMPTY_SNAPSHOT: AuthorizationSnapshot = AuthorizationSnapshot(
    permissions=(),
    roles=(),
)
```

Inputs are eagerly materialized and deduplicated. Properties expose read-only
`frozenset` values without copying them. `permissions` is the owned set, not a
precomputed intersection: `can()` requires membership in permissions and, when
present, abilities. `None` is unrestricted; an empty ability set permits nothing.
There is no wildcard expansion, case folding or name normalization. `hasRole()`
ignores credential abilities. Unhashable inputs/membership keys can propagate
`TypeError`; constructors do not enforce the annotated element type. Iterators
are consumed during construction. `repr()` shows collection counts and whether
abilities are unrestricted. This is a slotted class with read-only public
properties, not a frozen dataclass.

### ModelIdentityProvider

Import `orionis.auth.identity.provider.ModelIdentityProvider` or its identity
package reexport. Source: [provider.py](../identity/provider.py).

```python
class ModelIdentityProvider(IIdentityProvider):
    def __init__(self, app: IApplication, hasher: IHashManager) -> None:
    def model(self) -> type[Model]:
    async def retrieveById(self, identifier: object) -> IAuthenticatable | None:
    async def retrieveByCredentials(
        self,
        credentials: Mapping[str, object],
    ) -> IAuthenticatable | None:
    async def updateRememberToken(
        self,
        identity: IAuthenticatable,
        expected: str | None,
        token: str | None,
    ) -> bool:
    async def validateCredentials(
        self,
        identity: IAuthenticatable | None,
        credentials: Mapping[str, object],
    ) -> bool:
```

`model()` imports the configured dotted path on first use and caches the class.
Import/attribute/path failures and a value that is not an `IAuthenticatable`
subclass raise `IdentityProviderException`. The implementation checks that
contract, not ORM inheritance; later queries require the declared ORM metadata
and query methods. Configuration changes do not invalidate a resolved class.

`retrieveById(None)` returns `None` without resolving the model. Other keys must
be nonempty `int`, `str` or `UUID`, at most 255 textual characters, not booleans.
Integer-column keys are converted with `int`; UUID-column keys use `UUID` and
honor the column's `as_uuid`; other keys become text. Invalid conversions return
`None`. Model queries retain the model's scopes and soft-delete behavior.

`retrieveByCredentials()` reads only the configured username field; missing,
empty or non-string usernames return `None`. It does not strip/lowercase values
or check a password. `validateCredentials()` reads `"password"`, accepts a
nonempty string at most 4096 characters, and awaits the hasher. Missing identities
or missing stored hashes still call `make()` and return `False`. A `ValueError`
from hash verification is treated as invalid credentials; other failures propagate.
This does not guarantee equal timing. The inspected [Argon2 driver](../../hashing/hashers/argon2_hasher.py)
offloads hashing/checking with `asyncio.to_thread`.

`updateRememberToken()` returns `False` if the model lacks `remember_token`.
Otherwise it conditionally updates one row matching identity key, password hash
and expected token, using SQL NULL comparison for `expected=None`. A non-null
replacement also requires `active=True` in SQL. It returns whether exactly one
row changed; it does not mutate the supplied identity instance. It accesses
`identity.AUTH_PASSWORD` in addition to the three authentication contract methods.

### SessionGuard

Import `orionis.auth.guards.session_guard.SessionGuard`, also reexported by guards.
Source: [session_guard.py](../guards/session_guard.py). Contract: `ISessionGuard`.

```python
class SessionGuard(ISessionGuard):
    def __init__(self, app: IApplication, identities: IIdentityProvider) -> None:
    @property
    def name(self) -> str:
    async def resolve(self, request: Request) -> GuardResult | None:
    async def attempt(
        self,
        request: Request,
        credentials: Mapping[str, object],
        *,
        remember: bool = False,
    ) -> IAuthenticatable | None:
    def login(self, request: Request, identity: IAuthenticatable) -> None:
    async def logout(self, request: Request) -> None:
```

`name` is `"session"`. The constructor captures configuration/provider and creates
`RememberMe`. It can therefore propagate remember-settings errors, including a
cookie-name collision. No current identity is retained by the guard.

| Operation | Result, mutation and edge cases |
|---|---|
| `resolve(request)` | No session returns `None`. A stored identifier is looked up and its stored password fingerprint compared with the current hash. A missing identity/fingerprint or mismatch removes both auth session keys and tries remembered login. A valid ordinary session returns `GuardResult`; this branch does not check `active`. |
| `attempt(request, credentials, remember=...)` | Awaits lookup and credential verification, then requires Python `active is True`. Invalid credentials/status return `None`. Opt-in issues a remembered credential; opt-out forgets the previous one. It then calls `login()` and returns the identity, not a boolean. |
| `login(request, identity)` | Requires a session and a nonempty scalar ID of type `int`, `str` or `UUID`, excluding booleans; otherwise raises `AuthException`. It requests session regeneration, stores canonical ID/password fingerprint, creates a fresh CSRF token, and updates `request.state.csrf_token`. It neither checks the password nor checks `active`. |
| `logout(request)` | Revokes remembered login, removes the auth keys and invalidates the session. Without a session it only queues remember-cookie removal. Provider errors can propagate before invalidation. |

The guard itself does not save a session or emit a cookie. Those operations belong
to the surrounding [session middleware](../../http/layer/web/start_session.py)
and [session manager](../../session/manager.py). Calling a guard directly does not
bind an `AuthenticationContext`; middleware/manager perform that publication.

### RememberMe

Import `orionis.auth.remember.RememberMe` and `apply_remember_cookie`.
Source: [remember.py](../remember.py).

```python
class RememberMe:
    def __init__(self, app: IApplication, identities: IIdentityProvider) -> None:
    def clearCookie(self, request: Request) -> None:
    async def issue(self, request: Request, identity: IAuthenticatable) -> None:
    async def restore(self, request: Request) -> IAuthenticatable | None:
    async def revoke(self, request: Request, identifier: object) -> None:
    async def forget(self, request: Request, identity: IAuthenticatable) -> None:

def apply_remember_cookie(request: Request, response: Response) -> None:
```

Public instance state is `RememberMe.settings` (`RememberAuth`) and
`RememberMe.identities` (the injected provider), assigned without declared field
annotations. The class does not declare slots; these references can be replaced.
The constructor raises `ValueError` if its cookie equals `session.cookie`, and
propagates settings validation errors.

`issue()` requires `request.scheme == "https"` when secure settings are enabled,
then creates an identity selector, expiry and 32-byte random secret. Storage holds
a versioned digest bound to the whole cookie and current password hash. It uses
`updateRememberToken(identity, expected, replacement)` and raises `AuthException`
if persistence reports failure. Callers must verify the password first: this
method itself does not do so. A new issue replaces the identity's single grant.

`restore()` returns `None` for insecure transport, missing/non-string cookies,
invalid credentials, inactive identities or a lost compare-and-replace race.
Cookies are limited to 512 characters and the exact selector/expiry/43-character
secret pattern. Malformed or expired presented values queue deletion; missing
identities and digest mismatches do not necessarily queue a cookie change.
A successful restore rotates the credential, preserves the original deadline,
and queues the remaining lifetime. It returns the identity without logging in
or binding a context; `SessionGuard` performs the session transition.

`revoke()` retrieves the supplied identifier when not `None`, forgets its grant
if found and clears the cookie. `forget()` compare-and-replaces an existing token
with `None` and queues deletion; a false update result is not raised. Provider
exceptions propagate. `clearCookie()` only queues an empty cookie with zero age.

Queued state lives on the request. `apply_remember_cookie()` does nothing without
pending state; otherwise it calls `response.setCookie()` and sets `Cache-Control`
to `"no-store"`. Cookies use `/`, HttpOnly, configured Secure and SameSite lax,
with no Domain. Applying the queue does not clear it. Cookie expiry, digest
comparison and conditional rotation are separate from ordinary session storage.

### TokenGuard

Import `orionis.auth.guards.token_guard.TokenGuard`, also reexported by guards.
Source: [token_guard.py](../guards/token_guard.py). Contract: `IGuard`.

```python
class TokenGuard(IGuard):
    def __init__(
        self,
        tokens: IAccessTokenRepository,
        identities: IIdentityProvider,
    ) -> None:
    @property
    def name(self) -> str:
    async def resolve(self, request: Request) -> GuardResult | None:
```

`name` is `"token"`. `resolve()` reads `request.bearerToken`, looks up metadata,
retrieves the owner, verifies its callable authorizable accessors against both
stored type and canonical ID, then awaits `touch(id)`. Missing/unusable credentials,
owners, owner mismatches or failed touch return `None`. Success returns
`GuardResult` with record abilities and credential ID. It does not check `active`,
perform password hashing, start a session or bind a context. Dependency failures
propagate; revocation does not cancel work already in progress.

The [Request.bearerToken implementation](../../http/request.py) accepts a
case-insensitive Bearer scheme, strips surrounding token whitespace and rejects
duplicate Authorization headers. That parsing belongs to Request, not TokenGuard.

### Token functions and entities

Imports and sources: `orionis.auth.tokens.functions`
([helpers](../tokens/functions.py)), `orionis.auth.entities.access_token`
([AccessToken](../entities/access_token.py)), `orionis.auth.entities.guard_result`
([GuardResult](../entities/guard_result.py)), `orionis.auth.entities.new_access_token`
([NewAccessToken](../entities/new_access_token.py)).

```python
def generate_token_secret(size: int) -> str:
def hash_token_secret(secret: str) -> str:

@dataclass(frozen=True, slots=True, kw_only=True)
class AccessToken:
    id: object
    tokenable_type: str
    tokenable_id: object
    name: str
    abilities: frozenset[str] | None = None
    created_at: datetime | None = None
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None
    def toDict(self) -> dict[str, object]:

@dataclass(frozen=True, slots=True, kw_only=True)
class GuardResult:
    identity: IAuthenticatable
    guard: str
    abilities: frozenset[str] | None = None
    credential_id: object | None = None

@dataclass(frozen=True, slots=True, kw_only=True)
class NewAccessToken:
    access_token: AccessToken
    plain_text: str = field(repr=False)
    def toDict(self) -> dict[str, object]:
```

`generate_token_secret()` delegates to `secrets.token_urlsafe(size)` without its
own size-range validation. `hash_token_secret()` UTF-8 encodes a string and returns
its 64-character hexadecimal SHA-256 digest. Neither performs I/O. Standard-library
type/encoding/size failures can propagate; this digest helper is not the password
hashing service.

The dataclass decorator generates constructors, equality, representation and
frozen assignment behavior; no explicit constructors are declared here.
All constructor fields are keyword-only, with required fields/defaults shown
above. Dataclasses do not validate annotated types or deep-freeze arbitrary
referenced objects. `GuardResult` retains the identity reference.

| Entity | Field meanings |
|---|---|
| `AccessToken` | `id`: token-row key; `tokenable_type`/`tokenable_id`: polymorphic owner type/key; `name`: issuance label; `abilities`: credential limits; `created_at`: issuance moment; `expires_at`: deadline; `last_used_at`: recorded use; `revoked_at`: revocation moment. All four timestamp fields default to None. |
| `GuardResult` | `identity`: resolved object; `guard`: producing guard name; `abilities`: credential limits; `credential_id`: revocable credential key, or None. |
| `NewAccessToken` | `access_token`: stored metadata; `plain_text`: freshly issued bearer secret. Neither field has a value default. |

`AccessToken.toDict()` calls `dataclasses.asdict()` and returns copied metadata,
including native dates and ability collections, not JSON serialization.
`NewAccessToken.toDict()` returns only `{"access_token": ...}` metadata. Its
generated `repr()` excludes `plain_text`; the attribute remains directly readable.
Generic `dataclasses.asdict()` still exposes it. No field stores the database
digest on `AccessToken`; a plain secret is returned only by issuance, not lookup.

### AccessTokenRepository

Import `orionis.auth.tokens.repository.AccessTokenRepository`, also reexported by
tokens. Source: [repository.py](../tokens/repository.py).

```python
class AccessTokenRepository(IAccessTokenRepository):
    def __init__(self, app: IApplication, db: IQueryBuilder) -> None:
    async def create(
        self,
        tokenable: IAuthorizable,
        name: str,
        *,
        abilities: Iterable[str] | None = None,
        expires_at: datetime | None = None,
    ) -> NewAccessToken:
    async def findByPlainText(self, plain_text: str) -> AccessToken | None:
    async def touch(self, token_id: object) -> bool:
    async def revoke(self, token_id: object) -> bool:
    async def revokeAll(self, tokenable: IAuthorizable) -> int:
    async def purgeExpired(self) -> int:
```

`create()` stores a random secret's digest, canonical owner key, raw name, encoded
abilities and timestamps, then returns `NewAccessToken`. Names must be strings
with a nonblank value and at most 255 characters; surrounding spaces are preserved.
Abilities reject strings/bytes as the collection, unhashable values, more than
256 distinct entries, non-string names, blank names and names longer than 255.
They become a `frozenset`; duplicates collapse and padding is preserved. The
size bound is checked after materializing the iterable. Invalid token values
raise `TokenException`; invalid owners raise `AuthException` from key normalization.

An explicit deadline is normalized to UTC without a timezone offset. `None`
applies configured expiration minutes, or remains unlimited if absent. The
implementation also accepts parseable ISO timestamp strings despite the declared
datetime annotation; malformed non-null values raise `TokenException`. Already
expired deadlines may be stored but fail later lookup. Storage JSON is a sorted
ability array, or SQL NULL for unrestricted access.

If insertion supplies no generated ID, creation reads it back by unique digest.
A missing row then raises `TokenException`. SQL failures propagate; issuance does
not create an application transaction or retry a random-digest collision.

`findByPlainText()` rejects non-string, empty and over-512-character inputs before
I/O. Unknown, revoked, expired or malformed stored timestamps/abilities return
`None`; null timestamps are accepted. A found record contains metadata, not the
secret. `touch(None)`/`revoke(None)` return `False`; otherwise touch conditionally
updates an unrevoked row with a null or future deadline, while revoke marks an
unrevoked row regardless of expiry. Both return whether rows changed.

`revokeAll()` marks all unrevoked rows matching owner type and canonical ID and
returns the affected count. `purgeExpired()` performs two deletes, first elapsed
deadlines, then remaining revoked rows, and returns their summed counts. None of
these methods directly changes a request context; the manager's current-token
revocation adds that transition.

### Authorizer, Policy and PolicyRegistry

Imports: `orionis.auth.authorization.authorizer.Authorizer`,
`orionis.auth.authorization.policy.Policy`,
`orionis.auth.authorization.registry.PolicyRegistry`. Sources:
[authorizer](../authorization/authorizer.py), [policy](../authorization/policy.py),
[registry](../authorization/registry.py).

```python
class Authorizer(IAuthorizer):
    def __init__(self, app: IApplication) -> None:
    def registry(self) -> PolicyRegistry:
    def registerPolicy(self, resource: type, policy: type[IPolicy]) -> None:
    async def can(
        self,
        context: IAuthenticationContext,
        permission: str,
    ) -> bool:
    async def canAny(
        self,
        context: IAuthenticationContext,
        permissions: Iterable[str],
    ) -> bool:
    async def canAll(
        self,
        context: IAuthenticationContext,
        permissions: Iterable[str],
    ) -> bool:
    async def hasRole(
        self,
        context: IAuthenticationContext,
        role: str,
    ) -> bool:
    async def allows(
        self,
        context: IAuthenticationContext,
        ability: str,
        resource: object,
    ) -> bool:

class Policy(IPolicy):
    async def before(self, identity: object, ability: str) -> bool | None:

class PolicyRegistry:
    def __init__(self) -> None:
    def register(self, resource: type, policy: type[IPolicy]) -> None:
    def policyFor(self, resource: type) -> type[IPolicy] | None:
    def bindings(self) -> dict[type, type[IPolicy]]:
```

Permission/role operations deny guests without loading a snapshot and recheck
authentication after awaiting one. `canAny()`/`canAll()` use short-circuiting
`any()`/`all()` over the iterable: empty input is respectively false/true for an
authenticated context, but both are false for guests. These methods do not copy
the supplied iterable; a one-shot iterator may be only partly consumed.

`allows()` denies guests, invalid identifiers, underscore-prefixed abilities,
`before` and abilities absent from a non-null credential restriction before
policy construction. It resolves the resource class itself or the instance's
type. Missing policy raises `PolicyNotFoundException`. Each evaluation awaits
`app.build(policy_class)` to create a fresh policy.

The `before` hook is always awaited. `None` continues; any other value stops
evaluation, but only literal `True` grants. Only after that hook does the
authorizer require a callable ability handler; a missing handler then raises
`PolicyNotFoundException`. Ability handlers receive identity and resource and
may return synchronously or yield an awaitable. Again only literal `True` grants,
and the context must still expose the same identity object after evaluation.
Hooks, DI and handlers can propagate their own exceptions. The default
`Policy.before()` returns `None`; overriding it with a synchronous hook does not
match this awaited contract. A granting hook can bypass a missing handler, but
cannot bypass credential restrictions checked earlier.

`registry()` returns the live registry. `register()` requires a resource class
and an `IPolicy` subclass or raises `TypeError`, replaces any existing binding,
and clears all cached lookups. `policyFor()` walks the resource MRO on a miss and
caches either a policy class or `None`; the cache has no declared size limit.
`bindings()` returns a shallow dictionary copy. No policy instance is cached.

### PermissionRegistrar and DatabasePermissionRepository

Imports: `orionis.auth.authorization.registrar.PermissionRegistrar` and
`orionis.auth.authorization.repository.DatabasePermissionRepository`.
Sources: [registrar](../authorization/registrar.py),
[repository](../authorization/repository.py).

```python
class PermissionRegistrar:
    def __init__(self, db: IQueryBuilder) -> None:
    async def createPermission(self, name: str) -> object:
    async def createRole(self, name: str) -> object:
    async def givePermissionTo(
        self,
        authorizable: IAuthorizable,
        *permissions: str,
    ) -> None:
    async def revokePermissionFrom(
        self,
        authorizable: IAuthorizable,
        *permissions: str,
    ) -> None:
    async def assignRole(
        self,
        authorizable: IAuthorizable,
        *roles: str,
    ) -> None:
    async def removeRole(
        self,
        authorizable: IAuthorizable,
        *roles: str,
    ) -> None:
    async def grantToRole(self, role: str, *permissions: str) -> None:
    async def revokeFromRole(self, role: str, *permissions: str) -> None:

class DatabasePermissionRepository(IPermissionRepository):
    def __init__(self, db: IQueryBuilder) -> None:
    async def loadFor(
        self,
        authorizable: IAuthorizable,
    ) -> tuple[frozenset[str], frozenset[str]]:
```

Creation returns an existing/new row ID. Newly created names must be nonempty,
unpadded strings at most 255 characters or raise `AuthException`. A lost insert
is recovered inside a transaction/savepoint only when the matching row exists;
otherwise `QueryException` propagates. Missing generated IDs trigger a name
lookup; inability to recover a row ID raises `AuthException`.

Grant/assign methods create missing named rows and attach polymorphic pivots.
Composite keys make duplicate assignment recoverable through a verified identical
row. Revoke/remove methods delete only matching pivots and ignore unknown names;
they do not remove role/permission definitions. Owner-oriented methods validate
the owner even with no variadic names. `grantToRole()` still creates/resolves its
role with an empty permission list; `revokeFromRole()` looks up the role first.
Operations over multiple names are sequential, not one all-or-nothing transaction
covering the whole method. Registrar changes do not invalidate existing contexts'
snapshots.

`loadFor()` normalizes the owner; an `AuthException` from that normalization yields
two empty sets instead of querying. Other accessor/query errors propagate. One
UNION statement collects role names, direct permissions and role-inherited
permissions; results are materialized into permission and role `frozenset`s in
that order. It has no permission cache of its own and uses the five fixed table
names, not a configurable guard namespace. Roles have no hierarchy.

### AuthManager

Import `orionis.auth.manager.AuthManager`. Source: [manager.py](../manager.py).
The external facade `orionis.support.facades.auth.Auth` exposes this contract after
its provider boot; it is not the configuration entity also named Auth.

```python
class AuthManager(IAuthManager):
    def __init__(
        self,
        app: IApplication,
        authorizer: IAuthorizer,
        permissions: IPermissionRepository,
        session_guard: ISessionGuard,
        token_guard: TokenGuard,
        tokens: IAccessTokenRepository,
    ) -> None:
    def context(self) -> IAuthenticationContext:
    def user(self) -> IAuthenticatable | None:
    def identifier(self) -> object | None:
    def check(self) -> bool:
    def guest(self) -> bool:
    def guard(self, name: str | None = None) -> IGuard:
    async def attempt(
        self, credentials: Mapping[str, object], *, remember: bool = False,
    ) -> bool:
    async def login(self, identity: IAuthenticatable) -> None:
    async def logout(self) -> None:
    async def authorization(self) -> IAuthorizationSnapshot:
    async def can(self, permission: str) -> bool:
    async def cannot(self, permission: str) -> bool:
    async def canAny(self, permissions: Iterable[str]) -> bool:
    async def canAll(self, permissions: Iterable[str]) -> bool:
    async def hasRole(self, role: str) -> bool:
    async def authorize(self, permission: str) -> None:
    async def allows(self, ability: str, resource: object) -> bool:
    async def denies(self, ability: str, resource: object) -> bool:
    async def authorizeResource(self, ability: str, resource: object) -> None:
    def registerPolicy(self, resource: type, policy: type[IPolicy]) -> None:
    async def createToken(
        self,
        name: str,
        *,
        tokenable: IAuthorizable | None = None,
        abilities: Iterable[str] | None = None,
        expires_at: datetime | None = None,
    ) -> NewAccessToken:
    async def revokeCurrentToken(self) -> bool:
```

The constructor stores the two injected guards by their names and a configured
default. There is no public guard-registration method. `guard()` uses the default
for `None` or other falsy names and raises `GuardNotFoundException` for an unknown
key. Read-only state methods are synchronous and consult the current context;
outside a scope they observe a guest.

`attempt()`, `login()` and `logout()` require an active scope with a value stored
under the actual `Request` key or raise `AuthException`. They cooperate through
`authentication_lock()` and always use the session guard, irrespective of default
or previously resolved guard. Attempt converts the guard's identity/`None` result
into a boolean; failed attempt does not rebind the existing context. Successful
attempt/login binds a fresh session context with the permission repository.
Logout binds a guest session context after guard logout. Direct manager session
transitions do not apply the resolver middleware's guard-switch prohibition.

Authorization methods delegate to the context/authorizer. `cannot()` and `denies()`
negate their respective boolean checks. `authorize()`/`authorizeResource()` return
`None` when allowed, raise `AuthenticationException` for guests, or
`AuthorizationException` for denied authenticated identities. Policy lookup and
dependency failures remain visible. `registerPolicy()` mutates the authorizer's
registry.

`createToken()` rejects a context with non-null credential ID using
`AuthorizationException`, even if an explicit owner is supplied. Otherwise it uses
`tokenable` or the current identity: absence raises `AuthenticationException`;
an owner not implementing `IAuthorizable` raises `AuthException`. An explicit
authorizable owner can be used outside an authenticated request. Repository
validation/persistence errors propagate.

`revokeCurrentToken()` returns `False` without a credential; otherwise it takes
the transition lock, rechecks the current credential, revokes it and binds a
guest context preserving the guard. Identity is cleared even if revoke returns
`False`; a raised repository failure prevents that rebind.

### Middleware

All ten classes are reexported from `orionis.auth.middleware`.
Source files and defining import suffixes: [resolve_identity](../middleware/resolve_identity.py),
[authenticate](../middleware/authenticate.py), [guest](../middleware/guest.py),
[authorize](../middleware/authorize.py), [policy](../middleware/policy.py).
They inherit [BaseMiddleware](../../http/middleware.py); `call_next` is a no-argument
async callable returning `Response`.

```python
class ResolveIdentityMiddleware(BaseMiddleware):
    guard: ClassVar[str | None] = None
    def __init__(
        self,
        manager: IAuthManager,
        permissions: IPermissionRepository,
    ) -> None:
    async def handle(
        self,
        request: Request,
        call_next: NextCallable,
    ) -> Response:

class ResolveSessionIdentityMiddleware(ResolveIdentityMiddleware):
    guard: ClassVar[str | None] = Guards.SESSION.value
    async def handle(self, request: Request, call_next: NextCallable) -> Response:

class ResolveTokenIdentityMiddleware(ResolveIdentityMiddleware):
    guard: ClassVar[str | None] = Guards.TOKEN.value

class AuthenticateMiddleware(ResolveIdentityMiddleware):
    cache_control: ClassVar[str | None] = "no-store, private"
    def __init__(
        self,
        app: IApplication,
        manager: IAuthManager,
        permissions: IPermissionRepository,
    ) -> None:
    async def handle(
        self,
        request: Request,
        call_next: NextCallable,
    ) -> Response:

class AuthenticateSessionMiddleware(AuthenticateMiddleware):
    guard: ClassVar[str | None] = Guards.SESSION.value

class AuthenticateTokenMiddleware(AuthenticateMiddleware):
    guard: ClassVar[str | None] = Guards.TOKEN.value

class GuestMiddleware(ResolveIdentityMiddleware):
    guard: ClassVar[str | None] = Guards.SESSION.value
    redirect_to: ClassVar[str | None] = None
    def __init__(
        self,
        app: IApplication,
        manager: IAuthManager,
        permissions: IPermissionRepository,
    ) -> None:
    async def handle(self, request: Request, call_next: NextCallable) -> Response:

class RequirePermissionMiddleware(BaseMiddleware):
    permissions: ClassVar[tuple[str, ...]] = ()
    requires_all: ClassVar[bool] = True
    def __init__(self, authorizer: IAuthorizer) -> None:
    async def handle(
        self,
        request: Request,
        call_next: NextCallable,
    ) -> Response:

class RequireRoleMiddleware(BaseMiddleware):
    roles: ClassVar[tuple[str, ...]] = ()
    requires_all: ClassVar[bool] = False
    def __init__(self, authorizer: IAuthorizer) -> None:
    async def handle(
        self,
        request: Request,
        call_next: NextCallable,
    ) -> Response:

class RequirePolicyMiddleware(BaseMiddleware):
    ability: ClassVar[str] = ""
    resource: ClassVar[type | None] = None
    def __init__(self, authorizer: IAuthorizer) -> None:
    async def handle(
        self,
        request: Request,
        call_next: NextCallable,
    ) -> Response:
```

Subclass variants inherit their base constructor/handler unless explicitly shown.
Class variables define restrictions; instances are slotted. Declaring a real,
importable subclass matches the class-based [router](../../http/routes/router.py)
and [route cache](../../http/routes/route_cache.py), rather than passing a
parameterized middleware instance.

| Class/group | Behavior and failures |
|---|---|
| `ResolveIdentityMiddleware` | Under the transition lock, chooses its explicit guard, the current context's guard, or the manager default. Same-guard resolution reuses authenticated and guest results. Switching an authenticated context to another guard raises `AuthenticationException`. Missing scope raises `AuthException`; unknown guard propagates `GuardNotFoundException`. It binds the resolved/guest context and calls the next layer. |
| `ResolveSessionIdentityMiddleware` | Pins `"session"`, inherits resolution and applies queued remember cookies after successful downstream return. It does not apply that hook if downstream raises. |
| `ResolveTokenIdentityMiddleware` | Pins `"token"` and inherits the guest-permitting handler. |
| `AuthenticateMiddleware` and variants | Require identity. A session-guard guest browser with configured redirect target receives a 302; JSON/AJAX guests and token guests raise `AuthenticationException`. Returned downstream/redirect responses receive configured Cache-Control if truthy. Exceptions do not pass through that response-header step. |
| `GuestMiddleware` | Pins session by default. Guests continue. Authenticated JSON/AJAX callers raise `AuthorizationException`; other authenticated callers receive a home redirect. Destination is the class override, configured home, or fallback. |
| `RequirePermissionMiddleware` | Empty permissions raise `AuthConfigurationException` before identity checks. Guests raise `AuthenticationException`; failed all/any permission checks raise `AuthorizationException`. Default requires all. It does not resolve a guard itself. |
| `RequireRoleMiddleware` | Empty roles/configuration and guests have the same error ordering. Any non-null credential abilities, including an empty set, raise `AuthorizationException`. Default accepts any role; all mode short-circuits on a missing role. |
| `RequirePolicyMiddleware` | Missing ability/resource raises `AuthConfigurationException`; guests raise `AuthenticationException`; denied abilities raise `AuthorizationException`. It passes the declared resource class to the authorizer; missing policies/handlers may propagate `PolicyNotFoundException`. |

Only the authenticate group adds its protection Cache-Control. Public identity
resolution, role/permission/policy gates and guest redirects do not independently
add that header. The core kernel identity layers are separate from route middleware
exclusions; API identity resolution does not start a session.

### PasswordBroker

Import `orionis.auth.passwords.broker.PasswordBroker`; the passwords initializer
does not reexport it. Source: [broker.py](../passwords/broker.py).

```python
class PasswordBroker:
    def __init__(
        self, app: IApplication, db: IQueryBuilder, hashing: IHashManager,
    ) -> None:
    async def issue(self, email: str) -> tuple[Model, str] | None:
    async def valid(self, email: str, token: str) -> bool:
    async def reset(self, email: str, token: str, password: str) -> Model | None:
```

Public unannotated instance fields are `PasswordBroker.settings`,
`PasswordBroker.model`, `PasswordBroker.db`, `PasswordBroker.hashing` and
`PasswordBroker.tokens`: validated reset settings, eagerly resolved identity
model, gateway selected for the model's connection, injected hasher and access
token repository. They are mutable references; the broker does not declare slots.
Model import/configuration failures can occur during construction.

All three operations strip and lowercase the email. Unlike identity credential
lookup, they query the literal `email` column regardless of configured username.
`issue()` returns `None` for unknown identities or an unelapsed cooldown. An issued
value is `(identity, plain_reset_token)`; storage holds digest, canonical ID,
password fingerprint and Unix creation seconds. The first insert uses the email
primary key; subsequent issuance updates only a row older than the throttle.
A caught `QueryException` is absorbed only if an email row now exists; other SQL
errors propagate. Consumed rows remain to enforce cooldown.

`valid()` does not consume a token. It requires an exact 43-character URL-safe
secret, matching digest, creation strictly newer than the expiry boundary, the
same current account ID and unchanged password fingerprint. Invalid/stale/expired
values return `False`; dependency failures remain visible. Neither issuance nor
validation independently checks account activation.

`reset()` resolves the credential, hashes the replacement before opening a
transaction, then conditionally nulls the token and updates the same account's
password only while its old hash still matches. It clears `remember_token` when
the model declares that column, and revokes access tokens when the identity
implements `IAuthorizable`. A stale password update raises a private exception
that rolls back and becomes `None`; other failures propagate with transaction
rollback. An already consumed/invalid credential returns `None`.

**Observed discrepancy:** the docstring describes an updated returned identity,
but the implementation returns its earlier loaded instance without refreshing
attributes. Read the persisted identity again to inspect its new password or
remember-token state. The workflow example verifies this distinction. Password
strength/confirmation and email delivery are not performed by this broker.
Existing session fingerprints reject the changed password on a later resolution;
the broker does not enumerate or delete session-store records.

### AuthProvider

Import `orionis.auth.provider.AuthProvider`. Source: [provider.py](../provider.py).
Base lifecycle: [ServiceProvider](../../container/providers/service_provider.py).

```python
class AuthProvider(ServiceProvider):
    def register(self) -> None:
    async def boot(self) -> None:
```

The provider is listed by [CORE_PROVIDER_METADATA](../../foundation/core_providers.py)
and is not deferrable. `register()` declares exactly these bindings:

| Lifetime | Contract/key to implementation |
|---|---|
| Scoped | `IAuthenticationContext` to `AuthenticationContext`. |
| Singleton | `IIdentityProvider` to `ModelIdentityProvider`; `IPermissionRepository` to `DatabasePermissionRepository`; `IAuthorizer` to `Authorizer`; `PermissionRegistrar` to itself; `IAccessTokenRepository` to `AccessTokenRepository`; `ISessionGuard` to `SessionGuard`; `TokenGuard` to itself; `IAuthManager` to `AuthManager`. |

`boot()` awaits `Auth.pin()`. Merely importing a package or registering bindings
does not pin the facade. The inspected [Application.boot](../../foundation/application.py)
creates the application and boots eager providers for headless usage; HTTP/CLI
startup also boots them. After pinning, the manager's sync methods stay sync and
its async methods must still be awaited. `RememberMe` is constructed by the guard;
`PasswordBroker` is not explicitly registered by AuthProvider.

### Exceptions

All defining imports use `orionis.auth.exceptions`; all eight names are root
reexports. Source: [exceptions.py](../exceptions.py).

```python
class AuthException(Exception):
class AuthConfigurationException(AuthException):
class AuthenticationException(AuthException):
class AuthorizationException(AuthException):
class GuardNotFoundException(AuthException):
class IdentityProviderException(AuthException):
class PolicyNotFoundException(AuthException):
class TokenException(AuthException):
```

They inherit the standard exception constructor and declare no additional fields.
Concrete conditions appear with the API that raises them. In particular,
`AuthConfigurationException` is explicitly used by empty middleware declarations,
not every configuration error; entity validators also raise `TypeError` or
`ValueError`. Raw ORM/hash/import errors are not automatically converted into
`AuthException`.

The inspected [exception handler](../../failure/base/handler.py) maps
`AuthenticationException` and subclasses to 401, and `AuthorizationException`
and subclasses to 403. It selects JSON using `request.wantsJson()` and adds
`WWW-Authenticate: Bearer` for authentication failures with the current token
guard. A redirect produced by authentication middleware is an alternative
response, not an exception-to-status mapping.

### Contracts

The [contracts initializer](../contracts/__init__.py) reexports all twelve ABCs.
They declare empty slots. Abstract methods describe extension points, not
concrete database/scope implementations; instantiating an incomplete abstract
implementation raises the standard `TypeError`. Relevant concrete behavior is
documented above. The following declaration fragments include every member.

`orionis.auth.contracts.authenticatable.IAuthenticatable`
([source](../contracts/authenticatable.py)) and
`orionis.auth.contracts.authorizable.IAuthorizable`
([source](../contracts/authorizable.py)):

```python
class IAuthenticatable(ABC):
    @abstractmethod
    def getAuthIdentifierName(self) -> str:
    @abstractmethod
    def getAuthIdentifier(self) -> object:
    @abstractmethod
    def getAuthPassword(self) -> str:

class IAuthorizable(ABC):
    @abstractmethod
    def getAuthorizableType(self) -> str:
    @abstractmethod
    def getAuthorizableId(self) -> object:
```

`orionis.auth.contracts.guard.IGuard` ([source](../contracts/guard.py)) and
`orionis.auth.contracts.session_guard.ISessionGuard`
([source](../contracts/session_guard.py)); the latter inherits name/resolution:

```python
class IGuard(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
    @abstractmethod
    async def resolve(self, request: Request) -> GuardResult | None:

class ISessionGuard(IGuard):
    @abstractmethod
    async def attempt(
        self,
        request: Request,
        credentials: Mapping[str, object],
        *, remember: bool = False,
    ) -> IAuthenticatable | None:
    @abstractmethod
    def login(self, request: Request, identity: IAuthenticatable) -> None:
    @abstractmethod
    async def logout(self, request: Request) -> None:
```

`orionis.auth.contracts.identity_provider.IIdentityProvider`
([source](../contracts/identity_provider.py)). Only the last three methods below
are abstract. `updateRememberToken()` has a base body returning `False`; its
documented optional implementation must compare password/expected credential and
require an active identity when issuing a non-null replacement.

```python
class IIdentityProvider(ABC):
    async def updateRememberToken(
        self,
        identity: IAuthenticatable,
        expected: str | None,
        token: str | None,
    ) -> bool:
    @abstractmethod
    async def retrieveById(self, identifier: object) -> IAuthenticatable | None:
    @abstractmethod
    async def retrieveByCredentials(
        self,
        credentials: Mapping[str, object],
    ) -> IAuthenticatable | None:
    @abstractmethod
    async def validateCredentials(
        self,
        identity: IAuthenticatable | None,
        credentials: Mapping[str, object],
    ) -> bool:
```

`orionis.auth.contracts.context.IAuthenticationContext`
([source](../contracts/context.py)) and
`orionis.auth.contracts.snapshot.IAuthorizationSnapshot`
([source](../contracts/snapshot.py)); properties are getter-only:

```python
class IAuthenticationContext(ABC):
    @property
    @abstractmethod
    def identity(self) -> IAuthenticatable | None:
    @property
    @abstractmethod
    def guard(self) -> str | None:
    @property
    @abstractmethod
    def abilities(self) -> frozenset[str] | None:
    @property
    @abstractmethod
    def credentialId(self) -> object | None:
    @property
    @abstractmethod
    def isAuthenticated(self) -> bool:
    @property
    @abstractmethod
    def isGuest(self) -> bool:
    @abstractmethod
    def identifier(self) -> object | None:
    @abstractmethod
    async def authorization(self) -> IAuthorizationSnapshot:

class IAuthorizationSnapshot(ABC):
    @property
    @abstractmethod
    def permissions(self) -> frozenset[str]:
    @property
    @abstractmethod
    def roles(self) -> frozenset[str]:
    @property
    @abstractmethod
    def abilities(self) -> frozenset[str] | None:
    @abstractmethod
    def can(self, permission: str) -> bool:
    @abstractmethod
    def hasRole(self, role: str) -> bool:
```

`orionis.auth.contracts.permission_repository.IPermissionRepository`
([source](../contracts/permission_repository.py)),
`orionis.auth.contracts.policy.IPolicy` ([source](../contracts/policy.py)) and
`orionis.auth.contracts.authorizer.IAuthorizer`
([source](../contracts/authorizer.py)):

```python
class IPermissionRepository(ABC):
    @abstractmethod
    async def loadFor(
        self,
        authorizable: IAuthorizable,
    ) -> tuple[frozenset[str], frozenset[str]]:

class IPolicy(ABC):
    @abstractmethod
    async def before(self, identity: object, ability: str) -> bool | None:

class IAuthorizer(ABC):
    @abstractmethod
    async def can(
        self,
        context: IAuthenticationContext,
        permission: str,
    ) -> bool:
    @abstractmethod
    async def canAny(
        self,
        context: IAuthenticationContext,
        permissions: Iterable[str],
    ) -> bool:
    @abstractmethod
    async def canAll(
        self,
        context: IAuthenticationContext,
        permissions: Iterable[str],
    ) -> bool:
    @abstractmethod
    async def hasRole(
        self,
        context: IAuthenticationContext,
        role: str,
    ) -> bool:
    @abstractmethod
    async def allows(
        self,
        context: IAuthenticationContext,
        ability: str,
        resource: object,
    ) -> bool:
    @abstractmethod
    def registerPolicy(self, resource: type, policy: type[IPolicy]) -> None:
```

`orionis.auth.contracts.token_repository.IAccessTokenRepository`
([source](../contracts/token_repository.py)):

```python
class IAccessTokenRepository(ABC):
    @abstractmethod
    async def create(
        self,
        tokenable: IAuthorizable,
        name: str,
        *,
        abilities: Iterable[str] | None = None,
        expires_at: datetime | None = None,
    ) -> NewAccessToken:
    @abstractmethod
    async def findByPlainText(self, plain_text: str) -> AccessToken | None:
    @abstractmethod
    async def touch(self, token_id: object) -> bool:
    @abstractmethod
    async def revoke(self, token_id: object) -> bool:
    @abstractmethod
    async def revokeAll(self, tokenable: IAuthorizable) -> int:
    @abstractmethod
    async def purgeExpired(self) -> int:
```

`orionis.auth.contracts.manager.IAuthManager` ([source](../contracts/manager.py)):

```python
class IAuthManager(ABC):
    @abstractmethod
    def context(self) -> IAuthenticationContext:
    @abstractmethod
    def user(self) -> IAuthenticatable | None:
    @abstractmethod
    def identifier(self) -> object | None:
    @abstractmethod
    def check(self) -> bool:
    @abstractmethod
    def guest(self) -> bool:
    @abstractmethod
    def guard(self, name: str | None = None) -> IGuard:
    @abstractmethod
    async def attempt(
        self, credentials: Mapping[str, object], *, remember: bool = False,
    ) -> bool:
    @abstractmethod
    async def login(self, identity: IAuthenticatable) -> None:
    @abstractmethod
    async def logout(self) -> None:
    @abstractmethod
    async def authorization(self) -> IAuthorizationSnapshot:
    @abstractmethod
    async def can(self, permission: str) -> bool:
    @abstractmethod
    async def cannot(self, permission: str) -> bool:
    @abstractmethod
    async def canAny(self, permissions: Iterable[str]) -> bool:
    @abstractmethod
    async def canAll(self, permissions: Iterable[str]) -> bool:
    @abstractmethod
    async def hasRole(self, role: str) -> bool:
    @abstractmethod
    async def authorize(self, permission: str) -> None:
    @abstractmethod
    async def allows(self, ability: str, resource: object) -> bool:
    @abstractmethod
    async def denies(self, ability: str, resource: object) -> bool:
    @abstractmethod
    async def authorizeResource(self, ability: str, resource: object) -> None:
    @abstractmethod
    def registerPolicy(self, resource: type, policy: type[IPolicy]) -> None:
    @abstractmethod
    async def createToken(
        self,
        name: str,
        *,
        tokenable: IAuthorizable | None = None,
        abilities: Iterable[str] | None = None,
        expires_at: datetime | None = None,
    ) -> NewAccessToken:
    @abstractmethod
    async def revokeCurrentToken(self) -> bool:
```

## Usage examples

Each block is an independent script targeting Python 3.14+ with the framework
installed, or this checkout on `PYTHONPATH`. Each was syntax-checked, had its
Orionis imports resolved to the inspected local checkout, and executed successfully
on CPython 3.14.6/Windows. The first two do not write resources; database examples
change into their own temporary directory before importing service configuration.
Minimal request/application doubles are explicit, not full HTTP transports.
Low hashing costs below are test preparation, not production settings.

### Context, snapshot and a real exception

Eight concurrent checks reuse one repository load. Replacing the context makes
the old reference anonymous; binding without a scope raises `AuthException`.
Status: **executed successfully**.

```python
import asyncio
from orionis.auth import Authenticatable, Authorizable, AuthenticationContext
from orionis.auth.authorization import EMPTY_SNAPSHOT, AuthorizationSnapshot
from orionis.auth.context import bind_auth_context, current_auth_context
from orionis.auth.contracts import IAuthorizable, IPermissionRepository
from orionis.auth.exceptions import AuthException
from orionis.container.context.manager import ScopeManager


class Identity(Authenticatable, Authorizable):
    __slots__ = ("id",)

    def __init__(self) -> None:
        self.id = 7


class Permissions(IPermissionRepository):
    __slots__ = ("loads",)

    def __init__(self) -> None:
        self.loads = 0

    async def loadFor(
        self, authorizable: IAuthorizable,
    ) -> tuple[frozenset[str], frozenset[str]]:
        assert authorizable.getAuthorizableId() == 7
        self.loads += 1
        await asyncio.sleep(0)
        return frozenset({"posts.read", "posts.update"}), frozenset({"editor"})


async def main() -> None:
    try:
        bind_auth_context(AuthenticationContext())
    except AuthException:
        assert current_auth_context().isGuest
    else:
        raise AssertionError("Binding without a scope should fail")

    repository = Permissions()
    context = AuthenticationContext(
        identity=Identity(), guard="token", abilities=["posts.read"],
        repository=repository, credential_id=10,
    )
    async with ScopeManager():
        bind_auth_context(context)
        snapshots = await asyncio.gather(
            *(context.authorization() for _ in range(8)),
        )
        assert repository.loads == 1
        assert all(snapshot is snapshots[0] for snapshot in snapshots)
        assert snapshots[0].can("posts.read")
        assert not snapshots[0].can("posts.update")
        assert snapshots[0].hasRole("editor")
        assert context.identifier() == 7
        bind_auth_context(AuthenticationContext(guard="token"))
        assert context.identity is None and context.credentialId is None
        assert await context.authorization() is EMPTY_SNAPSHOT

    assert current_auth_context().isGuest
    assert AuthorizationSnapshot((), (), ()).abilities == frozenset()
    print("Context, snapshot and exception checks passed.")


asyncio.run(main())
```

### Policy evaluation with the real container

A synchronous ability is evaluated on a fresh container-built policy. Credential
restrictions deny before dispatch; an unrestricted missing handler raises
`PolicyNotFoundException`. Status: **executed successfully**.

```python
import asyncio
from dataclasses import dataclass
from orionis.auth import Authenticatable, AuthenticationContext, Policy
from orionis.auth.authorization.authorizer import Authorizer
from orionis.auth.exceptions import PolicyNotFoundException
from orionis.container.container import Container


class Identity(Authenticatable):
    __slots__ = ()
    id = 7


@dataclass
class Document:
    owner_id: int


class DocumentPolicy(Policy):
    __slots__ = ()

    def update(self, identity: object, resource: Document) -> bool:
        return resource.owner_id == identity.getAuthIdentifier()


async def main() -> None:
    app = Container()
    authorizer = Authorizer(app)
    authorizer.registerPolicy(Document, DocumentPolicy)
    context = AuthenticationContext(identity=Identity(), abilities=["update"])
    async with app.beginScope():
        assert await authorizer.allows(context, "update", Document(7))
        assert not await authorizer.allows(context, "update", Document(8))
        assert not await authorizer.allows(context, "delete", Document(7))
        unrestricted = AuthenticationContext(identity=Identity())
        try:
            await authorizer.allows(unrestricted, "delete", Document(7))
        except PolicyNotFoundException:
            pass
        else:
            raise AssertionError("A missing policy method should fail")
    assert authorizer.registry().policyFor(Document) is DocumentPolicy
    print("Policy and container checks passed.")


asyncio.run(main())
```

### Session login, persistent restoration and logout

This uses a real identity model, hasher, SQLite file, Session and cookie parser,
with a minimal HTTPS request double. It confirms rotation and old-cookie rejection
without connecting to a browser or server. Status: **executed successfully**.

```python
import asyncio
import os
import secrets
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace


original_directory = Path.cwd()
with TemporaryDirectory() as directory:
    try:
        os.chdir(directory)
        from orionis.auth import Authenticatable
        from orionis.auth.guards import SessionGuard
        from orionis.auth.identity import ModelIdentityProvider
        from orionis.auth.remember import apply_remember_cookie
        from orionis.database.connection_manager import ConnectionManager
        from orionis.hashing.hash_manager import HashManager
        from orionis.http.payload.estructures.cookies import Cookies
        from orionis.http.responses import Response
        from orionis.orm import BigInteger, Boolean, Model, String
        from orionis.orm.resolver import ConnectionResolver
        from orionis.session.session import Session

        class Account(Model, Authenticatable):
            __slots__ = ()
            table = "accounts"
            timestamps = False
            fillable = ["email", "password", "active"]
            hidden = ["password", "remember_token"]
            casts = {"active": "bool"}
            id = BigInteger().primary().autoIncrement()
            email = String(255).unique()
            password = String(255)
            active = Boolean()
            remember_token = String(100).nullable()

        class Settings:
            def config(self, key: str) -> object:
                return {
                    "database": {
                        "default": "sqlite",
                        "connections": {"sqlite": {
                            "driver": "sqlite", "database": "auth.sqlite",
                            "prefix": "",
                        }},
                    },
                    "hashing": {
                        "driver": "argon2",
                        "argon2": {"memory": 32, "threads": 1, "time": 1},
                    },
                    "auth.identity.model": f"{__name__}.Account",
                    "auth.remember": {
                        "cookie": "sample_remember", "lifetime": 30,
                        "secure": True,
                    },
                }.get(key)

        def incoming(cookies: object = None) -> SimpleNamespace:
            return SimpleNamespace(
                scheme="https", cookies={} if cookies is None else cookies,
                state=SimpleNamespace(session=Session()),
            )

        async def main() -> None:
            settings = Settings()
            manager = ConnectionManager(settings)
            ConnectionResolver.setManager(manager)
            try:
                await manager.connection().createTable(Account.__meta__.table)
                hashing = HashManager(settings)
                credential = secrets.token_urlsafe(24)
                account = await Account.create({
                    "email": "ada@example.test",
                    "password": await hashing.make(credential), "active": True,
                })
                provider = ModelIdentityProvider(settings, hashing)
                guard = SessionGuard(settings, provider)
                first = incoming()
                identity = await guard.attempt(
                    first, {"email": account.email, "password": credential},
                    remember=True,
                )
                assert identity is not None
                assert first.state.session.wantsRegenerate
                assert first.state.session.get("_auth_identifier") == str(account.id)
                response = Response()
                apply_remember_cookie(first, response)
                header = response.getHeader("set-cookie")[0]
                assert "Secure" in header and "HttpOnly" in header
                cookie = Cookies(header.split(";", 1)[0])
                second = incoming(cookie)
                restored = await guard.resolve(second)
                assert restored is not None and restored.identity.id == account.id
                assert await guard.resolve(incoming(cookie)) is None
                await guard.logout(second)
                assert second.state.session.invalidated
                assert (await Account.find(account.id)).remember_token is None
                print("Session, remember-cookie and logout checks passed.")
            finally:
                await manager.disconnect()
                ConnectionResolver.clear()

        asyncio.run(main())
    finally:
        os.chdir(original_directory)
```

### RBAC, restricted token, middleware and password reset

The script prepares its own seven auxiliary tables and identity model. It combines
session login through the auth manager, role permissions, restricted token
resolution, a permission
middleware, current-token revocation and one-use password reset. It asserts the
persisted change, old-session rejection and token revocation, and disconnects
before removing its SQLite file. Status: **executed successfully**.

```python
import asyncio
import os
import secrets
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace


original_directory = Path.cwd()
with TemporaryDirectory() as directory:
    try:
        os.chdir(directory)
        from orionis.auth import Authenticatable, Authorizable
        from orionis.auth.authorization.authorizer import Authorizer
        from orionis.auth.authorization.registrar import PermissionRegistrar
        from orionis.auth.authorization.repository import DatabasePermissionRepository
        from orionis.auth.exceptions import AuthorizationException
        from orionis.auth.guards import SessionGuard, TokenGuard
        from orionis.auth.identity import ModelIdentityProvider
        from orionis.auth.manager import AuthManager
        from orionis.auth.middleware import (
            RequirePermissionMiddleware, ResolveTokenIdentityMiddleware,
        )
        from orionis.auth.passwords.broker import PasswordBroker
        from orionis.auth.tokens import AccessTokenRepository
        from orionis.container.context.manager import ScopeManager
        from orionis.database.connection_manager import ConnectionManager
        from orionis.hashing.hash_manager import HashManager
        from orionis.http.request import Request
        from orionis.http.responses import Response
        from orionis.orm import BigInteger, Boolean, DateTime, Model, String, Text
        from orionis.orm.query_builder import QueryBuilder
        from orionis.orm.resolver import ConnectionResolver
        from orionis.orm.schema.column import ColumnDefinition
        from orionis.orm.schema.table import TableDefinition
        from orionis.session.session import Session

        class Account(Model, Authenticatable, Authorizable):
            __slots__ = ()
            table = "accounts"
            timestamps = False
            fillable = ["email", "password", "active"]
            casts = {"active": "bool"}
            id = BigInteger().primary().autoIncrement()
            email = String(255).unique()
            password = String(255)
            active = Boolean()
            remember_token = String(100).nullable()

        class Settings:
            def config(self, key: str) -> object:
                return {
                    "database": {
                        "default": "sqlite",
                        "connections": {"sqlite": {
                            "driver": "sqlite", "database": "workflow.sqlite",
                            "prefix": "",
                        }},
                    },
                    "hashing": {
                        "driver": "argon2",
                        "argon2": {"memory": 32, "threads": 1, "time": 1},
                    },
                    "auth.identity.model": f"{__name__}.Account",
                    "auth.passwords": {
                        "table": "password_reset_tokens",
                        "expiration": 15, "throttle": 60,
                    },
                }.get(key)

        class Readers(RequirePermissionMiddleware):
            __slots__ = ()
            permissions = ("posts.read",)

        def definition(
            name: str, columns: dict[str, ColumnDefinition],
            primary: tuple[str, ...],
        ) -> TableDefinition:
            for column_name, column in columns.items():
                column.name = column_name
            return TableDefinition(
                name=name, columns=columns,
                primary_key=primary[0] if len(primary) == 1 else None,
                composite_primary_key=primary if len(primary) > 1 else None,
            )

        async def main() -> None:
            settings = Settings()
            manager = ConnectionManager(settings)
            ConnectionResolver.setManager(manager)
            try:
                connection = manager.connection()
                await connection.createTable(Account.__meta__.table)
                for name in ("permissions", "roles"):
                    await connection.createTable(definition(name, {
                        "id": BigInteger().primary().autoIncrement(),
                        "name": String(255).unique(),
                    }, ("id",)))
                for name, foreign in (
                    ("model_has_permissions", "permission_id"),
                    ("model_has_roles", "role_id"),
                ):
                    await connection.createTable(definition(name, {
                        foreign: BigInteger(), "model_type": String(255),
                        "model_id": String(255),
                    }, (foreign, "model_id", "model_type")))
                await connection.createTable(definition("role_has_permissions", {
                    "permission_id": BigInteger(), "role_id": BigInteger(),
                }, ("permission_id", "role_id")))
                await connection.createTable(definition("personal_access_tokens", {
                    "id": BigInteger().primary().autoIncrement(),
                    "tokenable_type": String(255), "tokenable_id": String(255),
                    "name": String(255), "token": String(64).unique(),
                    "abilities": Text().nullable(),
                    "expires_at": DateTime().nullable(),
                    "last_used_at": DateTime().nullable(),
                    "revoked_at": DateTime().nullable(),
                    "created_at": DateTime().nullable(),
                    "updated_at": DateTime().nullable(),
                }, ("id",)))
                await connection.createTable(definition("password_reset_tokens", {
                    "email": String(255).primary(), "token": String(64).nullable(),
                    "user_id": String(255), "password_fingerprint": String(64),
                    "created_at": BigInteger(),
                }, ("email",)))
                db = QueryBuilder(manager)
                hashing = HashManager(settings)
                credential = secrets.token_urlsafe(24)
                account = await Account.create({
                    "email": "ada@example.test",
                    "password": await hashing.make(credential), "active": True,
                })
                identities = ModelIdentityProvider(settings, hashing)
                repository = DatabasePermissionRepository(db)
                registrar = PermissionRegistrar(db)
                tokens = AccessTokenRepository(settings, db)
                authorizer = Authorizer(settings)
                session_guard = SessionGuard(settings, identities)
                auth = AuthManager(
                    settings, authorizer, repository, session_guard,
                    TokenGuard(tokens, identities), tokens,
                )
                await registrar.grantToRole("editor", "posts.read", "posts.update")
                await registrar.assignRole(account, "editor")
                web = SimpleNamespace(state=SimpleNamespace(session=Session()))
                async with ScopeManager() as scope:
                    scope[Request] = web
                    await auth.login(account)
                    assert await auth.hasRole("editor")
                    assert await auth.canAll(["posts.read", "posts.update"])
                    issued = await auth.createToken("reader", abilities=["posts.read"])
                request = SimpleNamespace(bearerToken=issued.plain_text)

                async def endpoint() -> Response:
                    return Response("accepted")

                async def secured() -> Response:
                    return await Readers(authorizer).handle(request, endpoint)

                async with ScopeManager():
                    response = await ResolveTokenIdentityMiddleware(
                        auth, repository,
                    ).handle(request, secured)
                    assert response.getBody() == b"accepted"
                    assert not await auth.can("posts.update")
                    try:
                        await auth.createToken("not-allowed")
                    except AuthorizationException:
                        pass
                    else:
                        raise AssertionError("Token sessions cannot issue tokens")
                    assert await auth.revokeCurrentToken()
                    assert auth.guest()
                assert await tokens.findByPlainText(issued.plain_text) is None
                other = await tokens.create(account, "before-reset")
                broker = PasswordBroker(settings, db, hashing)
                issued_reset = await broker.issue(" ADA@example.test ")
                assert issued_reset is not None
                _, reset_token = issued_reset
                assert await broker.valid(account.email, reset_token)
                replacement = secrets.token_urlsafe(24)
                returned = await broker.reset(account.email, reset_token, replacement)
                assert returned is not None
                updated = await Account.find(account.id)
                assert await hashing.check(replacement, updated.getAuthPassword())
                assert returned.getAuthPassword() != updated.getAuthPassword()
                assert await session_guard.resolve(web) is None
                assert await tokens.findByPlainText(other.plain_text) is None
                assert not await broker.valid(account.email, reset_token)
                assert await broker.issue(account.email) is None
                print("RBAC, token, middleware and reset checks passed.")
            finally:
                await manager.disconnect()
                ConnectionResolver.clear()

        asyncio.run(main())
    finally:
        os.chdir(original_directory)
```

## Design characteristics

| Observed mechanism | Concrete consequence and evidence |
|---|---|
| Lazy package exports and model import | Root attribute access loads/caches only its declared target; identity model lookup is deferred except in the broker constructor. See [initializer](../__init__.py), [identity provider](../identity/provider.py), [broker](../passwords/broker.py). |
| Plain virtual identity mixins | ORM models obtain authentication behavior without inheriting the contracts' ABC metaclass. See [Authenticatable](../concerns/authenticatable.py), [Authorizable](../concerns/authorizable.py). |
| Scope ownership and context replacement | Retained built-in bound contexts cannot expose an authenticated identity after their scope/binding ceases to be current. See [context](../context/context.py). |
| Read-only frozenset properties | Public snapshot consumers cannot assign properties or mutate the exposed sets; identity references themselves are not copied. See [snapshot](../authorization/snapshot.py). |
| Frozen keyword-only token dataclasses | Constructors/field behavior are decorator-generated; NewAccessToken redaction is specific to its representation and toDict method. See [entities](../entities/__init__.py). |
| Slotted core services and empty-slot contracts | Guards, contexts, snapshots, identity/token/RBAC services, manager and middleware restrict their declared instance state. RememberMe, PasswordBroker and MustVerifyEmail do not declare slots. See their linked declarations. |
| Separate credential types | PAT lookup uses opaque-secret digests; remember grants bind cookie and password; reset records bind recipient, account ID and password fingerprint. These are not JWT payloads. See [tokens](../tokens/repository.py), [remember](../remember.py), [broker](../passwords/broker.py). |

## Performance and concurrency

- [AuthenticationContext](../context/context.py) eagerly materializes abilities but
  lazily loads permissions. A successful snapshot is retained for that context;
  later RBAC writes do not refresh it. The context lock covers cooperating tasks
  sharing that context, with ownership rechecks after awaited loads.
- [authentication_lock](../context/functions.py) is one lock per active scope.
  Manager session transitions, resolver middleware and current-token revocation
  use it. Direct guard/repository calls and explicit context bindings do not
  independently acquire it.
- [DatabasePermissionRepository](../authorization/repository.py) builds one UNION
  statement and materializes results into sets. [PermissionRegistrar](../authorization/registrar.py)
  handles unique/composite-key competition through transactions/savepoints and
  row verification, not a global Python lock. Multi-operation atomicity is not
  implicit.
- [TokenGuard](../guards/token_guard.py) performs token lookup, identity lookup and
  conditional usage update for a usable credential. It avoids a password hash.
  [AccessTokenRepository](../tokens/repository.py) may add a creation ID lookup,
  materializes abilities before bounding their count, and uses two purge deletes.
- [RememberMe](../remember.py) rotates through a conditional token/password update;
  it retains one grant per identity, not a list of devices. Concurrent rotation
  losers do not clear a winner's replacement cookie. [PasswordBroker](../passwords/broker.py)
  hashes before its reset transaction; conditional token consumption and password
  matching determine whether the operation can commit.
- [PolicyRegistry](../authorization/registry.py) retains class/MRO lookup results,
  including misses, without a size limit; every registration clears them.
  [Authorizer](../authorization/authorizer.py) builds policy instances per evaluation,
  and user callbacks may perform their own blocking work or I/O.
- Async declarations are not proof that all work is nonblocking. Secret generation,
  digesting, set/JSON materialization and class import run synchronously; the
  inspected hashing backend moves costly password work to a worker thread.

> ⚠️ Not specified in the source code: a module-wide guarantee for mutation/registration across threads or reuse of live locks and services across event loops. The documented scope locks and conditional database writes do not establish that broader guarantee.

## Compatibility notes

The [project manifest](../../../pyproject.toml) declares Python `>=3.14`; the
[lockfile](../../../uv.lock) carries the same constraint. Validation used CPython
3.14.6 on Windows. Native union/built-in generic annotations are present; many
types are imported under `TYPE_CHECKING`, relying on deferred annotation behavior.
These observations do not declare support below the project minimum or certify
every newer Python release.

| Dependency | Declared project constraint | Lockfile and validation environment |
|---|---|---|
| `sqlalchemy[asyncio]` | `>=2.0.54,<3.0` | `2.1.1` |
| `aiosqlite` | `>=0.22.1` | `0.22.1` |
| `msgspec` | `>=0.21.1` | `0.22.0` |
| `pwdlib[argon2,bcrypt]` | `>=0.3.1` | `0.3.1` |
| `argon2-cffi` | Transitive hashing backend, not a direct constraint | `25.1.0` |
| `bcrypt` | Transitive hashing backend, not a direct constraint | `5.0.0` |
| `python-dotenv` | `>=1.2.3,<2.0` | `1.2.4` |
| `pendulum` | `>=3.2.0,<4.0` | `3.2.0` |

Locked/installed versions are not minimum supported versions. SQLite and asyncpg
are base dependencies; the manifest declares optional database extras for other
drivers. Auth itself imports no optional driver. SQL behavior/transaction
isolation still depends on the selected connection.

Old sessions lacking the password fingerprint are rejected by
[SessionGuard.resolve](../guards/session_guard.py). Persisted owner IDs are
canonical text, with native restoration performed by the identity provider.
Private ORM metadata is consulted by the implementation; an arbitrary
IAuthenticatable class does not by itself supply the ORM operations it needs.
Container-built constructors use runtime dependency imports, not postponed
string annotations; reference fragments must not be turned into alternative
signatures by evaluating missing annotation imports.

## Verification and limitations

Verification performed for this documentation:

| Check | Result |
|---|---|
| Module identity and boundaries | Package discovery starts at the project root; verified `orionis/auth` maps to `orionis.auth`, and its direct docs directory is not a reparse point. |
| Source inventory | All 53 Python files inspected; 280 public entries documented, including contracts, fields, helpers, constants and two explicit repr methods. |
| Literal API fidelity | Declaration tokens compared against AST-derived source signatures, including decorators, annotations and defaults, without evaluating them. |
| Examples | Four independent scripts: syntax passed, local imports passed, execution and assertions passed. The code is identical in both languages. |
| Existing tests | 359 discovered, 359 reported PASSED, no failures/skips, through Application.boot and the native TestingEngine in a temporary copy of the test/resources tree. Auth source imports resolved to this checkout. |
| Documentation | Heading order, code-block equivalence, inline technical literals, local links, TOC anchors and absence of unresolved template variables checked. |
| Skill | Two-field YAML frontmatter and module-derived identity checked; local documentation references verified. |
| Write scope | Initial/final file hashes include ignored/untracked files; only the three authorized documents changed. Previous module documentation and the Git index were preserved. |

The inventory excludes imported dependencies as standalone Auth APIs, private
normalizers/SQL builders, `_StalePassword`, package export-dispatch helpers as
callable consumer APIs, and framework-private context fork/binding methods.
Their relevant effects are explained above. Dataclass-generated methods are
identified by their decorator rather than invented literal signatures. Every
identified public entry is represented; exclusions are not missing public APIs.

**Editor limitation:** VS Code's skill diagnostics expect a skill name matching
the containing folder (`docs`) and report several links with fragments as literal
file paths. The requested local entry point deliberately keeps `orionis-auth` in
[SKILL.md](SKILL.md); it is not an installed skill package. Its YAML subset,
target files and Markdown anchors passed the independent checks above. These
editor diagnostics remain; no configuration or registration was changed.

**Implemented behavior versus prior descriptions:** ordinary session/token
resolution does not enforce the credential-login `active is True` test; policies
check handler existence after the before hook; broker reset returns an unrefreshed
identity. The source docstring's unconditional console-guest wording is narrower
than the helper's actual active-scope behavior. These distinctions were preserved,
not corrected in source.

> ⚠️ Not executed in this environment: live PostgreSQL, MySQL, Oracle, SQL Server, external cache services, email transport, browser/server end-to-end workflows, independent OS workers and cross-thread/event-loop certification. This run used isolated SQLite files and native/component tests without external credentials or services.

> ⚠️ Not verifiable with the available files: production deployment guarantees for the application's chosen isolation level, filesystem, reverse proxy, HTTPS policy or custom identity/policy implementations. No deployment configuration or service execution was supplied as evidence.

No benchmark or runtime coverage percentage was measured. This manual documents
Auth and its necessary integrations, not the APIs of unrelated framework modules.
