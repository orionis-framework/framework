from types import SimpleNamespace
from typing import Any, ClassVar
from orionis.auth.context.context import AuthenticationContext
from orionis.auth.context.functions import bind_auth_context, current_auth_context
from orionis.auth.entities.guard_result import GuardResult
from orionis.auth.exceptions import (
    AuthConfigurationException,
    AuthenticationException,
    AuthorizationException,
)
from orionis.auth.middleware.authenticate import (
    AuthenticateMiddleware,
    AuthenticateSessionMiddleware,
    AuthenticateTokenMiddleware,
)
from orionis.auth.middleware.authorize import (
    RequirePermissionMiddleware,
    RequireRoleMiddleware,
)
from orionis.auth.middleware.policy import RequirePolicyMiddleware
from orionis.auth.middleware.guest import GuestMiddleware
from orionis.auth.middleware.resolve_identity import ResolveIdentityMiddleware
from orionis.container.context.manager import ScopeManager
from orionis.http.middleware import BaseMiddleware
from orionis.http.responses import RedirectResponse
from orionis.test import TestCase

class _Identity:
    """Identity double answering the authenticatable contract."""

    __slots__ = ("identifier",)

    def __init__(self, identifier: int = 1) -> None:
        """Store the identifier answered by the contract method."""
        self.identifier = identifier

    def getAuthIdentifierName(self) -> str:
        """Return the attribute holding the identifier."""
        return "identifier"

    def getAuthIdentifier(self) -> object:
        """Return the identifier of this identity."""
        return self.identifier

    def getAuthPassword(self) -> str:
        """Return an empty hash; credentials are irrelevant here."""
        return ""

class _StaticGuard:
    """Guard double resolving a fixed result."""

    __slots__ = ("_name", "_result", "calls")

    def __init__(self, name: str, result: GuardResult | None) -> None:
        """Store the guard name and the result it always answers."""
        self._name = name
        self._result = result
        self.calls = 0

    @property
    def name(self) -> str:
        """Return the configured guard name."""
        return self._name

    async def resolve(self, request: object) -> GuardResult | None:  # noqa: ARG002
        """Return the configured result and count the call."""
        self.calls += 1
        return self._result

class _StubManager:
    """Manager double exposing only the guard registry."""

    __slots__ = ("guards", "requested")

    def __init__(self, guards: dict[str | None, _StaticGuard]) -> None:
        """Store the guards this manager can hand out."""
        self.guards = guards
        self.requested: list[str | None] = []

    def guard(self, name: str | None = None) -> _StaticGuard:
        """Return the guard registered under the requested name."""
        self.requested.append(name)
        return self.guards[name]

class _StaticRepository:
    """Permission repository double returning a fixed authorization."""

    __slots__ = ("permissions", "roles")

    def __init__(
        self,
        permissions: tuple[str, ...] = (),
        roles: tuple[str, ...] = (),
    ) -> None:
        """Store the authorization every identity resolves to."""
        self.permissions = permissions
        self.roles = roles

    async def loadFor(
        self,
        authorizable: object,  # noqa: ARG002
    ) -> tuple[frozenset[str], frozenset[str]]:
        """Return the configured permissions and roles."""
        return frozenset(self.permissions), frozenset(self.roles)

class _StubApp:
    """Application double answering only the auth configuration."""

    __slots__ = ("_redirect_to",)

    def __init__(self, redirect_to: str | None = None) -> None:
        """Store the configured redirect target."""
        self._redirect_to = redirect_to

    def config(self, key: str | None = None) -> Any:  # noqa: ANN401
        """Answer the single key the middleware reads."""
        if key == "auth.session.redirect_to":
            return self._redirect_to
        return None

class _RecordingAuthorizer:
    """Authorizer double answering fixed verdicts."""

    __slots__ = ("calls", "verdict")

    def __init__(self, verdict: bool) -> None:  # noqa: FBT001
        """Store the verdict every check answers."""
        self.verdict = verdict
        self.calls: list[tuple[str, object]] = []

    async def can(self, context: object, permission: str) -> bool:  # noqa: ARG002
        """Record and answer a single permission check."""
        self.calls.append(("can", permission))
        return self.verdict

    async def canAny(self, context: object, permissions: object) -> bool:  # noqa: ARG002
        """Record and answer an any-of permission check."""
        self.calls.append(("canAny", tuple(permissions)))
        return self.verdict

    async def canAll(self, context: object, permissions: object) -> bool:  # noqa: ARG002
        """Record and answer an all-of permission check."""
        self.calls.append(("canAll", tuple(permissions)))
        return self.verdict

    async def hasRole(self, context: object, role: str) -> bool:  # noqa: ARG002
        """Record and answer a role check."""
        self.calls.append(("hasRole", role))
        return self.verdict

    async def allows(
        self,
        context: object,  # noqa: ARG002
        ability: str,
        resource: object,
    ) -> bool:
        """Record and answer a policy check."""
        self.calls.append(("allows", (ability, resource)))
        return self.verdict

    def registerPolicy(self, resource: type, policy: type) -> None:
        """Record a policy registration."""
        self.calls.append(("registerPolicy", (resource, policy)))

class _Post:
    """Resource double protected by a policy."""

    __slots__ = ()

def web_request(*, wants_json: bool = False, ajax: bool = False) -> SimpleNamespace:
    """Build a request double with content negotiation answers."""
    return SimpleNamespace(
        state=SimpleNamespace(),
        wantsJson=lambda: wants_json,
        isAjax=lambda: ajax,
    )

async def call_next() -> str:
    """Terminal of the pipeline used by every middleware test."""
    return "handled"

class _CanViewUsers(RequirePermissionMiddleware):
    """Route guard requiring a single permission."""

    __slots__ = ()

    permissions: ClassVar[tuple[str, ...]] = ("users.view",)

class _CanManageUsers(RequirePermissionMiddleware):
    """Route guard requiring several permissions at once."""

    __slots__ = ()

    permissions: ClassVar[tuple[str, ...]] = ("users.view", "users.delete")
    requires_all: ClassVar[bool] = False

class _MissingPermissions(RequirePermissionMiddleware):
    """Misconfigured route guard declaring no permission."""

    __slots__ = ()

class _MustBeAdmin(RequireRoleMiddleware):
    """Route guard requiring a single role."""

    __slots__ = ()

    roles: ClassVar[tuple[str, ...]] = ("admin",)

class _MissingRoles(RequireRoleMiddleware):
    """Misconfigured route guard declaring no role."""

    __slots__ = ()

class _CanCreatePosts(RequirePolicyMiddleware):
    """Route guard delegating to the policy of a resource class."""

    __slots__ = ()

    ability: ClassVar[str] = "create"
    resource: ClassVar[type | None] = _Post

class _MissingPolicy(RequirePolicyMiddleware):
    """Misconfigured route guard declaring no ability nor resource."""

    __slots__ = ()

class TestResolveIdentityMiddleware(TestCase):
    """Validate the middleware that only establishes the context."""

    async def testBindsTheResolvedIdentity(self) -> None:
        """Validates the normal path of identity resolution.

        Everything downstream reads the identity from the context.
        """
        guard = _StaticGuard(
            "session", GuardResult(identity=_Identity(7), guard="session"),
        )
        middleware = ResolveIdentityMiddleware(
            _StubManager({None: guard}), _StaticRepository(),
        )
        request = web_request()

        async with ScopeManager():
            result = await middleware.handle(request, call_next)

            self.assertEqual(result, "handled")
            self.assertEqual(current_auth_context().identifier(), 7)

    async def testGuestsStillReachTheController(self) -> None:
        """Validates that this middleware never rejects.

        Public pages must keep working for anonymous visitors.
        """
        guard = _StaticGuard("session", None)
        middleware = ResolveIdentityMiddleware(
            _StubManager({None: guard}), _StaticRepository(),
        )

        async with ScopeManager():
            result = await middleware.handle(web_request(), call_next)

            self.assertEqual(result, "handled")
            self.assertTrue(current_auth_context().isGuest)

    async def testUsesTheDefaultGuardUnlessPinned(self) -> None:
        """Validates how the guard is selected.

        The base class defers to the configured default guard.
        """
        guard = _StaticGuard("session", None)
        manager = _StubManager({None: guard})
        middleware = ResolveIdentityMiddleware(manager, _StaticRepository())

        async with ScopeManager():
            await middleware.handle(web_request(), call_next)

        self.assertEqual(manager.requested, [None])

    async def testCarriesTheCredentialAbilitiesIntoTheContext(self) -> None:
        """Validates that a token restriction survives the middleware.

        Dropping the abilities would silently widen the credential.
        """
        guard = _StaticGuard(
            "token",
            GuardResult(
                identity=_Identity(7),
                guard="token",
                abilities=frozenset({"users.view"}),
                credential_id=99,
            ),
        )
        middleware = ResolveIdentityMiddleware(
            _StubManager({None: guard}), _StaticRepository(("users.view",)),
        )

        async with ScopeManager():
            await middleware.handle(web_request(), call_next)
            context = current_auth_context()

            self.assertEqual(context.abilities, frozenset({"users.view"}))
            self.assertEqual(context.credentialId, 99)

class TestAuthenticateMiddleware(TestCase):
    """Validate the middleware that rejects anonymous requests."""

    async def testAuthenticatedRequestsContinue(self) -> None:
        """Validates the happy path.

        A resolved identity reaches the controller untouched.
        """
        guard = _StaticGuard(
            "session", GuardResult(identity=_Identity(1), guard="session"),
        )
        middleware = AuthenticateMiddleware(
            _StubApp(), _StubManager({None: guard}), _StaticRepository(),
        )

        async with ScopeManager():
            self.assertEqual(
                await middleware.handle(web_request(), call_next), "handled",
            )

    async def testGuestsRaiseAnAuthenticationError(self) -> None:
        """Validates the ``401`` path without a redirect target.

        The exception handler turns it into an unauthenticated response.
        """
        guard = _StaticGuard("session", None)
        middleware = AuthenticateMiddleware(
            _StubApp(), _StubManager({None: guard}), _StaticRepository(),
        )

        async with ScopeManager():

            with self.assertRaises(AuthenticationException):

                await middleware.handle(web_request(), call_next)

    async def testBrowsersAreRedirectedToTheConfiguredPage(self) -> None:
        """Validates the browser friendly rejection.

        A redirect keeps the flash data alive, unlike a raised exception.
        """
        guard = _StaticGuard("session", None)
        middleware = AuthenticateMiddleware(
            _StubApp("/login"),
            _StubManager({None: guard}),
            _StaticRepository(),
        )

        async with ScopeManager():
            response = await middleware.handle(web_request(), call_next)

        self.assertIsInstance(response, RedirectResponse)
        self.assertEqual(response.status_code, 302)

    async def testJsonClientsNeverGetARedirect(self) -> None:
        """Validates the content negotiation of the rejection.

        An API client expects a status code, not a redirect.
        """
        guard = _StaticGuard("session", None)
        middleware = AuthenticateMiddleware(
            _StubApp("/login"),
            _StubManager({None: guard}),
            _StaticRepository(),
        )

        async with ScopeManager():

            with self.assertRaises(AuthenticationException):

                await middleware.handle(web_request(wants_json=True), call_next)

    async def testAjaxClientsNeverGetARedirect(self) -> None:
        """Validates that background requests are answered with a status.

        Following a redirect would replace the page fragment with HTML.
        """
        guard = _StaticGuard("session", None)
        middleware = AuthenticateMiddleware(
            _StubApp("/login"),
            _StubManager({None: guard}),
            _StaticRepository(),
        )

        async with ScopeManager():

            with self.assertRaises(AuthenticationException):

                await middleware.handle(web_request(ajax=True), call_next)

    async def testTheGuardSpecificVariantsPinTheirGuard(self) -> None:
        """Validates the ready made session and token middlewares.

        Each one must always ask for its own guard.
        """
        session_guard = _StaticGuard("session", None)
        token_guard = _StaticGuard("token", None)
        manager = _StubManager({
            "session": session_guard, "token": token_guard,
        })

        session_middleware = AuthenticateSessionMiddleware(
            _StubApp(), manager, _StaticRepository(),
        )
        token_middleware = AuthenticateTokenMiddleware(
            _StubApp(), manager, _StaticRepository(),
        )

        for middleware in (session_middleware, token_middleware):
            async with ScopeManager():
                with self.assertRaises(AuthenticationException):
                    await middleware.handle(web_request(), call_next)

        self.assertEqual(manager.requested, ["session", "token"])

    async def testTokenRoutesNeverRedirectToTheSessionLogin(self) -> None:
        """Return an authentication failure for token clients without Accept."""
        middleware = AuthenticateTokenMiddleware(
            _StubApp("/login"),
            _StubManager({"token": _StaticGuard("token", None)}),
            _StaticRepository(),
        )
        async with ScopeManager():
            with self.assertRaises(AuthenticationException):
                await middleware.handle(web_request(), call_next)

class TestRequirePermissionMiddleware(TestCase):
    """Validate the permission gate placed on a route."""

    async def testAllowsAnAuthorizedIdentity(self) -> None:
        """Validates the happy path of a permission gate.

        The controller runs when the permission is granted.
        """
        authorizer = _RecordingAuthorizer(verdict=True)
        middleware = _CanViewUsers(authorizer)

        async with ScopeManager():
            bind_auth_context(
                AuthenticationContext(identity=_Identity(), guard="session"),
            )
            self.assertEqual(
                await middleware.handle(web_request(), call_next), "handled",
            )

        self.assertEqual(authorizer.calls, [("canAll", ("users.view",))])

    async def testRejectsAnUnauthorizedIdentity(self) -> None:
        """Validates the ``403`` path.

        The identity is known but lacks the permission.
        """
        middleware = _CanViewUsers(_RecordingAuthorizer(verdict=False))

        async with ScopeManager():
            bind_auth_context(
                AuthenticationContext(identity=_Identity(), guard="session"),
            )
            with self.assertRaises(AuthorizationException):
                await middleware.handle(web_request(), call_next)

    async def testRejectsGuestsAsUnauthenticated(self) -> None:
        """Validates the ``401`` path of an authorization gate.

        A guest is not forbidden, it is simply unauthenticated.
        """
        middleware = _CanViewUsers(_RecordingAuthorizer(verdict=True))

        async with ScopeManager():

            with self.assertRaises(AuthenticationException):

                await middleware.handle(web_request(), call_next)

    async def testSupportsAnyOfSemantics(self) -> None:
        """Validates the alternative combination mode.

        Holding one of the listed permissions is enough.
        """
        authorizer = _RecordingAuthorizer(verdict=True)
        middleware = _CanManageUsers(authorizer)

        async with ScopeManager():
            bind_auth_context(
                AuthenticationContext(identity=_Identity(), guard="session"),
            )
            await middleware.handle(web_request(), call_next)

        self.assertEqual(authorizer.calls[0][0], "canAny")

    async def testFailsFastWhenNoPermissionIsDeclared(self) -> None:
        """Validates the guard against a misconfigured subclass.

        Silently allowing the request would be a security hole.
        """
        middleware = _MissingPermissions(_RecordingAuthorizer(verdict=True))

        async with ScopeManager():

            with self.assertRaises(AuthConfigurationException):

                await middleware.handle(web_request(), call_next)

    def testIsARegularMiddlewareClass(self) -> None:
        """Validates that the gate plugs into the routing pipeline.

        Only ``BaseMiddleware`` subclasses may be attached to a route.
        """
        self.assertTrue(issubclass(_CanViewUsers, BaseMiddleware))

class TestRequireRoleMiddleware(TestCase):
    """Validate the role gate placed on a route."""

    async def testAllowsAnIdentityHoldingTheRole(self) -> None:
        """Validates the happy path of a role gate.

        Roles are evaluated through the authorizer.
        """
        authorizer = _RecordingAuthorizer(verdict=True)
        middleware = _MustBeAdmin(authorizer)

        async with ScopeManager():
            bind_auth_context(
                AuthenticationContext(identity=_Identity(), guard="session"),
            )
            self.assertEqual(
                await middleware.handle(web_request(), call_next), "handled",
            )

        self.assertEqual(authorizer.calls, [("hasRole", "admin")])

    async def testRejectsAnIdentityWithoutTheRole(self) -> None:
        """Validates the ``403`` path of a role gate.

        The controller must never run.
        """
        middleware = _MustBeAdmin(_RecordingAuthorizer(verdict=False))

        async with ScopeManager():
            bind_auth_context(
                AuthenticationContext(identity=_Identity(), guard="session"),
            )
            with self.assertRaises(AuthorizationException):
                await middleware.handle(web_request(), call_next)

    async def testRejectsGuestsAsUnauthenticated(self) -> None:
        """Validates that anonymous requests are answered with ``401``.

        Roles cannot be evaluated without an identity.
        """
        middleware = _MustBeAdmin(_RecordingAuthorizer(verdict=True))

        async with ScopeManager():

            with self.assertRaises(AuthenticationException):

                await middleware.handle(web_request(), call_next)

    async def testFailsFastWhenNoRoleIsDeclared(self) -> None:
        """Validates the guard against a misconfigured subclass.

        An empty requirement would let everything through.
        """
        middleware = _MissingRoles(_RecordingAuthorizer(verdict=True))

        async with ScopeManager():

            with self.assertRaises(AuthConfigurationException):

                await middleware.handle(web_request(), call_next)

    async def testRoleMembershipCannotBypassTokenRestrictions(self) -> None:
        """Require a capability gate for restricted token credentials."""
        middleware = _MustBeAdmin(_RecordingAuthorizer(verdict=True))
        async with ScopeManager():
            bind_auth_context(AuthenticationContext(
                identity=_Identity(), guard="token", abilities=(),
            ))
            with self.assertRaises(AuthorizationException):
                await middleware.handle(web_request(), call_next)

class TestRequirePolicyMiddleware(TestCase):
    """Validate the policy gate placed on a route."""

    async def testAllowsWhenThePolicyAgrees(self) -> None:
        """Validates the happy path of a policy gate.

        The ability is evaluated against the resource class.
        """
        authorizer = _RecordingAuthorizer(verdict=True)
        middleware = _CanCreatePosts(authorizer)

        async with ScopeManager():
            bind_auth_context(
                AuthenticationContext(identity=_Identity(), guard="session"),
            )
            self.assertEqual(
                await middleware.handle(web_request(), call_next), "handled",
            )

        self.assertEqual(authorizer.calls, [("allows", ("create", _Post))])

    async def testRejectsWhenThePolicyDenies(self) -> None:
        """Validates the ``403`` path of a policy gate.

        A denial must stop the pipeline.
        """
        middleware = _CanCreatePosts(_RecordingAuthorizer(verdict=False))

        async with ScopeManager():
            bind_auth_context(
                AuthenticationContext(identity=_Identity(), guard="session"),
            )
            with self.assertRaises(AuthorizationException):
                await middleware.handle(web_request(), call_next)

    async def testRejectsGuestsAsUnauthenticated(self) -> None:
        """Validates that anonymous requests never reach a policy.

        Policies always receive a real identity.
        """
        middleware = _CanCreatePosts(_RecordingAuthorizer(verdict=True))

        async with ScopeManager():

            with self.assertRaises(AuthenticationException):

                await middleware.handle(web_request(), call_next)

    async def testFailsFastWhenTheGateIsIncomplete(self) -> None:
        """Validates the guard against a misconfigured subclass.

        Both the ability and the resource are mandatory.
        """
        middleware = _MissingPolicy(_RecordingAuthorizer(verdict=True))

        async with ScopeManager():

            with self.assertRaises(AuthConfigurationException):

                await middleware.handle(web_request(), call_next)

class TestGuestMiddleware(TestCase):
    """Validate the guest-only routes used for login and registration."""

    async def testGuestsReachTheForm(self) -> None:
        """Continue without inventing an authenticated identity."""
        middleware = GuestMiddleware(
            _StubManager({"session": _StaticGuard("session", None)}),
            _StaticRepository(),
        )
        async with ScopeManager():
            self.assertEqual(
                await middleware.handle(web_request(), call_next), "handled",
            )

    async def testAuthenticatedBrowsersLeaveTheGuestRoute(self) -> None:
        """Redirect an authenticated browser away from the login form."""
        result = GuardResult(identity=_Identity(), guard="session")
        middleware = GuestMiddleware(
            _StubManager({"session": _StaticGuard("session", result)}),
            _StaticRepository(),
        )
        async with ScopeManager():
            response = await middleware.handle(web_request(), call_next)
            self.assertEqual(response.getStatusCode(), 302)

    async def testAuthenticatedJsonClientsAreForbidden(self) -> None:
        """Use 403 for a known identity denied access to a guest-only route."""
        result = GuardResult(identity=_Identity(), guard="session")
        middleware = GuestMiddleware(
            _StubManager({"session": _StaticGuard("session", result)}),
            _StaticRepository(),
        )
        async with ScopeManager():
            with self.assertRaises(AuthorizationException):
                await middleware.handle(web_request(wants_json=True), call_next)
