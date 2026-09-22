import asyncio
from pathlib import Path
from typing import ClassVar
from types import SimpleNamespace
import msgspec
from orionis.auth.contracts.context import IAuthenticationContext
from orionis.auth.contracts.manager import IAuthManager
from orionis.auth.contracts.permission_repository import IPermissionRepository
from orionis.auth.exceptions import AuthenticationException, AuthorizationException
from orionis.auth.middleware.authenticate import (
    AuthenticateSessionMiddleware,
    AuthenticateTokenMiddleware,
)
from orionis.auth.middleware.authorize import RequirePermissionMiddleware
from orionis.console.output.http_request import HTTPRequestPrinter
from orionis.container.container import Container
from orionis.container.context.manager import ScopeManager
from orionis.container.context.scope import ScopedContext
from orionis.failure.base.handler import BaseExceptionHandler
from orionis.http.adapters.response.asgi import ASGIResponseAdapter
from orionis.http.adapters.response.rsgi import RSGIResponseAdapter
from orionis.http.default.responses import DefaultResponses
from orionis.http.kernel import KernelHTTP
from orionis.http.layer.web.start_session import StartSessionMiddleware
from orionis.http.responses import Response
from orionis.http.routes.entities.compiled_route import CompiledRoute
from orionis.http.routes.enums.route_types import RouteType
from orionis.http.routes.loader import RouteLoader
from orionis.session.manager import SessionManager
from orionis.session.session import Session
from orionis.support.facades.session import Session as SessionFacade
from tests.auth import test_manager as auth_fixtures
from tests.http import test_kernel as http_fixtures
from tests.session import test_manager as session_fixtures

# ruff: noqa: TC001


class _CanView(RequirePermissionMiddleware):
    """Require the capability exercised by protected integration routes."""

    __slots__ = ()
    permissions: ClassVar[tuple[str, ...]] = ("users.view",)

class _ExpiredIdentity(AuthenticationException):
    """Represent an application-specific authentication failure."""

class _DeniedOperation(AuthorizationException):
    """Represent an application-specific authorization denial."""


class _Rendezvous:
    """Force two requests to interleave inside their real controller."""

    __slots__ = ("barrier",)

    def __init__(self) -> None:
        """Create a two-party barrier for one concurrent request pair."""
        self.barrier = asyncio.Barrier(2)


async def identity_handler(
    auth: IAuthManager,
    context: IAuthenticationContext,
) -> dict[str, object]:
    """Return the identity and authorization injected into a real route handler."""
    return {
        "identity": auth.identifier(),
        "injected": context.identifier(),
        "guard": context.guard,
        "credential": context.credentialId,
        "allowed": await auth.can("users.view"),
    }


async def concurrent_handler(
    auth: IAuthManager,
    rendezvous: _Rendezvous,
    context: IAuthenticationContext,
) -> dict[str, object]:
    """Observe Auth across a deterministic interleaving with another request."""
    before = auth.identifier()
    await rendezvous.barrier.wait()
    payload = await identity_handler(auth, context)
    payload["before"] = before
    await rendezvous.barrier.wait()
    payload["after"] = auth.identifier()
    return payload


async def logout_handler(auth: IAuthManager) -> Response:
    """Invalidate the current web session from a kernel-dispatched handler."""
    await auth.logout()
    return Response(status_code=204)


class _HttpApp(auth_fixtures._StubApp):
    """Supply isolated services while delegating invocation to the real container."""

    __slots__ = ("basePath", "builds", "container", "scopes")

    def __init__(self, directory: Path) -> None:
        """Configure web middleware without external services."""
        super().__init__(str(directory / "unused.sqlite"))
        self.basePath = directory
        self._tree["http"] = http_fixtures.make_http_config(csrf_enabled=True)
        self._tree["session"] = session_fixtures._make_config()
        self.container = type("HttpTestContainer", (Container,), {})()
        self.builds: dict[type, object] = {}
        self.scopes: list[ScopeManager] = []

    async def build(self, target: type) -> object:
        """Return prebuilt infrastructure or use actual constructor injection."""
        if target in self.builds:
            return self.builds[target]
        return await self.container.build(target)

    async def invoke(self, target: object, **kwargs: object) -> object:
        """Invoke the handler with the real container and current Request binding."""
        return await self.container.invoke(target, **kwargs)

    def instance(self, abstract: type, instance: object) -> bool:
        """Register Session in the active request scope using the real container."""
        return self.container.instance(abstract, instance)

    def beginScope(self) -> ScopeManager:
        """Create and record a real scope for each HTTP request."""
        scope = self.container.beginScope()
        self.scopes.append(scope)
        return scope

    def isDebug(self) -> bool:
        """Disable console request output in the isolated integration runtime."""
        return False

    def underMaintenance(self) -> bool:
        """Allow requests through the normal kernel lifecycle."""
        return False


class _HttpCatch:
    """Use the real exception status mapping without writing application logs."""

    __slots__ = ("handler",)

    def __init__(self, responses: object) -> None:
        """Build the standard exception handler."""
        self.handler = BaseExceptionHandler(responses)

    async def exception(self, exc: Exception, request: object) -> Response:
        """Delegate error classification to Orionis."""
        return await self.handler.handleHTTP(exc, request)


class _RsgiProtocol:
    """Record bytes emitted by the real RSGI response adapter."""

    __slots__ = ("body", "headers", "status")

    def __init__(self) -> None:
        """Start without a response."""
        self.status = 0
        self.headers: list[tuple[str, str]] = []
        self.body = b""

    def response_bytes(
        self, status: int, headers: list[tuple[str, str]], body: bytes,
    ) -> None:
        """Record the protocol response supplied by the adapter."""
        self.status, self.headers, self.body = status, headers, body


def route(path: str, function: str, *, web: bool = False) -> CompiledRoute:
    """Build a route descriptor using native middleware classes."""
    guard = AuthenticateSessionMiddleware if web else AuthenticateTokenMiddleware
    middleware = (guard,) if path == "/logout" else (guard, _CanView)
    if path == "/public":
        middleware = ()
    return CompiledRoute(
        path=path,
        method="POST" if path == "/logout" else "GET",
        type=RouteType.FUNCTION,
        action={"module": __name__, "function": function},
        name=None,
        regex=None,
        segment_count=1,
        kind="web" if web else "api",
        compiled_middlewares=middleware,
    )


class TestAuthHttpIntegration(auth_fixtures._ManagerCase):
    """Exercise request identity through the actual HTTP kernel and transports."""

    def setUp(self) -> None:
        """Detach from the test runner's ambient container scope."""
        self._scope_token = ScopedContext.setCurrentScope(None)

    def tearDown(self) -> None:
        """Restore the runner's context after the isolated HTTP runtime."""
        ScopedContext.reset(self._scope_token)

    async def asyncSetUp(self) -> None:
        """Boot a real kernel over the existing temporary Auth database fixtures."""
        await super().asyncSetUp()
        self.http_app = _HttpApp(Path(self._tmp.name))
        self.http_app.instance(IAuthManager, self.auth)
        self.http_app.instance(IPermissionRepository, self.permissions)
        self.http_app.instance(_Rendezvous, _Rendezvous())
        self.responses = http_fixtures._StubDefaultResponses()
        self.catch = _HttpCatch(self.responses)
        self.sessions = SessionManager(self.http_app, object())
        routes = {
            "GET": {"static": {
                "/api": route("/api", "identity_handler"),
                "/concurrent": route("/concurrent", "concurrent_handler"),
                "/web": route("/web", "identity_handler", web=True),
                "/public": route("/public", "identity_handler", web=True),
            }, "dynamic": []},
            "POST": {"static": {
                "/logout": route("/logout", "logout_handler", web=True),
            }, "dynamic": []},
        }
        self.http_app.builds = {
            RouteLoader: http_fixtures._StubRouteLoader(routes, None),
            DefaultResponses: self.responses,
            HTTPRequestPrinter: http_fixtures._StubRequestPrinter(),
            StartSessionMiddleware: StartSessionMiddleware(self.sessions, self.catch),
            ASGIResponseAdapter: ASGIResponseAdapter(),
            RSGIResponseAdapter: RSGIResponseAdapter(),
            AuthenticateSessionMiddleware: AuthenticateSessionMiddleware(
                self.app, self.auth, self.permissions,
            ),
            AuthenticateTokenMiddleware: AuthenticateTokenMiddleware(
                self.app, self.auth, self.permissions,
            ),
            _CanView: _CanView(self.authorizer),
        }
        self.kernel = KernelHTTP(self.http_app, self.catch)
        await self.kernel.boot()

    async def asyncTearDown(self) -> None:
        """Dispose the test container and its database after every request scenario."""
        Container._instances.pop(type(self.http_app.container), None)
        await super().asyncTearDown()

    async def asgi(
        self, path: str, headers: list[tuple[bytes, bytes]] | None = None,
        method: str = "GET",
    ) -> tuple[int, dict[str, object], list[tuple[bytes, bytes]]]:
        """Send one ASGI request through the kernel and collect its real response."""
        messages: list[dict] = []

        async def receive() -> dict:
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict) -> None:
            messages.append(message)

        scope = http_fixtures.make_asgi_scope(path, method, headers)
        await self.kernel.handleASGI(scope, receive, send)
        start = messages[0]
        body = b"".join(item.get("body", b"") for item in messages[1:])
        payload = msgspec.json.decode(body) if body else {}
        self.assertTrue(self.auth.guest())
        return start["status"], payload, start["headers"]

    async def testAsgiDistinguishesUnauthorizedAndForbidden(self) -> None:
        """Send guests to 401 and known identities without rights to 403."""
        status, _, headers = await self.asgi("/api")
        self.assertEqual(status, 401)
        self.assertIn((b"www-authenticate", b"Bearer"), headers)
        issued = await self.tokens.create(self.ada, "api")
        headers = [(b"authorization", f"Bearer {issued.plain_text}".encode())]
        status, _, _ = await self.asgi("/api", headers)
        self.assertEqual(status, 403)
        await self.registrar.givePermissionTo(self.ada, "users.view")
        status, payload, _ = await self.asgi("/api", headers)
        self.assertEqual(status, 200)
        self.assertEqual(payload["identity"], self.ada.id)
        self.assertEqual(payload["injected"], self.ada.id)
        self.assertTrue(self.auth.guest())

    async def testConcurrentAsgiRequestsKeepTheirInjectedIdentity(self) -> None:
        """Interleave two real API requests through shared middleware and services."""
        await self.registrar.givePermissionTo(self.ada, "users.view")
        await self.registrar.givePermissionTo(self.bob, "users.view")
        first = await self.tokens.create(self.ada, "first")
        second = await self.tokens.create(self.bob, "second")
        responses = await asyncio.gather(*(
            self.asgi("/concurrent", [
                (b"authorization", f"Bearer {issued.plain_text}".encode()),
            ]) for issued in (first, second)
        ))
        self.assertTrue(all(not scope.isActive for scope in self.http_app.scopes))
        for response, identity in zip(responses, (self.ada, self.bob), strict=True):
            status, payload, _ = response
            self.assertEqual(status, 200)
            self.assertEqual(
                [payload[key] for key in ("before", "identity", "injected", "after")],
                [identity.id] * 4,
            )

    async def testWebSessionAndCsrfLogoutUseTheKernelLifecycle(self) -> None:
        """Restore a session, authorize, validate CSRF, log out and reject replay."""
        await self.registrar.givePermissionTo(self.ada, "users.view")
        session = Session()
        session.put("_auth_identifier", str(self.ada.id))
        csrf = "existing-csrf-value"
        session.put("_csrf_token", csrf)
        await self.sessions.save(Response(), session)
        headers = [(b"cookie", f"sessionid={session.id}".encode())]
        status, payload, _ = await self.asgi("/web", headers)
        self.assertEqual(status, 200)
        self.assertEqual(payload["identity"], self.ada.id)
        status, _, _ = await self.asgi("/logout", headers, "POST")
        self.assertEqual(status, 419)
        status, _, _ = await self.asgi(
            "/logout", [*headers, (b"x-csrf-token", csrf.encode())], "POST",
        )
        self.assertEqual(status, 204)
        self.assertIsNone(await self.sessions._store.read(session.id))
        status, _, _ = await self.asgi("/web", headers)
        self.assertEqual(status, 401)
        with self.assertRaises(RuntimeError):
            SessionFacade.get("_auth_identifier")

    async def testRsgiUsesTheSameAuthenticationAndAuthorization(self) -> None:
        """Exercise the real RSGI adapters and the same token middleware pipeline."""
        await self.registrar.givePermissionTo(self.ada, "users.view")
        issued = await self.tokens.create(self.ada, "rsgi")
        scope = http_fixtures._StubRsgiScope("/api")
        scope.headers = http_fixtures._StubRsgiHeaders({
            "host": ["orionis.test"],
            "authorization": [f"Bearer {issued.plain_text}"],
        })
        protocol = _RsgiProtocol()
        await self.kernel.handleRSGI(scope, protocol)
        self.assertEqual(protocol.status, 200)
        self.assertEqual(msgspec.json.decode(protocol.body)["identity"], self.ada.id)
        self.assertTrue(self.auth.guest())
        self.assertTrue(all(not scope.isActive for scope in self.http_app.scopes))

    async def testCustomAuthExceptionsKeepTheirHttpSemantics(self) -> None:
        """Classify application subclasses as 401 or 403 rather than generic 500."""
        request = SimpleNamespace(wantsJson=lambda: True)
        for exception, expected in (
            (_ExpiredIdentity("expired"), 401),
            (_DeniedOperation("denied"), 403),
        ):
            response = await self.catch.exception(exception, request)
            self.assertEqual(response.getStatusCode(), expected)

    async def testBearerHeadersAreUnambiguousAndCaseInsensitive(self) -> None:
        """Accept case-insensitive schemes and reject duplicate credentials."""
        await self.registrar.givePermissionTo(self.ada, "users.view")
        issued = await self.tokens.create(self.ada, "header-check")
        value = f"bEaReR {issued.plain_text}".encode()
        status, _, _ = await self.asgi("/api", [(b"authorization", value)])
        self.assertEqual(status, 200)
        status, _, _ = await self.asgi("/api", [
            (b"authorization", b"Basic ignored"),
            (b"authorization", value),
        ])
        self.assertEqual(status, 401)
