from typing import ClassVar
import msgspec
from orionis.auth.exceptions import AuthenticationException
from orionis.http.adapters.response.asgi import ASGIResponseAdapter
from orionis.http.adapters.response.rsgi import RSGIResponseAdapter
from orionis.http.middleware import BaseMiddleware
from orionis.http.responses import HTMLResponse, RedirectResponse
from orionis.http.routes.fluent import FluentRoute
from orionis.http.routes.route_compiler import RouteCompiler
from orionis.mcp.config import McpConfig
from orionis.mcp.transport.policy import McpHttpPolicy, McpProtocolResponse
from orionis.test import TestCase
from tests.http.test_kernel import (
    _StubRsgiHeaders,
    _StubRsgiScope,
    boot_kernel,
    make_asgi_scope,
    receive_empty,
)

class _Reporter:
    """Observe reporting while never constructing HTML error presentation."""

    __slots__ = ("reported",)

    def __init__(self) -> None:
        """Start with no reported failures.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        self.reported = []

    async def getExceptionHandler(self):
        """Return a reporting-only exception handler double.

        Returns
        -------
        object
            Return the result produced by ``getExceptionHandler``.
        """
        return self

    async def call(self, _handler, method, **arguments: object):
        """Record native report invocations without formatting client output.

        Parameters
        ----------
        _handler : object
            Value supplied for ``_handler``.
        method : object
            Value supplied for ``method``.
        **arguments : object
            Value supplied for ``arguments``.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        if method != "report":
            message = "The HTML exception presenter must not run"
            raise AssertionError(message)
        self.reported.append(arguments["exception"])

class _Policy(McpHttpPolicy):
    """Supply concrete dependencies to the existing kernel test application."""

    __slots__ = ()

    def __init__(self) -> None:
        """Allow exactly one browser origin.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        super().__init__(
            _Reporter(),
            McpConfig(allowed_origins=("https://trusted.test",)),
        )

class _Controller:
    """Expose the same policy marker as the native MCP controller."""

    __slots__ = ()
    http_protocol_policy: ClassVar[type[_Policy]] = _Policy

    def handle(self):
        """Return a response already framed by the MCP protocol dispatcher.

        Returns
        -------
        McpProtocolResponse
            Return the result produced by ``handle``.
        """
        return McpProtocolResponse(
            content=b'{"jsonrpc":"2.0","id":1,"result":{"resultType":"complete"}}',
            media_type="application/json",
        )

class _OrdinaryController:
    """Keep a neighboring ordinary HTTP route outside the endpoint policy."""

    __slots__ = ()

    def handle(self):
        """Return ordinary HTML unchanged.

        Returns
        -------
        HTMLResponse
            Return the result produced by ``handle``.
        """
        return HTMLResponse(content="<p>ordinary</p>")

class _AuthMiddleware(BaseMiddleware):
    """Raise authentication failure from inside the ordinary route pipeline."""

    __slots__ = ()

    async def handle(self, _request, _call_next):
        """Include private details that must never reach protocol clients.

        Parameters
        ----------
        _request : object
            Value supplied for ``_request``.
        _call_next : object
            Value supplied for ``_call_next``.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        message = "private credential details"
        raise AuthenticationException(message)

class _RedirectMiddleware(BaseMiddleware):
    """Simulate an application browser-login redirect attached by mistake."""

    __slots__ = ()

    async def handle(self, _request, _call_next):
        """Return a real native redirect response.

        Parameters
        ----------
        _request : object
            Value supplied for ``_request``.
        _call_next : object
            Value supplied for ``_call_next``.

        Returns
        -------
        RedirectResponse
            Return the result produced by ``handle``.
        """
        return RedirectResponse("/login")

class _LimitMiddleware(BaseMiddleware):
    """Provide a native rejection whose important headers must survive."""

    __slots__ = ()

    async def handle(self, _request, _call_next):
        """Return an HTML rate limit rejection with a retry hint.

        Parameters
        ----------
        _request : object
            Value supplied for ``_request``.
        _call_next : object
            Value supplied for ``_call_next``.

        Returns
        -------
        HTMLResponse
            Return the result produced by ``handle``.
        """
        return HTMLResponse(
            content="<p>private implementation details</p>",
            status_code=429,
            headers={"Retry-After": "12", "X-Content-Type-Options": "nosniff"},
        )

class _Protocol:
    """Capture actual RSGI response-adapter output."""

    __slots__ = ("result",)

    def __init__(self) -> None:
        """Store the single response emitted for one request.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        self.result = None

    def response_bytes(self, status, headers, body):
        """Record the complete native RSGI response.

        Parameters
        ----------
        status : object
            Value supplied for ``status``.
        headers : object
            Value supplied for ``headers``.
        body : object
            Value supplied for ``body``.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        self.result = status, dict(headers), body

    def response_empty(self, status, headers):
        """Record an empty native RSGI response.

        Parameters
        ----------
        status : object
            Value supplied for ``status``.
        headers : object
            Value supplied for ``headers``.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        self.response_bytes(status, headers, b"")

class TestKernelPolicy(TestCase):
    """Keep native HTTP semantics while forcing protocol-safe MCP boundaries."""

    async def kernel(self, middleware=None, **options: object):
        """Boot the actual resolver and middleware with a marked static controller.

        Parameters
        ----------
        middleware : object
            Value supplied for ``middleware``.
        **options : object
            Value supplied for ``options``.

        Returns
        -------
        object
            Return the result produced by ``kernel``.
        """
        route = FluentRoute("POST", "/mcp", [_Controller, "handle"])._kind("api")
        if middleware is not None:
            route.middleware(middleware)
        ordinary = FluentRoute("GET", "/ordinary", [_OrdinaryController, "handle"])
        routes, _ = RouteCompiler().compile(
            [route.export(), ordinary.export()],
            None,
            [],
        )
        kernel, app, _, catch = await boot_kernel(routes=routes, **options)
        kernel._KernelHTTP__asgi_adapter = ASGIResponseAdapter()
        kernel._KernelHTTP__rsgi_adapter = RSGIResponseAdapter()
        return kernel, app, catch

    async def request(self, kernel, interface, *, path="/mcp", method="POST", extra=()):
        """Drive the same native kernel through ASGI or RSGI using browser Accept.

        Parameters
        ----------
        kernel : object
            Value supplied for ``kernel``.
        interface : object
            Value supplied for ``interface``.
        path : object
            Value supplied for ``path``.
        method : object
            Value supplied for ``method``.
        extra : object
            Value supplied for ``extra``.

        Returns
        -------
        object
            Return the result produced by ``request``.
        """
        headers = [("host", "orionis.test"), ("accept", "text/html"), *extra]
        if interface == "rsgi":
            scope = _StubRsgiScope(path, method)
            grouped = {}
            for name, value in headers:
                grouped.setdefault(name, []).append(value)
            scope.headers = _StubRsgiHeaders(grouped)
            protocol = _Protocol()
            await kernel.handleRSGI(scope, protocol)
            return protocol.result
        sent = []

        async def send(message):
            """Record response messages sent by the transport.

            Parameters
            ----------
            message : object
                Value supplied for ``message``.

            Returns
            -------
            None
                Complete the documented checks or setup without a return value.
            """
            sent.append(message)

        await kernel.handleASGI(
            make_asgi_scope(
                path,
                method,
                [(key.encode(), value.encode()) for key, value in headers],
            ),
            receive_empty,
            send,
        )
        return (
            sent[0]["status"],
            {key.decode(): value.decode() for key, value in sent[0]["headers"]},
            b"".join(message.get("body", b"") for message in sent),
        )

    def assertProtocolError(self, result, status):
        """Require sanitized JSON-RPC without a fabricated request ID.

        Parameters
        ----------
        result : object
            Value supplied for ``result``.
        status : object
            Value supplied for ``status``.

        Returns
        -------
        object
            Return the result produced by ``assertProtocolError``.
        """
        actual, headers, body = result
        self.assertEqual(actual, status)
        self.assertIn("application/json", headers["content-type"])
        message = msgspec.json.decode(body)
        self.assertEqual(message["jsonrpc"], "2.0")
        self.assertIn("error", message)
        self.assertNotIn("id", message)
        self.assertNotIn(b"private", body)
        return headers

    async def test_origins_precede_global_and_route_work_for_every_method(self):
        """Invalid origins are rejected even during maintenance and OPTIONS.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        kernel, app, _ = await self.kernel(maintenance=True)
        for interface in ("asgi", "rsgi"):
            for method in ("POST", "GET", "DELETE", "OPTIONS"):
                result = await self.request(
                    kernel,
                    interface,
                    method=method,
                    extra=(("origin", "https://evil.test"),),
                )
                self.assertProtocolError(result, 403)
        self.assertEqual(app.scopes, [])

    async def test_native_method_options_and_unrelated_route_behavior(self):
        """Let routing return 405/OPTIONS while keeping neighboring HTML untouched.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        kernel, _, catch = await self.kernel()
        for interface in ("asgi", "rsgi"):
            for method in ("GET", "DELETE"):
                headers = self.assertProtocolError(
                    await self.request(kernel, interface, method=method),
                    405,
                )
                self.assertEqual(headers["allow"], "POST")
            status, _, body = await self.request(kernel, interface, method="OPTIONS")
            self.assertEqual((status, body), (200, b""))
            status, _, body = await self.request(
                kernel,
                interface,
                path="/ordinary",
                method="GET",
            )
            self.assertEqual((status, body), (200, b"<p>ordinary</p>"))
        self.assertEqual(catch.handled, [])

    async def test_native_auth_failure_reports_without_html_in_debug_mode(self):
        """Preserve Bearer authentication status even when browsers request HTML.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        kernel, _, catch = await self.kernel(_AuthMiddleware, debug=True)
        for interface in ("asgi", "rsgi"):
            headers = self.assertProtocolError(
                await self.request(kernel, interface),
                401,
            )
            self.assertEqual(headers["www-authenticate"], "Bearer")
        policy = kernel._KernelHTTP__endpoint_policies["/mcp"]
        self.assertEqual(len(policy._app.reported), 2)
        self.assertEqual(catch.handled, [])

    async def test_redirects_and_shared_rejections_are_protocol_safe(self):
        """Replace browser redirects and preserve retry/security headers on errors.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        for interface in ("asgi", "rsgi"):
            kernel, _, _ = await self.kernel(_RedirectMiddleware)
            headers = self.assertProtocolError(
                await self.request(kernel, interface),
                403,
            )
            self.assertNotIn("location", headers)
            kernel, _, _ = await self.kernel(_LimitMiddleware)
            headers = self.assertProtocolError(
                await self.request(kernel, interface),
                429,
            )
            self.assertEqual(headers["retry-after"], "12")
            self.assertEqual(headers["x-content-type-options"], "nosniff")
            kernel, _, _ = await self.kernel(maintenance=True)
            self.assertProtocolError(await self.request(kernel, interface), 503)

    async def test_body_framing_failures_keep_native_status_and_protocol_body(self):
        """Sanitize global errors that happen before the MCP controller sees a body.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        kernel, _, _ = await self.kernel()
        for interface in ("asgi", "rsgi"):
            self.assertProtocolError(
                await self.request(
                    kernel,
                    interface,
                    extra=(("content-length", "invalid"),),
                ),
                400,
            )
            self.assertProtocolError(
                await self.request(
                    kernel,
                    interface,
                    extra=(("content-length", "999999999999999999999"),),
                ),
                413,
            )
