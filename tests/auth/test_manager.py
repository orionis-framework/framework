import asyncio
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from orionis.http.default.controllers.login_controller import LoginController
from orionis.auth.authorization.authorizer import Authorizer
from orionis.auth.authorization.policy import Policy
from orionis.auth.authorization.registrar import PermissionRegistrar
from orionis.auth.authorization.repository import DatabasePermissionRepository
from orionis.auth.concerns.authenticatable import Authenticatable
from orionis.auth.concerns.authorizable import Authorizable
from orionis.auth.context.context import AuthenticationContext
from orionis.auth.context.functions import (
    authentication_lock,
    bind_auth_context,
    current_auth_context,
)
from orionis.auth.contracts.manager import IAuthManager  # noqa: TC001
from orionis.auth.exceptions import (
    AuthException,
    AuthenticationException,
    AuthorizationException,
    GuardNotFoundException,
)
from orionis.auth.guards.session_guard import SessionGuard
from orionis.auth.guards.token_guard import TokenGuard
from orionis.auth.identity.provider import ModelIdentityProvider
from orionis.auth.manager import AuthManager
from orionis.auth.middleware.resolve_identity import (
    ResolveIdentityMiddleware,
    ResolveSessionIdentityMiddleware,
)
from orionis.auth.tokens.repository import AccessTokenRepository
from orionis.container.context.manager import ScopeManager
from orionis.container.context.scope import ScopedContext
from orionis.database.connection_manager import ConnectionManager
from orionis.hashing.hash_manager import HashManager
from orionis.http.request import Request
from orionis.orm import BigInteger, Boolean, Model, String, Uuid
from orionis.orm.query_builder import QueryBuilder
from orionis.orm.resolver import ConnectionResolver
from orionis.orm.schema.constraints import UniqueConstraint
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import DateTime, Text
from orionis.session.session import Session
from orionis.test import TestCase

class Account(Model, Authenticatable, Authorizable):
    """Identity model used by the manager tests."""

    table = "accounts"
    timestamps = False

    id = BigInteger().primary().autoIncrement()
    email = String(255)
    password = String(255)
    active = Boolean().nullable()

class Member(Model, Authenticatable, Authorizable):
    """Identity model with a native UUID key and a non-default password column."""

    __slots__ = ()
    table = "members"
    timestamps = False
    uuids = True
    AUTH_PASSWORD = "credential_hash"  # noqa: S105

    id = Uuid().primary()
    email = String(255)
    credential_hash = String(255)
    active = Boolean().nullable()

class _LoginRequest:
    """Provide request state and a cached form payload to the example controller."""

    __slots__ = ("payload", "state")

    def __init__(self, payload: dict[str, str]) -> None:
        """Store the payload and an existing session instance."""
        self.payload = payload
        self.state = SimpleNamespace(session=Session())

    async def data(self) -> dict[str, str]:
        """Return the already parsed login input."""
        return self.payload

class _StubApp:
    """Application stub exposing every configuration this suite needs."""

    __slots__ = ("_tree",)

    def __init__(self, database: str) -> None:
        """Build the configuration tree answered by ``config()``."""
        self._tree: dict[str, Any] = {
            "database": {
                "default": "sqlite",
                "connections": {
                    "sqlite": {
                        "driver": "sqlite",
                        "database": database,
                        "prefix": "",
                    },
                },
            },
            "hashing": {
                "driver": "argon2",
                "argon2": {"memory": 32, "threads": 1, "time": 1},
            },
            "auth": {
                "default": "session",
                "identity": {
                    "model": f"{__name__}.Account",
                    "username": "email",
                    "password": "password",
                },
                "session": {"key": "_auth_identifier", "redirect_to": None},
                "tokens": {"table": "personal_access_tokens"},
            },
        }

    def config(self, key: str | None = None) -> Any:  # noqa: ANN401
        """Resolve a dot-notated configuration key."""
        if key is None:
            return self._tree
        node: Any = self._tree
        for part in key.split("."):
            if not isinstance(node, dict):
                return None
            node = node.get(part)
            if node is None:
                return None
        return node

    async def build(self, target: type) -> object:
        """Instantiate a policy class without a real container."""
        return target()

class _TokenIdentityMiddleware(ResolveIdentityMiddleware):
    """Identity middleware pinned to the personal access token guard."""

    __slots__ = ()

    guard = "token"

class _AccountPolicy(Policy):
    """Policy allowing an identity to act only on its own account."""

    __slots__ = ()

    async def update(self, identity: object, account: Account) -> bool:
        """Allow the update only for the owner of the account."""
        return account.id == identity.getAuthIdentifier()

class _UnauthorizableIdentity(Authenticatable):
    """Identity that can log in but can never own permissions."""

    __slots__ = ("id",)

    def __init__(self) -> None:
        """Store the identifier a guard would read from the session."""
        self.id = 99

def build_table(
    name: str,
    columns: dict[str, Any],
    **kwargs: object,
) -> TableDefinition:
    """Name every column and wrap them into a table definition."""
    for column_name, column in columns.items():
        column.name = column_name
    return TableDefinition(name=name, columns=columns, **kwargs)

class _ManagerCase(TestCase):
    """Base case wiring the whole authentication stack over SQLite."""

    async def asyncSetUp(self) -> None:
        """Create the schema, seed identities and build the manager."""
        self._tmp = tempfile.TemporaryDirectory()
        database = str(Path(self._tmp.name) / "auth.sqlite")

        self.app = _StubApp(database)
        self.manager_db = ConnectionManager(self.app)
        self._previous_manager = ConnectionResolver._manager
        ConnectionResolver.setManager(self.manager_db)
        self.connection = self.manager_db.connection("sqlite")

        await self.connection.createTable(build_table(
            "accounts",
            {
                "id": BigInteger().primary().autoIncrement(),
                "email": String(255),
                "password": String(255),
                "active": Boolean().nullable(),
            },
            primary_key="id",
        ))
        for name in ("permissions", "roles"):
            await self.connection.createTable(build_table(
                name,
                {
                    "id": BigInteger().primary().autoIncrement(),
                    "name": String(255),
                },
                primary_key="id",
                unique_constraints=(
                    UniqueConstraint(columns=("name",)),
                ),
            ))
        for name, owner in (
            ("model_has_permissions", "permission_id"),
            ("model_has_roles", "role_id"),
        ):
            await self.connection.createTable(build_table(
                name,
                {
                    owner: BigInteger(),
                    "model_type": String(255),
                    "model_id": String(255),
                },
                composite_primary_key=(owner, "model_id", "model_type"),
            ))
        await self.connection.createTable(build_table(
            "role_has_permissions",
            {"permission_id": BigInteger(), "role_id": BigInteger()},
            composite_primary_key=("permission_id", "role_id"),
        ))
        await self.connection.createTable(build_table(
            "personal_access_tokens",
            {
                "id": BigInteger().primary().autoIncrement(),
                "tokenable_type": String(255),
                "tokenable_id": String(255),
                "name": String(255),
                "token": String(64).unique(),
                "abilities": Text().nullable(),
                "last_used_at": DateTime().nullable(),
                "expires_at": DateTime().nullable(),
                "revoked_at": DateTime().nullable(),
                "created_at": DateTime().nullable(),
                "updated_at": DateTime().nullable(),
            },
            primary_key="id",
        ))

        self.db = QueryBuilder(self.manager_db)
        self.hasher = HashManager(self.app)
        self.identities = ModelIdentityProvider(self.app, self.hasher)
        self.permissions = DatabasePermissionRepository(self.db)
        self.registrar = PermissionRegistrar(self.db)
        self.tokens = AccessTokenRepository(self.app, self.db)
        self.authorizer = Authorizer(self.app)
        self.auth: IAuthManager = AuthManager(
            self.app,
            self.authorizer,
            self.permissions,
            SessionGuard(self.app, self.identities),
            TokenGuard(self.tokens, self.identities),
            self.tokens,
        )

        self.ada = await Account.create({
            "email": "ada@orionis.dev",
            "password": await self.hasher.make("secret"),
            "active": True,
        })
        self.bob = await Account.create({
            "email": "bob@orionis.dev",
            "password": await self.hasher.make("secret"),
            "active": True,
        })

    async def asyncTearDown(self) -> None:
        """Release the connection and drop the temporary database."""
        ConnectionResolver.setManager(self._previous_manager)
        await self.connection.disconnect()
        self._tmp.cleanup()

    def webRequest(self, session: Session | None = None) -> SimpleNamespace:
        """Build a web request double carrying a session."""
        state = SimpleNamespace()
        state.session = session if session is not None else Session()
        return SimpleNamespace(
            state=state,
            bearerToken=None,
            wantsJson=lambda: False,
            isAjax=lambda: False,
        )

    def apiRequest(self, token: str | None) -> SimpleNamespace:
        """Build an API request double carrying a bearer token."""
        return SimpleNamespace(
            state=SimpleNamespace(),
            bearerToken=token,
            wantsJson=lambda: True,
            isAjax=lambda: False,
        )

class TestAuthManagerSessionFlow(_ManagerCase):
    """Validate the web authentication lifecycle through the manager."""

    def testOutsideARequestEverythingIsAGuest(self) -> None:
        """Query the manager without any request in flight.

        Validates that console commands and background jobs never observe
        an authenticated identity.
        """
        self.assertTrue(self.auth.guest())
        self.assertFalse(self.auth.check())
        self.assertIsNone(self.auth.user())
        self.assertIsNone(self.auth.identifier())

    async def testAttemptAuthenticatesAndBindsTheContext(self) -> None:
        """Validates the full login path.

        The session is written and the context becomes visible at once.
        """
        request = self.webRequest()
        async with ScopeManager() as scope:
            scope[Request] = request

            granted = await self.auth.attempt({
                "email": "ada@orionis.dev", "password": "secret",
            })

            self.assertTrue(granted)
            self.assertTrue(self.auth.check())
            self.assertEqual(self.auth.identifier(), self.ada.id)
            self.assertEqual(
                request.state.session.get("_auth_identifier"), str(self.ada.id),
            )

    async def testAttemptRejectsWrongCredentials(self) -> None:
        """Validates that a failed login changes nothing.

        The request must stay anonymous.
        """
        async with ScopeManager() as scope:
            scope[Request] = self.webRequest()

            granted = await self.auth.attempt({
                "email": "ada@orionis.dev", "password": "wrong",
            })

            self.assertFalse(granted)
            self.assertTrue(self.auth.guest())

    async def testAttemptRejectsAnUnknownIdentity(self) -> None:
        """Validates that a missing account behaves like a wrong secret.

        The two failures must be indistinguishable.
        """
        async with ScopeManager() as scope:
            scope[Request] = self.webRequest()

            granted = await self.auth.attempt({
                "email": "ghost@orionis.dev", "password": "secret",
            })

            self.assertFalse(granted)
            self.assertTrue(self.auth.guest())

    async def testLoginSkipsCredentialVerification(self) -> None:
        """Validates the programmatic login used right after signup.

        No password is involved in this path.
        """
        async with ScopeManager() as scope:
            scope[Request] = self.webRequest()

            await self.auth.login(self.ada)

            self.assertTrue(self.auth.check())
            self.assertIs(self.auth.user(), self.ada)

    async def testLogoutClearsTheContextAndTheSession(self) -> None:
        """Validates that logging out leaves nothing behind.

        The session is destroyed and the context becomes a guest.
        """
        request = self.webRequest()
        async with ScopeManager() as scope:
            scope[Request] = request
            await self.auth.login(self.ada)

            await self.auth.logout()

            self.assertTrue(self.auth.guest())
            self.assertTrue(request.state.session.invalidated)

    async def testSessionOperationsRequireARequest(self) -> None:
        """Attempt a credential login with no request in the scope.

        Validates the guard against using the manager out of band: there
        would be no session to write the identity into.
        """
        with self.assertRaises(AuthException):
            await self.auth.attempt({"email": "ada@orionis.dev"})

    def testGuardsAreResolvedByName(self) -> None:
        """Resolve the registered guards through the manager registry.

        Validates that the default comes from the configuration and that
        an unknown name fails loudly instead of falling back.
        """
        self.assertEqual(self.auth.guard().name, "session")
        self.assertEqual(self.auth.guard("token").name, "token")
        with self.assertRaises(GuardNotFoundException):
            self.auth.guard("ldap")

    async def testExampleLoginControllerActuallyAuthenticates(self) -> None:
        """Submit wrong and valid credentials through the shipped controller.

        Validates that the manager drives a real login end to end and
        that each outcome redirects to its own page.
        """
        controller = LoginController(self.app)
        for credential, expected in (("wrong", False), ("secret", True)):
            payload = {"email": self.ada.email, "password": credential}
            request = _LoginRequest(payload)
            async with ScopeManager() as scope:
                scope[Request] = request
                response = await controller.login(
                    request, SimpleNamespace(**payload), self.auth,
                )
                self.assertEqual(self.auth.check(), expected)
                location = dict(response.getStringHeaders()).get("location")
                self.assertEqual(location, "/home" if expected else "/login")

    async def testUuidModelWorksAcrossSessionTokensAndPermissions(self) -> None:
        """Drive a UUID identity through sessions, tokens and permissions.

        Validates that a model with a native UUID key and a renamed hash
        column is supported by every source the manager relies on.
        """
        await self.connection.createTable(Member.__meta__.table)
        member = await Member.create({
            "email": "member@orionis.dev",
            "credential_hash": await self.hasher.make("secret"),
            "active": True,
        })
        self.app._tree["auth"]["identity"] = {
            "model": f"{__name__}.Member", "username": "email",
        }
        provider = ModelIdentityProvider(self.app, self.hasher)
        session_guard = SessionGuard(self.app, provider)
        request = self.webRequest()
        resolved = await session_guard.attempt(
            request, {"email": member.email, "password": "secret"},
        )
        self.assertEqual(resolved.id, member.id)
        self.assertEqual(request.state.session.get("_auth_identifier"), str(member.id))
        restored = await session_guard.resolve(request)
        self.assertEqual(restored.identity.id, member.id)
        await self.registrar.givePermissionTo(member, "users.view")
        self.assertIn("users.view", (await self.permissions.loadFor(member))[0])
        issued = await self.tokens.create(member, "uuid-token")
        token_guard = TokenGuard(self.tokens, provider)
        result = await token_guard.resolve(self.apiRequest(issued.plain_text))
        self.assertEqual(result.identity.id, member.id)

class TestAuthManagerAuthorization(_ManagerCase):
    """Validate permission, role and policy checks through the manager."""

    async def testGuestsAreAlwaysDenied(self) -> None:
        """Validates the default answer for anonymous requests.

        Authorization is deny by default.
        """
        self.assertFalse(await self.auth.can("users.view"))
        self.assertTrue(await self.auth.cannot("users.view"))
        self.assertFalse(await self.auth.hasRole("admin"))
        with self.assertRaises(AuthenticationException):
            await self.auth.authorize("users.view")

    async def testGrantsADirectPermission(self) -> None:
        """Validates the end-to-end direct permission flow.

        The permission is stored, resolved and answered.
        """
        await self.registrar.givePermissionTo(self.ada, "users.view")

        async with ScopeManager() as scope:
            scope[Request] = self.webRequest()
            await self.auth.login(self.ada)

            self.assertTrue(await self.auth.can("users.view"))
            self.assertFalse(await self.auth.can("users.delete"))
            await self.auth.authorize("users.view")

    async def testGrantsPermissionsInheritedFromRoles(self) -> None:
        """Validates the end-to-end role flow.

        Roles hand their permissions to every holder.
        """
        await self.registrar.grantToRole("admin", "users.view", "users.delete")
        await self.registrar.assignRole(self.ada, "admin")

        async with ScopeManager() as scope:
            scope[Request] = self.webRequest()
            await self.auth.login(self.ada)

            self.assertTrue(await self.auth.hasRole("admin"))
            self.assertTrue(
                await self.auth.canAll(["users.view", "users.delete"]),
            )

    async def testRaisesForbiddenForAnAuthorizedIdentityWithoutRights(
        self,
    ) -> None:
        """Validates the distinction between 401 and 403.

        An authenticated identity without rights is forbidden, not
        unauthenticated.
        """
        async with ScopeManager() as scope:
            scope[Request] = self.webRequest()
            await self.auth.login(self.ada)

            with self.assertRaises(AuthorizationException):
                await self.auth.authorize("users.delete")

    async def testAuthorizationNeverLeaksBetweenIdentities(self) -> None:
        """Validates that permissions follow the identity.

        Two identities of the same model stay independent.
        """
        await self.registrar.givePermissionTo(self.ada, "users.view")

        async with ScopeManager() as scope:
            scope[Request] = self.webRequest()
            await self.auth.login(self.bob)
            self.assertFalse(await self.auth.can("users.view"))

    async def testEvaluatesPoliciesAgainstAResource(self) -> None:
        """Validates the resource aware authorization path.

        Ownership rules live in the policy, not in a permission.
        """
        self.auth.registerPolicy(Account, _AccountPolicy)

        async with ScopeManager() as scope:
            scope[Request] = self.webRequest()
            await self.auth.login(self.ada)

            self.assertTrue(await self.auth.allows("update", self.ada))
            self.assertTrue(await self.auth.denies("update", self.bob))
            await self.auth.authorizeResource("update", self.ada)
            with self.assertRaises(AuthorizationException):
                await self.auth.authorizeResource("update", self.bob)

    async def testPolicyChecksRequireAnIdentity(self) -> None:
        """Validates that guests never reach a policy.

        Policies always receive a real identity.
        """
        self.auth.registerPolicy(Account, _AccountPolicy)
        with self.assertRaises(AuthenticationException):
            await self.auth.authorizeResource("update", self.ada)

class TestAuthManagerTokens(_ManagerCase):
    """Validate the personal access token flow through the manager."""

    async def testIssuesATokenForTheAuthenticatedIdentity(self) -> None:
        """Validates the common case of minting a token.

        The owner defaults to the identity of the current request.
        """
        async with ScopeManager() as scope:
            scope[Request] = self.webRequest()
            await self.auth.login(self.ada)

            issued = await self.auth.createToken("ci")

        self.assertEqual(issued.access_token.tokenable_id, str(self.ada.id))
        self.assertTrue(issued.plain_text)

    async def testIssuingATokenRequiresAnIdentity(self) -> None:
        """Validates that a guest cannot mint a credential.

        There would be nobody to attach it to.
        """
        with self.assertRaises(AuthenticationException):
            await self.auth.createToken("ci")

    async def testAuthenticatesAnApiRequestWithATokenGuard(self) -> None:
        """Validates the API authentication path end-to-end.

        The bearer token resolves to the owning identity.
        """
        issued = await self.auth.createToken("ci", tokenable=self.ada)
        middleware = _TokenIdentityMiddleware(self.auth, self.permissions)

        async def call_next() -> str:
            return "handled"

        async with ScopeManager() as scope:
            request = self.apiRequest(issued.plain_text)
            scope[Request] = request

            await middleware.handle(request, call_next)

            self.assertTrue(self.auth.check())
            self.assertEqual(self.auth.identifier(), self.ada.id)

    async def testTokenAbilitiesNarrowTheAuthorization(self) -> None:
        """Validates the intersection rule on a real request.

        The identity owns two permissions but the token allows only one.
        """
        await self.registrar.givePermissionTo(
            self.ada, "users.view", "users.delete",
        )
        issued = await self.auth.createToken(
            "reader", tokenable=self.ada, abilities=["users.view"],
        )
        middleware = _TokenIdentityMiddleware(self.auth, self.permissions)

        async def call_next() -> str:
            return "handled"

        async with ScopeManager() as scope:
            request = self.apiRequest(issued.plain_text)
            scope[Request] = request
            await middleware.handle(request, call_next)

            self.assertTrue(await self.auth.can("users.view"))
            self.assertFalse(await self.auth.can("users.delete"))

    async def testATokenNeverElevatesTheIdentityPermissions(self) -> None:
        """Validates the security invariant of abilities.

        An ability the identity does not own stays denied.
        """
        await self.registrar.givePermissionTo(self.ada, "users.view")
        issued = await self.auth.createToken(
            "greedy",
            tokenable=self.ada,
            abilities=["users.view", "users.delete"],
        )
        middleware = _TokenIdentityMiddleware(self.auth, self.permissions)

        async def call_next() -> str:
            return "handled"

        async with ScopeManager() as scope:
            request = self.apiRequest(issued.plain_text)
            scope[Request] = request
            await middleware.handle(request, call_next)

            self.assertTrue(await self.auth.can("users.view"))
            self.assertFalse(await self.auth.can("users.delete"))

    async def testRevokesTheTokenOfTheCurrentRequest(self) -> None:
        """Validates the sign out path of an API client.

        The credential used right now is the one revoked.
        """
        issued = await self.auth.createToken("ci", tokenable=self.ada)
        middleware = _TokenIdentityMiddleware(self.auth, self.permissions)

        async def call_next() -> str:
            return "handled"

        async with ScopeManager() as scope:
            request = self.apiRequest(issued.plain_text)
            scope[Request] = request
            await middleware.handle(request, call_next)

            self.assertTrue(await self.auth.revokeCurrentToken())
            self.assertTrue(self.auth.guest())

            await middleware.handle(request, call_next)
            self.assertTrue(self.auth.guest())

        self.assertIsNone(
            await self.tokens.findByPlainText(issued.plain_text),
        )

    async def testSessionRequestsHaveNoTokenToRevoke(self) -> None:
        """Validates the answer for a session authenticated request.

        Session authentication carries no revocable credential.
        """
        async with ScopeManager() as scope:
            scope[Request] = self.webRequest()
            await self.auth.login(self.ada)

            self.assertFalse(await self.auth.revokeCurrentToken())

    async def testAnExpiredTokenNeverAuthenticates(self) -> None:
        """Validates the expiration path on a real request.

        The middleware leaves the request anonymous.
        """
        issued = await self.auth.createToken(
            "stale",
            tokenable=self.ada,
            expires_at=datetime.now(UTC).replace(tzinfo=None)
            - timedelta(minutes=1),
        )
        middleware = _TokenIdentityMiddleware(self.auth, self.permissions)

        async def call_next() -> str:
            return "handled"

        async with ScopeManager() as scope:
            request = self.apiRequest(issued.plain_text)
            scope[Request] = request
            await middleware.handle(request, call_next)

            self.assertTrue(self.auth.guest())

class TestAuthManagerConcurrency(_ManagerCase):
    """Validate that concurrent requests never observe each other."""

    async def testConcurrentLoginsKeepTheirOwnIdentity(self) -> None:
        """Validates request isolation across suspension points.

        Two logins running at the same time must never cross, which is
        exactly what a singleton holding the current user would break.
        """
        observed: dict[str, list[object]] = {}

        async def handle(name: str, email: str) -> None:
            async with ScopeManager() as scope:
                scope[Request] = self.webRequest()
                await self.auth.attempt({"email": email, "password": "secret"})
                seen: list[object] = []
                for _ in range(6):
                    await asyncio.sleep(0)
                    seen.append(self.auth.identifier())
                observed[name] = seen

        await asyncio.gather(
            handle("ada", "ada@orionis.dev"),
            handle("bob", "bob@orionis.dev"),
        )

        self.assertEqual(observed["ada"], [self.ada.id] * 6)
        self.assertEqual(observed["bob"], [self.bob.id] * 6)

    async def testConcurrentAuthorizationChecksStayIsolated(self) -> None:
        """Validates that authorization follows the right identity.

        A shared snapshot would leak permissions across requests.
        """
        await self.registrar.givePermissionTo(self.ada, "users.delete")
        observed: dict[str, list[bool]] = {}

        async def handle(name: str, account: Account) -> None:
            async with ScopeManager() as scope:
                scope[Request] = self.webRequest()
                await self.auth.login(account)
                seen: list[bool] = []
                for _ in range(4):
                    await asyncio.sleep(0)
                    seen.append(await self.auth.can("users.delete"))
                observed[name] = seen

        await asyncio.gather(
            handle("ada", self.ada), handle("bob", self.bob),
        )

        self.assertEqual(observed["ada"], [True] * 4)
        self.assertEqual(observed["bob"], [False] * 4)

    async def testAGuestRequestIsNotContaminatedByAnAuthenticatedOne(
        self,
    ) -> None:
        """Validates that an anonymous request stays anonymous.

        The guest context is shared, so it must never be mutated.
        """
        observed: dict[str, list[bool]] = {}

        async def authenticated() -> None:
            async with ScopeManager() as scope:
                scope[Request] = self.webRequest()
                await self.auth.login(self.ada)
                for _ in range(4):
                    await asyncio.sleep(0)
                observed["auth"] = [self.auth.check()]

        async def anonymous() -> None:
            async with ScopeManager() as scope:
                scope[Request] = self.webRequest()
                seen: list[bool] = []
                for _ in range(4):
                    await asyncio.sleep(0)
                    seen.append(self.auth.check())
                observed["guest"] = seen

        await asyncio.gather(authenticated(), anonymous())

        self.assertEqual(observed["auth"], [True])
        self.assertEqual(observed["guest"], [False] * 4)

    async def testConcurrentApiRequestsNeverShareTheirToken(self) -> None:
        """Validates isolation of token authenticated requests.

        Each request must resolve its own credential and abilities.
        """
        await self.registrar.givePermissionTo(self.ada, "users.view")
        await self.registrar.givePermissionTo(self.bob, "users.view")
        ada_token = await self.auth.createToken(
            "ada", tokenable=self.ada, abilities=["users.view"],
        )
        bob_token = await self.auth.createToken(
            "bob", tokenable=self.bob, abilities=[],
        )
        middleware = _TokenIdentityMiddleware(self.auth, self.permissions)
        observed: dict[str, tuple[object, bool]] = {}

        async def call_next() -> str:
            return "handled"

        async def handle(name: str, plain_text: str) -> None:
            async with ScopeManager() as scope:
                request = self.apiRequest(plain_text)
                scope[Request] = request
                await middleware.handle(request, call_next)
                await asyncio.sleep(0)
                observed[name] = (
                    self.auth.identifier(),
                    await self.auth.can("users.view"),
                )

        await asyncio.gather(
            handle("ada", ada_token.plain_text),
            handle("bob", bob_token.plain_text),
        )

        self.assertEqual(observed["ada"], (self.ada.id, True))
        self.assertEqual(observed["bob"], (self.bob.id, False))

    async def testConcurrentResolutionReusesOneContext(self) -> None:
        """Resolve the identity of one request from eight coroutines at once.

        Validates that repeated middleware resolutions coalesce into a
        single context instead of racing each other.
        """
        middleware = ResolveIdentityMiddleware(self.auth, self.permissions)
        session = Session()
        session.put("_auth_identifier", self.ada.id)
        request = self.webRequest(session)
        async with ScopeManager() as scope:
            scope[Request] = request
            contexts = await asyncio.gather(*(
                middleware._establish(request) for _ in range(8)
            ))
            self.assertEqual(len({id(context) for context in contexts}), 1)

    async def testLoginAndLogoutSerializeInOneRequest(self) -> None:
        """Queue a login and a logout behind the same authentication lock.

        Validates that both transitions apply in acquisition order, so a
        request never ends up in a half authenticated state.
        """
        async with ScopeManager() as scope:
            scope[Request] = self.webRequest()
            async with authentication_lock():
                login = asyncio.create_task(self.auth.login(self.ada))
                logout = asyncio.create_task(self.auth.logout())
            await asyncio.gather(login, logout)
            self.assertTrue(self.auth.guest())
            self.assertTrue(scope[Request].state.session.invalidated)

    async def testTokenAuthenticationCannotMintAnUnrestrictedCredential(self) -> None:
        """Issue a token from a request authenticated by a restricted token.

        Validates the privilege escalation guard: a limited credential
        must never be able to mint an unrestricted one.
        """
        issued = await self.tokens.create(self.ada, "limited", abilities=[])
        middleware = _TokenIdentityMiddleware(self.auth, self.permissions)
        async with ScopeManager() as scope:
            request = self.apiRequest(issued.plain_text)
            scope[Request] = request
            await middleware._establish(request)
            with self.assertRaises(AuthorizationException):
                await self.auth.createToken("escalated")

    async def testAnAuthenticatedRequestCannotSilentlySwitchGuards(self) -> None:
        """Resolve a session identity over a request already holding a token.

        Validates that a session fallback can never replace a token
        context, which would silently drop its ability restrictions.
        """
        issued = await self.tokens.create(self.ada, "limited", abilities=[])
        token_middleware = _TokenIdentityMiddleware(self.auth, self.permissions)
        session_middleware = ResolveSessionIdentityMiddleware(
            self.auth, self.permissions,
        )
        inherited_middleware = ResolveIdentityMiddleware(self.auth, self.permissions)
        async with ScopeManager() as scope:
            request = self.webRequest()
            request.bearerToken = issued.plain_text
            request.state.session.put("_auth_identifier", self.bob.id)
            scope[Request] = request
            await token_middleware._establish(request)
            context = await inherited_middleware._establish(request)
            self.assertEqual(context.guard, "token")
            self.assertEqual(context.abilities, frozenset())
            with self.assertRaises(AuthenticationException):
                await session_middleware._establish(request)
            self.assertEqual(self.auth.identifier(), self.ada.id)

class TestAuthManagerContext(_ManagerCase):
    """Validate how the manager exposes the context of the request."""

    def testTheAccessorMirrorsTheScopedContext(self) -> None:
        """Compare the accessor against the scope bound context.

        Validates that the manager owns no state of its own and always
        reads the context published by the running scope.
        """
        self.assertIs(self.auth.context(), current_auth_context())

    async def testTheContextCarriesTheAuthenticatedIdentity(self) -> None:
        """Read the context right after a successful login.

        Validates that the identity, the guard and the scope binding are
        all visible through a single accessor.
        """
        async with ScopeManager() as scope:
            scope[Request] = self.webRequest()
            await self.auth.login(self.ada)

            context = self.auth.context()

            self.assertIs(context, current_auth_context())
            self.assertIs(context.identity, self.ada)
            self.assertEqual(context.guard, "session")


class TestAuthManagerAuthorizationSnapshot(_ManagerCase):
    """Validate the immutable authorization view of a request."""

    async def testExposesDirectAndInheritedGrants(self) -> None:
        """Read the snapshot of an identity holding a role.

        Validates that permissions and roles are resolved together, which
        is what the authorizer intersects with the credential abilities.
        """
        await self.registrar.grantToRole("admin", "users.view")
        await self.registrar.assignRole(self.ada, "admin")
        await self.registrar.givePermissionTo(self.ada, "users.export")

        async with ScopeManager() as scope:
            scope[Request] = self.webRequest()
            await self.auth.login(self.ada)

            snapshot = await self.auth.authorization()

            self.assertEqual(
                snapshot.permissions, frozenset({"users.view", "users.export"}),
            )
            self.assertEqual(snapshot.roles, frozenset({"admin"}))
            self.assertIsNone(snapshot.abilities)

    async def testAGuestSnapshotGrantsNothing(self) -> None:
        """Read the snapshot of an anonymous request.

        Validates the deny by default stance: an unauthenticated request
        never reaches the permission store.
        """
        snapshot = await self.auth.authorization()

        self.assertEqual(snapshot.permissions, frozenset())
        self.assertEqual(snapshot.roles, frozenset())

    async def testATokenNarrowsTheSnapshotAbilities(self) -> None:
        """Read the snapshot of a token authenticated request.

        Validates that the restriction of the presented credential is
        reported next to what the identity owns.
        """
        await self.registrar.givePermissionTo(
            self.ada, "users.view", "users.delete",
        )
        issued = await self.auth.createToken(
            "reader", tokenable=self.ada, abilities=["users.view"],
        )
        middleware = _TokenIdentityMiddleware(self.auth, self.permissions)

        async with ScopeManager() as scope:
            request = self.apiRequest(issued.plain_text)
            scope[Request] = request
            await middleware._establish(request)

            snapshot = await self.auth.authorization()

            self.assertEqual(snapshot.abilities, frozenset({"users.view"}))
            self.assertEqual(
                snapshot.permissions, frozenset({"users.view", "users.delete"}),
            )


class TestAuthManagerPartialPermissionChecks(_ManagerCase):
    """Validate the any-of permission check of the manager."""

    async def testGrantsWhenASinglePermissionMatches(self) -> None:
        """Ask for two permissions while the identity owns only one.

        Validates the any-of semantics used by routes accepting several
        equivalent rights.
        """
        await self.registrar.givePermissionTo(self.ada, "users.view")

        async with ScopeManager() as scope:
            scope[Request] = self.webRequest()
            await self.auth.login(self.ada)

            self.assertTrue(
                await self.auth.canAny(["users.view", "users.delete"]),
            )
            self.assertFalse(
                await self.auth.canAll(["users.view", "users.delete"]),
            )

    async def testDeniesWhenNoPermissionMatches(self) -> None:
        """Ask for permissions the identity does not own at all.

        Validates that the any-of check never degrades into an implicit
        grant.
        """
        async with ScopeManager() as scope:
            scope[Request] = self.webRequest()
            await self.auth.login(self.ada)

            self.assertFalse(
                await self.auth.canAny(["users.view", "users.delete"]),
            )

    async def testGuestsAreDeniedEveryPartialCheck(self) -> None:
        """Run the any-of check without an authenticated identity.

        Validates that an anonymous request is refused before any store
        is queried.
        """
        self.assertFalse(await self.auth.canAny(["users.view"]))


class TestAuthManagerTokenOwnership(_ManagerCase):
    """Validate which identities may own a personal access token."""

    async def testRejectsAnOwnerThatCannotHoldPermissions(self) -> None:
        """Issue a token for an identity that is not authorizable.

        Validates the guard protecting the polymorphic owner columns: a
        token row without a usable authorization key would be orphaned.
        """
        with self.assertRaises(AuthException) as captured:
            await self.auth.createToken(
                "ci",
                tokenable=_UnauthorizableIdentity(),  # type: ignore[arg-type]
            )

        self.assertIn("IAuthorizable", str(captured.exception))
        self.assertNotIsInstance(captured.exception, AuthenticationException)
        self.assertNotIsInstance(captured.exception, AuthorizationException)

    async def testARevocationRaceRevokesTheCredentialOnlyOnce(self) -> None:
        """Queue a revocation behind a transition that logs the request out.

        Validates the second credential check performed once the lock is
        acquired: without it the manager would revoke a credential that
        no longer belongs to the request.
        """
        issued = await self.auth.createToken("ci", tokenable=self.ada)
        middleware = _TokenIdentityMiddleware(self.auth, self.permissions)

        async with ScopeManager() as scope:
            request = self.apiRequest(issued.plain_text)
            scope[Request] = request
            await middleware._establish(request)

            async with authentication_lock():
                revocation = asyncio.create_task(
                    self.auth.revokeCurrentToken(),
                )
                await asyncio.sleep(0)
                bind_auth_context(AuthenticationContext(guard="token"))

            revoked = await revocation

        self.assertFalse(revoked)
        self.assertIsNotNone(
            await self.tokens.findByPlainText(issued.plain_text),
        )


class TestAuthManagerOutsideAnHttpRequest(_ManagerCase):
    """Validate the guard protecting the session lifecycle operations."""

    async def asyncSetUp(self) -> None:
        """Detach the ambient scope installed by the test runner."""
        await super().asyncSetUp()
        self._scope_token = ScopedContext.setCurrentScope(None)

    async def asyncTearDown(self) -> None:
        """Restore the ambient scope before tearing the fixture down."""
        ScopedContext.reset(self._scope_token)
        await super().asyncTearDown()

    async def testLoginIsRefusedWithoutAScope(self) -> None:
        """Log an identity in from outside any container scope.

        Validates the refusal a console command gets: there is no session
        to remember the identity in.
        """
        with self.assertRaises(AuthException):
            await self.auth.login(self.ada)

    async def testLogoutIsRefusedWithoutAScope(self) -> None:
        """Log out from outside any container scope.

        Validates that the symmetric operation is refused for the very
        same reason.
        """
        with self.assertRaises(AuthException):
            await self.auth.logout()

    async def testLoginIsRefusedWhenTheScopeCarriesNoRequest(self) -> None:
        """Log an identity in inside a scope holding no request.

        Validates the second half of the guard: an active scope is not
        enough, the request itself must be reachable.
        """
        async with ScopeManager():
            with self.assertRaises(AuthException):
                await self.auth.login(self.ada)

