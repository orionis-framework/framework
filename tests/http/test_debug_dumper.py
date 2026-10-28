from __future__ import annotations
import asyncio
import inspect
import os
import sys
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, replace
from html import escape
from io import StringIO
from typing import TYPE_CHECKING
from orionis.console.debug.dumper import Dumper, HttpDump
from orionis.console.output.var_dumper import VarDumper
from orionis.container.container import Container
from orionis.container.context.manager import ScopeManager
from orionis.container.context.scope import ScopedContext
from orionis.failure.enums.kernel_type import KernelContext
from orionis.http.adapters.response.asgi import ASGIResponseAdapter
from orionis.http.middleware import BaseMiddleware
from orionis.http.request import Request
from orionis.http.responses import HTMLResponse, Response
from orionis.session.manager import SessionManager
from orionis.test import TestCase
from tests.http.layer.web.test_session_persistence import _make_middleware
from tests.http.test_kernel import (
    _StubApp,
    _StubCatch,
    _StubDefaultResponses,
    _StubRsgiProtocol,
    _StubRsgiScope,
    _StubResponseAdapter,
    boot_kernel,
    dispatch,
    make_asgi_scope,
    make_route,
    make_routes,
    receive_empty,
)
from tests.http.test_support import replace_attribute

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Never
    from orionis.http.kernel import KernelHTTP
    from orionis.session.session import Session

@dataclass(slots=True)
class _UnexpectedCall:
    """Record forbidden collaborator calls and fail immediately."""

    message: str
    calls: int = 0

    def __call__(self, *_args: object, **_kwargs: object) -> Never:
        """
        Count an unexpected invocation before raising its assertion failure.

        Parameters
        ----------
        *_args : object
            Unused positional arguments supplied by the caller.
        **_kwargs : object
            Unused keyword arguments supplied by the caller.

        Raises
        ------
        AssertionError
            Always raised because the collaborator must not be invoked.
        """
        self.calls += 1
        raise AssertionError(self.message)

def _dump_path(path: str) -> Response:
    """
    Interrupt HTTP dispatch with a dump containing the request path.

    Parameters
    ----------
    path : str
        Request path used as the request-local isolation marker.

    Returns
    -------
    Response
        Never returned because dumping must interrupt the handler.

    Raises
    ------
    HttpDump
        If debug HTTP dispatch permits capturing a dump.
    RuntimeError
        If HTTP dumping is disabled or dispatch has already completed.
    AssertionError
        If execution unexpectedly continues after dumping.
    """
    Dumper.dd(
        {"path": path, "value": "<script>alert('dump')</script>"},
        show_types=True,
        show_index=True,
        redirect_output=True,
        insert_line=True,
    )
    error_msg = "Execution continued after Dumper.dd()."
    raise AssertionError(error_msg)

def dump_handler(request: Request) -> Response:
    """
    Dump the current path from an injected HTTP request.

    Parameters
    ----------
    request : Request
        Injected request supplying the path marker.

    Returns
    -------
    Response
        Never returned because dumping interrupts request handling.
    """
    return _dump_path(request.path)

def dump_fallback() -> Response:
    """
    Dump a missing-route marker before a typed request exists.

    Returns
    -------
    Response
        Never returned because dumping interrupts fallback handling.
    """
    return _dump_path("/missing")

class _DumpController:
    """Exercise synchronous and asynchronous controller actions."""

    def show(self, request: Request) -> Response:
        """
        Dump the request path from a synchronous controller action.

        Parameters
        ----------
        request : Request
            Injected request supplying the path marker.

        Returns
        -------
        Response
            Never returned because dumping interrupts the action.
        """
        return dump_handler(request)

    async def showAsync(self, request: Request) -> Response:
        """
        Yield once before dumping the request path in an async action.

        Parameters
        ----------
        request : Request
            Injected request supplying the path marker.

        Returns
        -------
        Response
            Never returned because dumping interrupts the action.
        """
        await asyncio.sleep(0)
        return dump_handler(request)

    def continueDump(self, request: Request) -> Response:
        """
        Print the request path and return the normal HTTP response.

        Parameters
        ----------
        request : Request
            Injected request supplying the path marker.

        Returns
        -------
        Response
            Response containing ``'continued'`` after console output.
        """
        Dumper.dump({"path": request.path})
        return Response(content="continued")

    def showFrozen(self) -> Response:
        """
        Capture a dump snapshot before ``finally`` mutates the input.

        Returns
        -------
        Response
            Never returned because dumping interrupts the action.

        Raises
        ------
        HttpDump
            If HTTP dumping captures the value before cleanup.
        AssertionError
            If execution unexpectedly continues after dumping.
        """
        data = {"snapshot": "before-finally"}
        try:
            Dumper.dd(data)
        finally:
            data["snapshot"] = "after-finally"
        error_msg = "Execution continued after Dumper.dd()."
        raise AssertionError(error_msg)

class _DumpMiddleware(BaseMiddleware):
    """Exercise dumping before the route handler is invoked."""

    async def handle(self, request: Request, _call_next: object) -> Response:
        """
        Interrupt HTTP dispatch before invoking the next middleware handler.

        Parameters
        ----------
        request : Request
            Current request supplying the path marker.
        _call_next : object
            Unused continuation that dumping prevents from running.

        Returns
        -------
        Response
            Never returned because dumping interrupts the middleware.
        """
        return dump_handler(request)

class TestHttpDebugDumper(TestCase):
    """Use real container invocation and scopes with the kernel fixtures."""

    async def _boot(
        self,
        *,
        debug: bool = True,
        fallback: tuple | None = None,
    ) -> tuple[KernelHTTP, _StubApp, _StubCatch]:
        """
        Boot dump routes with exit guards and real scoped container calls.

        Parameters
        ----------
        debug : bool, optional
            Enable HTTP dump rendering; defaults to ``True``.
        fallback : tuple | None, optional
            Fallback handler specification; defaults to ``None``.

        Returns
        -------
        tuple[KernelHTTP, _StubApp, _StubCatch]
            Booted kernel, application stub, and exception handler stub.
        """
        self.sys_exit = _UnexpectedCall("sys.exit was called")
        self.os_exit = _UnexpectedCall("os._exit was called")
        self.enterContext(replace_attribute(sys, "exit", self.sys_exit))
        self.enterContext(replace_attribute(os, "_exit", self.os_exit))
        self.enterContext(
            replace_attribute(
                _StubApp, "beginScope", staticmethod(ScopeManager),
            ),
        )
        container = Container()
        self.enterContext(
            replace_attribute(
                _StubApp, "invoke", staticmethod(container.invoke),
            ),
        )
        self.enterContext(
            replace_attribute(_StubApp, "call", staticmethod(container.call)),
        )
        routes = make_routes()
        for path, method, kind in (
            ("/dump", "show", "api"),
            ("/async-dump", "showAsync", "api"),
            ("/other-dump", "showAsync", "api"),
            ("/web-dump", "show", "web"),
            ("/continue-dump", "continueDump", "api"),
            ("/frozen-dump", "showFrozen", "api"),
        ):
            routes["GET"]["static"][path] = replace(
                make_route(path, controller="_DumpController", kind=kind),
                action={
                    "module": __name__,
                    "class": "_DumpController",
                    "method": method,
                },
            )
        routes["GET"]["static"]["/function-dump"] = replace(
            make_route("/function-dump", function="dump_handler"),
            action={"module": __name__, "function": "dump_handler"},
        )
        routes["GET"]["static"]["/middleware-dump"] = make_route(
            "/middleware-dump",
            function="api_handler",
            middlewares=(_DumpMiddleware,),
        )
        kernel, app, _responses, catch = await boot_kernel(
            routes=routes, debug=debug, fallback=fallback,
        )
        return kernel, app, catch

    def _assertDump(self, response: Response, path: str) -> None:
        """
        Verify HTML dump content, source location, and absence of exits.

        Parameters
        ----------
        response : Response
            Dispatched response expected to contain an HTML dump.
        path : str
            Request-local path marker expected in the dump.

        Returns
        -------
        None
            Complete the response, caller-location, and exit-guard assertions.
        """
        self.assertIsInstance(response, HTMLResponse)
        self.assertEqual(response.getStatusCode(), 200)
        self.assertEqual(
            response.getHeader("content-type"), ["text/html; charset=utf-8"],
        )
        self.assertEqual(response.getHeader("cache-control"), ["no-store"])
        body = response.getBody().decode()
        self.assertIn(path, body)
        self.assertIn("dict", body)
        self.assertIn("#1", body)
        self.assertIn("&lt;script&gt;", body)
        self.assertNotIn("<script>", body)
        source_lines, first_line = inspect.getsourcelines(_dump_path)
        call_line = first_line + next(
            index for index, line in enumerate(source_lines)
            if line.lstrip().startswith("Dumper.dd(")
        )
        filename = escape(_dump_path.__code__.co_filename)
        self.assertIn(f">{filename}:{call_line}</span>", body)
        self.assertNotIn(">Python</span>", body)
        self.assertEqual(self.sys_exit.calls, 0)
        self.assertEqual(self.os_exit.calls, 0)

    async def testHttpDumpPreservesExplicitSourceOverrides(self) -> None:
        """
        Verify that HTTP dumps preserve explicit source-location overrides.

        Returns
        -------
        None
            This test does not return a value.
        """
        async with ScopeManager() as scope:
            scope["kernel"] = KernelContext.HTTP
            with self.assertRaises(HttpDump) as captured:
                Dumper.dd(
                    "custom-location", module_path="custom.py", line_number=42,
                )

        html = captured.exception.dumper.toHtml()
        self.assertIn(">custom.py:42</span>", html)

    async def testControllerDumpReturnsHtmlWithoutStoppingTheServer(self) -> None:
        """
        Verify that controller dumps return HTML without stopping the server.

        Returns
        -------
        None
            This test does not return a value.
        """
        kernel, _app, catch = await self._boot()
        previous_scope = ScopedContext.getCurrentScope()
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            response = await dispatch(kernel, "/dump")
            normal_response = await dispatch(kernel, "/api")

        self._assertDump(response, "/dump")
        self.assertEqual(normal_response.getBody(), b"api")
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(catch.handled, [])
        self.assertIs(ScopedContext.getCurrentScope(), previous_scope)

    async def testSupportsWebFunctionsAndMiddleware(self) -> None:
        """
        Verify dumps across web routes, function handlers, and middleware.

        Returns
        -------
        None
            This test does not return a value.
        """
        kernel, _app, catch = await self._boot()
        for path in ("/web-dump", "/function-dump", "/middleware-dump"):
            with self.subTest(path=path):
                response = await dispatch(kernel, path)
                self._assertDump(response, path)
        self.assertEqual(catch.handled, [])

    async def testRealSessionMiddlewareLeavesDumpsForTheKernel(self) -> None:
        """
        Verify session aborts and kernel dump handling on both transports.

        Returns
        -------
        None
            This test does not return a value.
        """
        session_calls: list[str] = []
        abort_session = SessionManager.abort
        save_session = SessionManager.save

        async def abort(manager: SessionManager, session: Session) -> None:
            """
            Record session aborts while preserving the real manager behavior.

            Parameters
            ----------
            manager : SessionManager
                Manager receiving the abort operation.
            session : Session
                Session belonging to the interrupted request.

            Returns
            -------
            None
                Complete the real session abort.
            """
            session_calls.append("abort")
            await abort_session(manager, session)

        async def save(
            manager: SessionManager,
            response: Response,
            session: Session,
        ) -> None:
            """
            Record session saves while preserving the real manager behavior.

            Parameters
            ----------
            manager : SessionManager
                Manager receiving the save operation.
            response : Response
                Response receiving the session cookie.
            session : Session
                Session belonging to the completed request.

            Returns
            -------
            None
                Complete the real session save.
            """
            session_calls.append("save")
            await save_session(manager, response, session)

        for debug in (True, False):
            for interface in ("asgi", "rsgi"):
                with self.subTest(debug=debug, interface=interface):
                    kernel, _app, catch = await self._boot(debug=debug)
                    _manager, middleware, session_catch = _make_middleware()
                    kernel._KernelHTTP__web_middleware = (
                        middleware, *kernel._KernelHTTP__web_middleware[1:],
                    )
                    previous_scope = ScopedContext.getCurrentScope()
                    session_calls.clear()
                    with (
                        replace_attribute(SessionManager, "abort", abort),
                        replace_attribute(SessionManager, "save", save),
                    ):
                        if interface == "asgi":
                            response = await dispatch(kernel, "/web-dump")
                        else:
                            response = await kernel.handleRSGI(
                                _StubRsgiScope("/web-dump"), _StubRsgiProtocol(),
                            )

                    self.assertEqual(session_catch.handled, [])
                    self.assertEqual(session_calls, ["abort"])
                    self.assertIs(
                        ScopedContext.getCurrentScope(), previous_scope,
                    )
                    if debug:
                        self._assertDump(response, "/web-dump")
                        self.assertEqual(catch.handled, [])
                    else:
                        self.assertEqual(response.getStatusCode(), 500)
                        self.assertEqual(len(catch.handled), 1)
                        self.assertIs(type(catch.handled[0]), RuntimeError)
                        self.assertNotIn(b"/web-dump", response.getBody())
                        self.assertEqual(self.sys_exit.calls, 0)
                        self.assertEqual(self.os_exit.calls, 0)

    async def testConcurrentAsyncControllersKeepTheirOwnDump(self) -> None:
        """
        Verify that concurrent controllers isolate dump values and scopes.

        Returns
        -------
        None
            This test does not return a value.
        """
        kernel, _app, catch = await self._boot()
        previous_scope = ScopedContext.getCurrentScope()
        first, second = await asyncio.gather(
            dispatch(kernel, "/async-dump"),
            dispatch(kernel, "/other-dump"),
        )

        self._assertDump(first, "/async-dump")
        self._assertDump(second, "/other-dump")
        self.assertNotIn(b"/other-dump", first.getBody())
        self.assertNotIn(b"/async-dump", second.getBody())
        self.assertEqual(catch.handled, [])
        self.assertIs(ScopedContext.getCurrentScope(), previous_scope)

    async def testRsgiControllerDumpReturnsHtml(self) -> None:
        """
        Verify that RSGI controller dumps produce HTML responses.

        Returns
        -------
        None
            This test does not return a value.
        """
        kernel, _app, catch = await self._boot()
        response = await kernel.handleRSGI(
            _StubRsgiScope("/dump"), _StubRsgiProtocol(),
        )

        self._assertDump(response, "/dump")
        self.assertEqual(catch.handled, [])

    async def testRealAsgiAdapterSendsTheHtmlResponse(self) -> None:
        """
        Verify the ASGI messages emitted by the real response adapter.

        Returns
        -------
        None
            This test does not return a value.
        """
        kernel, _app, catch = await self._boot()
        kernel._KernelHTTP__asgi_adapter = ASGIResponseAdapter()
        messages: list[dict] = []

        async def send(message: dict) -> None:
            """
            Record one ASGI response message.

            Parameters
            ----------
            message : dict
                ASGI response message to append to the captured sequence.

            Returns
            -------
            None
                Append the message without modifying it.
            """
            messages.append(message)

        await kernel.handleASGI(
            make_asgi_scope("/dump"), receive_empty, send,
        )

        self.assertEqual(messages[0]["type"], "http.response.start")
        self.assertEqual(messages[0]["status"], 200)
        headers = dict(messages[0]["headers"])
        self.assertEqual(headers[b"content-type"], b"text/html; charset=utf-8")
        self.assertEqual(headers[b"cache-control"], b"no-store")
        self.assertEqual(messages[1]["type"], "http.response.body")
        self.assertIn(b"/dump", messages[1]["body"])
        self.assertEqual(catch.handled, [])

    async def testDumpStillContinuesWithoutChangingTheHttpResponse(self) -> None:
        """
        Verify that ordinary dumps preserve the normal HTTP response.

        Returns
        -------
        None
            This test does not return a value.
        """
        for debug in (True, False):
            with self.subTest(debug=debug):
                kernel, _app, catch = await self._boot(debug=debug)
                stdout = StringIO()
                with redirect_stdout(stdout):
                    response = await dispatch(kernel, "/continue-dump")

                self.assertEqual(response.getBody(), b"continued")
                self.assertIn("/continue-dump", stdout.getvalue())
                self.assertEqual(catch.handled, [])
                self.assertEqual(self.sys_exit.calls, 0)
                self.assertEqual(self.os_exit.calls, 0)

    async def testDumpIsRejectedOnceResponseSendingBegins(self) -> None:
        """
        Verify that late dumps raise without rendering HTML or exiting.

        Returns
        -------
        None
            This test does not return a value.
        """
        kernel, _app, _catch = await self._boot()
        previous_scope = ScopedContext.getCurrentScope()

        async def send_dump(*_transport: object) -> None:
            """
            Attempt to dump after request dispatch has completed.

            Parameters
            ----------
            *_transport : object
                Unused arguments supplied by the response adapter.

            Returns
            -------
            None
                Never returned because late dumping is rejected.

            Raises
            ------
            RuntimeError
                Always raised because request dispatch has already completed.
            """
            Dumper.dd("late-dump")

        to_html = _UnexpectedCall("HTML rendering was called after dispatch")
        with (
            replace_attribute(_StubResponseAdapter, "send", send_dump),
            replace_attribute(VarDumper, "toHtml", to_html),
            self.assertRaisesRegex(RuntimeError, "debug request dispatch"),
        ):
            await dispatch(kernel, "/api")

        self.assertEqual(to_html.calls, 0)
        self.assertEqual(self.sys_exit.calls, 0)
        self.assertEqual(self.os_exit.calls, 0)
        self.assertIs(ScopedContext.getCurrentScope(), previous_scope)

    async def testOrdinaryRequestsDoNotRunDumpSetup(self) -> None:
        """
        Verify that ordinary requests skip dump setup and debug lookups.

        Returns
        -------
        None
            This test does not return a value.
        """
        for debug in (True, False):
            with self.subTest(debug=debug):
                kernel, _app, catch = await self._boot(debug=debug)
                keys: list[object] = []
                original_setitem = ScopeManager.__setitem__

                def record(
                    scope: ScopeManager,
                    key: object,
                    value: object,
                    *,
                    recorded: list[object] = keys,
                    write: Callable[
                        [ScopeManager, object, object], None,
                    ] = original_setitem,
                ) -> None:
                    """
                    Record scope assignments without changing their behavior.

                    Parameters
                    ----------
                    scope : ScopeManager
                        Scope receiving the assignment.
                    key : object
                        Binding key to record and assign.
                    value : object
                        Value to assign under the key.
                    recorded : list[object], optional
                        Collection receiving each assigned key for this subtest.
                    write : callable, optional
                        Unpatched scope assignment method used for delegation.

                    Returns
                    -------
                    None
                        Record the key and delegate the assignment unchanged.
                    """
                    recorded.append(key)
                    write(scope, key, value)

                debug_mode = _UnexpectedCall(
                    "Debug mode was checked for an ordinary request",
                )
                with (
                    replace_attribute(_StubApp, "isDebug", debug_mode),
                    replace_attribute(ScopeManager, "__setitem__", record),
                ):
                    asgi = await dispatch(kernel, "/api")
                    rsgi = await kernel.handleRSGI(
                        _StubRsgiScope("/api"), _StubRsgiProtocol(),
                    )

                self.assertEqual(asgi.getBody(), b"api")
                self.assertEqual(rsgi.getBody(), b"api")
                self.assertEqual(debug_mode.calls, 0)
                self.assertEqual(keys, ["kernel", Request, "kernel", Request])
                self.assertEqual(catch.handled, [])

    async def testDumpPreservesValuesBeforeFinallyCleanup(self) -> None:
        """
        Verify that dumps snapshot values before ``finally`` cleanup.

        Returns
        -------
        None
            This test does not return a value.
        """
        kernel, _app, catch = await self._boot()
        response = await dispatch(kernel, "/frozen-dump")

        self.assertEqual(response.getStatusCode(), 200)
        self.assertIn(b"before-finally", response.getBody())
        self.assertNotIn(b"after-finally", response.getBody())
        self.assertEqual(catch.handled, [])

    async def testRenderingFailureUsesTheOrdinaryErrorHandler(self) -> None:
        """
        Verify that dump-rendering failures use the ordinary error handler.

        Returns
        -------
        None
            This test does not return a value.
        """
        kernel, _app, catch = await self._boot()

        def fail_render(*_args: object, **_kwargs: object) -> Never:
            """
            Fail HTML fragment rendering with the expected error.

            Parameters
            ----------
            *_args : object
                Unused positional arguments supplied by the renderer.
            **_kwargs : object
                Unused keyword arguments supplied by the renderer.

            Raises
            ------
            ValueError
                Always raised to exercise ordinary HTTP error handling.
            """
            error_msg = "dump-render-failed"
            raise ValueError(error_msg)

        with replace_attribute(VarDumper, "toHtml", fail_render):
            response = await dispatch(kernel, "/dump")

        self.assertEqual(response.getStatusCode(), 500)
        self.assertEqual(len(catch.handled), 1)
        self.assertIsInstance(catch.handled[0], ValueError)
        self.assertEqual(str(catch.handled[0]), "dump-render-failed")
        self.assertEqual(self.sys_exit.calls, 0)
        self.assertEqual(self.os_exit.calls, 0)

    async def testProductionRejectsDumpsWithoutRenderingOrExiting(self) -> None:
        """
        Verify that production rejects dumps without rendering or exiting.

        Returns
        -------
        None
            This test does not return a value.
        """
        kernel, _app, catch = await self._boot(debug=False)
        to_html = _UnexpectedCall("HTML rendering was called in production")
        render_page = _UnexpectedCall("Page rendering was called in production")
        with (
            replace_attribute(VarDumper, "toHtml", to_html),
            replace_attribute(_StubDefaultResponses, "dump", render_page),
        ):
            response = await dispatch(kernel, "/dump")

        self.assertEqual(response.getStatusCode(), 500)
        self.assertEqual(len(catch.handled), 1)
        self.assertIsInstance(catch.handled[0], RuntimeError)
        self.assertIn("debug", str(catch.handled[0]))
        self.assertNotIn(b"<script>", response.getBody())
        self.assertEqual(to_html.calls, 0)
        self.assertEqual(render_page.calls, 0)
        self.assertEqual(self.sys_exit.calls, 0)
        self.assertEqual(self.os_exit.calls, 0)

    async def testPageRenderingFailureUsesTheOrdinaryErrorHandler(self) -> None:
        """
        Verify that template failures use the ordinary error handler.

        Returns
        -------
        None
            This test does not return a value.
        """
        kernel, _app, catch = await self._boot()

        async def fail_page(*_args: object, **_kwargs: object) -> Never:
            """
            Fail asynchronous dump-page rendering with the expected error.

            Parameters
            ----------
            *_args : object
                Unused positional arguments supplied by the renderer.
            **_kwargs : object
                Unused keyword arguments supplied by the renderer.

            Raises
            ------
            ValueError
                Always raised to exercise ordinary HTTP error handling.
            """
            error_msg = "dump-page-render-failed"
            raise ValueError(error_msg)

        with replace_attribute(_StubDefaultResponses, "dump", fail_page):
            response = await dispatch(kernel, "/dump")

        self.assertEqual(response.getStatusCode(), 500)
        self.assertEqual(len(catch.handled), 1)
        self.assertIsInstance(catch.handled[0], ValueError)
        self.assertEqual(str(catch.handled[0]), "dump-page-render-failed")
        self.assertEqual(self.sys_exit.calls, 0)
        self.assertEqual(self.os_exit.calls, 0)

    async def testFallbackDumpIsNotReportedAsAnApplicationError(self) -> None:
        """
        Verify that fallback dumps are not reported as application errors.

        Returns
        -------
        None
            This test does not return a value.
        """
        kernel, _app, catch = await self._boot(fallback=(None, dump_fallback))
        response = await dispatch(kernel, "/missing")

        self._assertDump(response, "/missing")
        self.assertEqual(catch.handled, [])
