"""Exercise automatic authentication with real guards and request scopes."""
import asyncio
from typing import TYPE_CHECKING, ClassVar
import msgspec
from orionis.auth.concerns.authenticatable import Authenticatable
from orionis.auth.concerns.authorizable import Authorizable
from orionis.auth.context.functions import current_auth_context
from orionis.auth.entities.access_token import AccessToken
from orionis.auth.exceptions import AuthenticationException
from orionis.auth.guards.session_guard import SessionGuard
from orionis.auth.guards.token_guard import TokenGuard
from orionis.auth.manager import AuthManager
from orionis.auth.middleware import (
    AuthenticateMiddleware,
    AuthenticateSessionMiddleware,
    AuthenticateTokenMiddleware,
    GuestMiddleware,
    RequirePermissionMiddleware,
    ResolveIdentityMiddleware,
    ResolveSessionIdentityMiddleware,
    ResolveTokenIdentityMiddleware,
)
from orionis.console.output.http_request import HTTPRequestPrinter
from orionis.container.context.manager import ScopeManager
from orionis.container.context.scope import ScopedContext
from orionis.http.adapters.response.asgi import ASGIResponseAdapter
from orionis.http.adapters.response.rsgi import RSGIResponseAdapter
from orionis.http.default.responses import DefaultResponses
from orionis.http.kernel import KernelHTTP
from orionis.http.layer.web.exceptions import CSRFTokenMismatchException
from orionis.http.layer.web.start_session import StartSessionMiddleware
from orionis.http.middleware import BaseMiddleware
from orionis.http.request import Request
from orionis.http.responses import JSONResponse, Response
from orionis.http.routes.loader import RouteLoader
from orionis.test import TestCase
from tests.auth.test_middleware import _RecordingAuthorizer, _StaticRepository
from tests.http.routes.test_nested_routing import compile_router, make_router
from tests.http.test_kernel import (
    _StubApp,
    _StubCatch,
    _StubDefaultResponses,
    _StubRequestPrinter,
    _StubResponseAdapter,
    _StubRouteLoader,
    _StubRsgiHeaders,
    _StubRsgiProtocol,
    _StubRsgiScope,
    dispatch,
    make_http_config,
)

if TYPE_CHECKING:
    from orionis.http.layer.contracts.middleware import NextCallable

_CREDENTIAL = "test-api-credential"
_CSRF = "test-csrf-value"

def identity_handler() -> JSONResponse:
    """Expose the identity visible to a controller in the current request."""
    context = current_auth_context()
    request = ScopedContext.getCurrentScope()[Request]
    return JSONResponse({
        "identifier": context.identifier(),
        "guard": context.guard,
        "abilities": sorted(context.abilities or ()),
        "session": getattr(request.state, "session", None) is not None,
    })

class _Session:
    """Request-local session populated by the session restoration fixture."""

    __slots__ = ("data",)

    def __init__(self, identifier: str | None) -> None:
        """Keep the optional identifier and the configured CSRF token."""
        self.data: dict[str, object] = {"_csrf_token": _CSRF}
        if identifier:
            self.data["_auth_identifier"] = identifier

    def get(self, key: str) -> object:
        """Read a value as the session guard does in production."""
        return self.data.get(key)

    def forget(self, key: str) -> None:
        """Remove a stale identity reference."""
        self.data.pop(key, None)

class _RestoreSession(BaseMiddleware):
    """Restore a session for web requests without opening external storage."""

    __slots__ = ()

    async def handle(self, request: Request, call_next: NextCallable) -> Response:
        """Attach a distinct session before CSRF and session authentication."""
        request.state.session = _Session(request.headers.get("x-session-identity"))
        return await call_next()

class _Identity(Authenticatable, Authorizable):
    """Identity double mixing both authentication concerns."""

    __slots__ = ("id", "password")

    def __init__(self, identifier: int, password: str) -> None:
        """Store the identifier and the stored password hash."""
        self.id = identifier
        self.password = password

class _Identities:
    """Record identity lookups while yielding to concurrent requests."""

    __slots__ = ("calls",)

    def __init__(self) -> None:
        """Start with no repository calls."""
        self.calls: list[object] = []

    async def retrieveById(self, identifier: object) -> _Identity | None:
        """Return two persisted identities and reject stale identifiers."""
        self.calls.append(identifier)
        await asyncio.sleep(0)
        if str(identifier) in {"7", "8"}:
            return _Identity(int(identifier), "")
        return None

class _Tokens:
    """Record token lookups and usage updates without external storage."""

    __slots__ = ("lookups", "touches")

    def __init__(self) -> None:
        """Start with no credential reads or writes."""
        self.lookups: list[str] = []
        self.touches: list[object] = []

    async def findByPlainText(self, value: str) -> AccessToken | None:
        """Accept one credential with a restricted permission set."""
        self.lookups.append(value)
        if value != _CREDENTIAL:
            return None
        return AccessToken(
            id=1, tokenable_id=7, tokenable_type=_Identity(7, "").getAuthorizableType(),
            name="tests", abilities=frozenset({"users.view"}),
        )

    async def touch(self, identifier: object) -> bool:
        """Record the usage update performed by the real token guard."""
        self.touches.append(identifier)
        return True

class _AuthApp(_StubApp):
    """Open real container scopes for the kernel's public entry point."""

    __slots__ = ()

    def beginScope(self) -> ScopeManager:
        """Let the kernel own identity isolation and scope cleanup."""
        return ScopeManager()

class _CanViewUsers(RequirePermissionMiddleware):
    """Require a permission after the kernel has established an identity."""

    __slots__ = ()

    permissions: ClassVar[tuple[str, ...]] = ("users.view",)

async def boot_auth_kernel(
    *, csrf_enabled: bool = False, default_guard: str = "session",
) -> tuple[KernelHTTP, _Identities, _Tokens, _StubCatch]:
    """Boot real routing, guards and middleware with in-memory collaborators."""
    router = make_router()
    router.get("/public", identity_handler)
    router.post("/public", identity_handler)
    router.get("/private", identity_handler).middleware(AuthenticateSessionMiddleware)
    router.get("/login", identity_handler).middleware(GuestMiddleware)
    router.get("/permission", identity_handler).middleware(_CanViewUsers)
    router.get("/optional", identity_handler).middleware(ResolveIdentityMiddleware)
    router._setKind("api")
    router.get("/api/public", identity_handler)
    router.get("/api/private", identity_handler).middleware(AuthenticateTokenMiddleware)
    router.get("/api/generic", identity_handler).middleware(AuthenticateMiddleware)
    responses = _StubDefaultResponses()
    catch = _StubCatch()
    app = _AuthApp(
        {
            RouteLoader: _StubRouteLoader(compile_router(router), None),
            StartSessionMiddleware: _RestoreSession(),
            ASGIResponseAdapter: _StubResponseAdapter(),
            RSGIResponseAdapter: _StubResponseAdapter(),
            HTTPRequestPrinter: _StubRequestPrinter(),
            DefaultResponses: responses,
        },
        {
            "http": make_http_config(csrf_enabled=csrf_enabled),
            "auth.default": default_guard,
            "auth.session.redirect_to": "/login",
            "auth.session.home": "/private",
        },
    )
    identities = _Identities()
    tokens = _Tokens()
    repository = _StaticRepository()
    authorizer = _RecordingAuthorizer(True)
    manager = AuthManager(
        app, authorizer, repository, SessionGuard(app, identities),
        TokenGuard(tokens, identities), tokens,
    )
    for middleware in (
        ResolveIdentityMiddleware, ResolveSessionIdentityMiddleware,
        ResolveTokenIdentityMiddleware,
    ):
        app.builds[middleware] = middleware(manager, repository)
    for middleware in (
        AuthenticateMiddleware, AuthenticateSessionMiddleware,
        AuthenticateTokenMiddleware, GuestMiddleware,
    ):
        app.builds[middleware] = middleware(app, manager, repository)
    app.builds[_CanViewUsers] = _CanViewUsers(authorizer)
    kernel = KernelHTTP(app, catch)
    await kernel.boot()
    return kernel, identities, tokens, catch

class TestAutomaticAuthentication(TestCase):
    """Validate optional identity resolution before application middleware."""

    async def testPublicRoutesAllowGuestsWithoutRepositoryCalls(self) -> None:
        """Anonymous requests stay public and never query authentication storage."""
        kernel, identities, tokens, catch = await boot_auth_kernel()
        for path, guard in (("/public", "session"), ("/api/public", "token")):
            response = await dispatch(kernel, path)
            self.assertEqual(response.status_code, 200)
            data = msgspec.json.decode(response.getBody())
            self.assertIsNone(data["identifier"])
            self.assertEqual(data["guard"], guard)
            self.assertEqual(data["session"], guard == "session")
        self.assertEqual(identities.calls, [])
        self.assertEqual(tokens.lookups, [])
        self.assertEqual(catch.handled, [])

    async def testWebRestoresIdentityBeforePublicAndProtectedHandlers(self) -> None:
        """Session resolution precedes handlers, guest checks and authorization."""
        kernel, identities, tokens, catch = await boot_auth_kernel(
            default_guard="token",
        )
        headers = [(b"x-session-identity", b"7")]
        for path in ("/public", "/private", "/permission", "/optional"):
            response = await dispatch(kernel, path, headers=headers)
            self.assertEqual(response.status_code, 200)
            data = msgspec.json.decode(response.getBody())
            self.assertEqual(data["identifier"], 7)
            self.assertEqual(data["guard"], "session")
        response = await dispatch(kernel, "/login", headers=headers)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.getHeader("location"), ["/private"])
        self.assertEqual(identities.calls, ["7"] * 5)
        self.assertEqual(tokens.lookups, [])
        self.assertEqual(catch.handled, [])

    async def testApiResolvesBearerOnceAndRetainsAbilities(self) -> None:
        """Both explicit and generic authentication reuse the resolved token."""
        kernel, identities, tokens, catch = await boot_auth_kernel()
        for path in ("/api/public", "/api/private", "/api/generic"):
            response = await dispatch(kernel, path, headers=[
                (b"authorization", f"Bearer {_CREDENTIAL}".encode()),
            ])
            data = msgspec.json.decode(response.getBody())
            self.assertEqual(data["identifier"], 7)
            self.assertEqual(data["guard"], "token")
            self.assertEqual(data["abilities"], ["users.view"])
            self.assertFalse(data["session"])
        self.assertEqual(identities.calls, [7] * 3)
        self.assertEqual(tokens.lookups, [_CREDENTIAL] * 3)
        self.assertEqual(tokens.touches, [1] * 3)
        self.assertEqual(catch.handled, [])

    async def testWebIgnoresBearerAndApiIgnoresSessionCredentials(self) -> None:
        """Route kind determines the credential source even with both present."""
        kernel, identities, tokens, catch = await boot_auth_kernel()
        headers = [
            (b"x-session-identity", b"8"),
            (b"authorization", f"Bearer {_CREDENTIAL}".encode()),
        ]
        web_response = await dispatch(kernel, "/public", headers=headers)
        api_response = await dispatch(kernel, "/api/public", headers=headers)
        web = msgspec.json.decode(web_response.getBody())
        api = msgspec.json.decode(api_response.getBody())
        self.assertEqual(web["identifier"], 8)
        self.assertEqual(api["identifier"], 7)
        self.assertEqual(identities.calls, ["8", 7])
        self.assertEqual(tokens.lookups, [_CREDENTIAL])
        self.assertEqual(catch.handled, [])

    async def testInvalidCredentialsStayAnonymousOnPublicRoutes(self) -> None:
        """Stale sessions and rejected tokens preserve optional authentication."""
        kernel, identities, tokens, catch = await boot_auth_kernel()
        for path, headers in (
            ("/public", [(b"x-session-identity", b"404")]),
            ("/api/public", [(b"authorization", b"Bearer invalid")]),
        ):
            response = await dispatch(kernel, path, headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertIsNone(msgspec.json.decode(response.getBody())["identifier"])
        self.assertEqual(identities.calls, ["404"])
        self.assertEqual(tokens.lookups, ["invalid"])
        self.assertEqual(tokens.touches, [])
        self.assertEqual(catch.handled, [])

    async def testCredentialsFromTheOtherPipelineNeverAuthenticate(self) -> None:
        """A session alone cannot authenticate an API and a Bearer cannot log in web."""
        kernel, identities, tokens, catch = await boot_auth_kernel()
        for path, headers in (
            ("/api/public", [(b"x-session-identity", b"7")]),
            ("/public", [(b"authorization", f"Bearer {_CREDENTIAL}".encode())]),
        ):
            response = await dispatch(kernel, path, headers=headers)
            self.assertIsNone(msgspec.json.decode(response.getBody())["identifier"])
        self.assertEqual(identities.calls, [])
        self.assertEqual(tokens.lookups, [])
        self.assertEqual(catch.handled, [])

    async def testRsgiUsesTheSameAuthenticationPipeline(self) -> None:
        """Both transport entry points establish the same token context."""
        kernel, identities, tokens, catch = await boot_auth_kernel()
        scope = _StubRsgiScope("/api/public")
        scope.headers = _StubRsgiHeaders({
            "host": ["orionis.test"],
            "authorization": [f"Bearer {_CREDENTIAL}"],
        })
        response = await kernel.handleRSGI(scope, _StubRsgiProtocol())
        data = msgspec.json.decode(response.getBody())
        self.assertEqual(data["identifier"], 7)
        self.assertEqual(data["guard"], "token")
        self.assertEqual(identities.calls, [7])
        self.assertEqual(tokens.touches, [1])
        self.assertEqual(catch.handled, [])

    async def testOptionsDoesNotResolveAnIdentity(self) -> None:
        """Protocol introspection returns before any authentication storage access."""
        kernel, identities, tokens, catch = await boot_auth_kernel()
        response = await dispatch(kernel, "/api/public", "OPTIONS", [
            (b"authorization", f"Bearer {_CREDENTIAL}".encode()),
        ])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(identities.calls, [])
        self.assertEqual(tokens.lookups, [])
        self.assertEqual(catch.handled, [])

    def testViewRegistrationDoesNotSpecialCaseRootAuthentication(self) -> None:
        """View paths rely on the same kernel policy as controller routes."""
        router = make_router()
        for path in ("/", "/about"):
            route = router.view(path, "welcome")
            self.assertEqual(route.export()["middleware"], [])

    async def testProtectedRoutesStillRejectGuests(self) -> None:
        """Authentication and guest-only rules remain explicit route decisions."""
        kernel, identities, tokens, catch = await boot_auth_kernel()
        response = await dispatch(kernel, "/private")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.getHeader("location"), ["/login"])
        self.assertEqual((await dispatch(kernel, "/login")).status_code, 200)
        await dispatch(kernel, "/api/private")
        await dispatch(kernel, "/api/generic")
        self.assertEqual(len(catch.handled), 2)
        for error in catch.handled:
            self.assertIsInstance(error, AuthenticationException)
        self.assertEqual(identities.calls, [])
        self.assertEqual(tokens.lookups, [])

    async def testCsrfRejectsBeforeIdentityLookup(self) -> None:
        """Reject an unsafe web request before querying its identity provider."""
        kernel, identities, _tokens, catch = await boot_auth_kernel(csrf_enabled=True)
        headers = [(b"x-session-identity", b"7")]
        await dispatch(kernel, "/public", "POST", headers)
        self.assertIsInstance(catch.handled[0], CSRFTokenMismatchException)
        self.assertEqual(identities.calls, [])
        headers.append((b"x-csrf-token", _CSRF.encode()))
        response = await dispatch(kernel, "/public", "POST", headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(identities.calls, ["7"])

    async def testConcurrentRequestsNeverShareIdentity(self) -> None:
        """Shared middleware instances keep identity state in kernel-owned scopes."""
        kernel, _identities, _tokens, catch = await boot_auth_kernel()
        original = current_auth_context()
        responses = await asyncio.gather(*(
            dispatch(kernel, "/public", headers=[(b"x-session-identity", identifier)])
            for identifier in (b"7", b"8", b"") * 5
        ))
        self.assertEqual(
            [
                msgspec.json.decode(response.getBody())["identifier"]
                for response in responses
            ],
            [7, 8, None] * 5,
        )
        self.assertIs(current_auth_context(), original)
        self.assertEqual(catch.handled, [])
