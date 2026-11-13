# ruff: noqa: PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Exercise failure delivery while preserving HTTP transport behavior."""

from __future__ import annotations
import asyncio
from threading import Event
from types import SimpleNamespace
from orionis.failure.runtime import capture, operation
from orionis.http.adapters.response.files import complete_file_read, open_file
from orionis.http.adapters.response.asgi import ASGIResponseAdapter
from orionis.http.adapters.response.streams import await_cleanup, close_stream
from orionis.http.adapters.websocket.asgi import ASGIWebSocketTransport
from orionis.http.adapters.websocket.rsgi import RSGIWebSocketTransport
from orionis.http.exceptions.websocket import WebSocketDisconnected
from orionis.http.enums.interfaces import Interface
from orionis.http.payload.stream_parser import MultipartStreamParser
from orionis.http.payload.form_data import FormData
from orionis.http.request import Request
from orionis.http.responses import Response
from orionis.http.routes.exceptions.route_not_found import RouteNotFound
from orionis.schemas.exceptions.validation import ValidationException
from orionis.test import TestCase
from tests.foundation.test_application_async import _AsyncCall
from tests.foundation.test_failure_lifecycle import (
    RecordingHandler,
    reporting_application,
)
from tests.http.test_kernel import (
    _StubRsgiProtocol,
    _StubRsgiScope,
    boot_kernel,
    fallback_function,
    make_asgi_scope,
    receive_empty,
    send_noop,
)
from tests.http.test_support import make_adapter, replace_attribute
from tests.http.payload.test_stream_parser import stream_chunks
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.http.kernel import KernelHTTP
    from orionis.foundation.application import Application


class _ReportingApp:
    """Share one runtime between the application and a controlled kernel."""

    def __init__(self, original: object, app: Application) -> None:
        """Retain controlled services and the active reporting runtime."""
        self.original = original
        self._failure_runtime = app._failure_runtime

    def __getattr__(self, name: str) -> object:
        """Forward ordinary kernel service access to its fixture."""
        return getattr(self.original, name)


async def reporting_kernel(
    **kwargs: object,
) -> tuple[Application, KernelHTTP, RecordingHandler, object, object]:
    """Wire the real application boundary around the existing kernel fixture."""
    kernel, original, responses, catcher = await boot_kernel(**kwargs)
    app, handler = reporting_application()
    app._failure_runtime.activate(object())
    kernel._KernelHTTP__app = _ReportingApp(original, app)
    app._Application__kernel_http_asgi = kernel.handleASGI
    app._Application__kernel_http_rsgi = kernel.handleRSGI
    return app, kernel, handler, responses, catcher


class TestHttpFailureReporting(TestCase):
    async def testHandledOuterExceptionCannotHideLocalCleanupFailures(self) -> None:
        """Propagate owned cleanup errors even inside another caller's except block.

        Returns
        -------
        None
            No return value.
        """
        for interface in ("asgi", "rsgi", "websocket"):
            with self.subTest(interface=interface):
                app, kernel, handler, _, _ = await reporting_kernel()
                failure = OSError("owned cleanup failed")

                def close(_request: Request, error: Exception = failure) -> None:
                    """Raise the cleanup failure selected by this scenario.

                    Parameters
                    ----------
                    _request : Request
                        Request whose cleanup is exercised.
                    error : Exception
                        Failure to propagate.

                    Returns
                    -------
                    None
                        No return value.
                    """
                    raise error

                socket = SimpleNamespace(
                    accepted=True,
                    closed=False,
                    close=_AsyncCall(side_effect=failure),
                )
                unrelated = LookupError("unrelated caller exception")
                with (
                    replace_attribute(Request, "close", close),
                    replace_attribute(
                        type(kernel),
                        "_KernelHTTP__processWebSocket",
                        _AsyncCall(),
                    ),
                    operation(app, flow="http", isolated=True),
                ):
                    try:
                        raise unrelated
                    except LookupError:
                        with self.assertRaises(OSError) as caught:
                            if interface == "asgi":
                                await kernel.handleASGI(
                                    make_asgi_scope("/api"),
                                    receive_empty,
                                    send_noop,
                                )
                            elif interface == "rsgi":
                                await kernel.handleRSGI(
                                    _StubRsgiScope("/api"),
                                    _StubRsgiProtocol(),
                                )
                            else:
                                await kernel._KernelHTTP__runWebSocket(
                                    None,
                                    socket,
                                    Interface.ASGI,
                                )
                self.assertIs(caught.exception, failure)
                self.assertEqual([error for error, _ in handler.events], [failure])

    async def testBufferedSendFailureRetainsResponseStartedState(self) -> None:
        """Observe transport failures without attempting a second response."""
        for fail_type, started in (
            ("http.response.start", False),
            ("http.response.body", True),
        ):
            with self.subTest(fail_type=fail_type):
                app, handler = reporting_application()
                app._failure_runtime.activate(object())
                failure = OSError("transport failed")
                events = []

                async def send(
                    event: dict,
                    events: list = events,
                    fail_type: str = fail_type,
                    failure: OSError = failure,
                ) -> None:
                    """Fail at the selected transport event."""
                    events.append(event)
                    if event["type"] == fail_type:
                        raise failure

                with (
                    operation(app, flow="http", isolated=True),
                    self.assertRaises(OSError),
                ):
                    await ASGIResponseAdapter().send(
                        make_adapter([]),
                        Response(content="body"),
                        receive_empty,
                        send,
                    )
                self.assertEqual([error for error, _ in handler.events], [failure])
                self.assertEqual(
                    handler.events[0][1].metadata["response_started"],
                    started,
                )
                self.assertEqual(len(events), 2 if started else 1)

    async def testWebSocketTranslationPreservesOriginalTransportFailure(self) -> None:
        """Deliver originals once while preserving the disconnect control type."""
        for interface in ("asgi", "rsgi"):
            with self.subTest(interface=interface):
                app, handler = reporting_application()
                app._failure_runtime.activate(object())
                failure = OSError("socket send failed")
                if interface == "asgi":
                    transport = ASGIWebSocketTransport(
                        {},
                        receive_empty,
                        _AsyncCall(side_effect=failure),
                    )
                else:
                    transport = RSGIWebSocketTransport(object())
                    transport._transport = SimpleNamespace(
                        send_str=_AsyncCall(side_effect=failure),
                    )
                with operation(app, flow="http", isolated=True):
                    with self.assertRaises(WebSocketDisconnected) as caught:
                        await transport.sendText("data")
                    await capture(caught.exception, app=app)
                self.assertIs(caught.exception.__cause__, failure)
                self.assertEqual([error for error, _ in handler.events], [failure])
                self.assertEqual(handler.events[0][1].metadata["transport"], interface)

    async def testLocalValidationPreservesHttpResponseAndArrivesOnce(self) -> None:
        """Observe local validation without changing redirect or API responses."""
        for path, status in (("/web-invalid", 302), ("/api-invalid", 422)):
            with self.subTest(path=path):
                app, _, handler, _, _ = await reporting_kernel()
                scope = make_asgi_scope(
                    path,
                    headers=[
                        (b"host", b"orionis.test"),
                        (b"content-type", b"application/x-www-form-urlencoded"),
                    ],
                )
                response = await app(scope, receive_empty, send_noop)
                self.assertEqual(response.getStatusCode(), status)
                self.assertEqual(len(handler.events), 1)
                error, context = handler.events[0]
                self.assertIsInstance(error, ValidationException)
                self.assertTrue(context.expected)
                self.assertEqual(handler.reports, [])

    async def testPendingWebSocketCleanupPreservesFailureAndCancellation(self) -> None:
        """Retain a pending handshake's primary failure when its rejection fails."""
        for primary in (ValueError("handshake"), asyncio.CancelledError("caller")):
            with self.subTest(primary=type(primary)):
                app, kernel, handler, _, _ = await reporting_kernel()
                secondary = OSError("reject failed")
                process = _AsyncCall(side_effect=primary)
                closing = _AsyncCall(side_effect=secondary)
                socket = SimpleNamespace(accepted=False, closed=False, close=closing)
                with (
                    replace_attribute(
                        type(kernel),
                        "_KernelHTTP__processWebSocket",
                        process,
                    ),
                    operation(app, flow="websocket", isolated=True),
                    self.assertRaises(type(primary)) as caught,
                ):
                    await kernel._KernelHTTP__runWebSocket(None, socket, Interface.ASGI)
                self.assertIs(caught.exception, primary)
                expected = (
                    [secondary]
                    if isinstance(
                        primary,
                        asyncio.CancelledError,
                    )
                    else [primary, secondary]
                )
                self.assertEqual([error for error, _ in handler.events], expected)
                self.assertEqual(closing.awaitCount, 1)

    async def testPolicyBeforeFailureIsReportedWithoutAnActiveRequestScope(
        self,
    ) -> None:
        """Report a pre-scope policy failure through the application boundary."""
        app, kernel, handler, _, _ = await reporting_kernel()
        failure = RuntimeError("before failed")

        def before(_adapter: object) -> None:
            """Fail before the kernel opens its request scope."""
            raise failure

        kernel._KernelHTTP__endpoint_policies["/api"] = SimpleNamespace(before=before)
        with self.assertRaises(RuntimeError):
            await app(make_asgi_scope("/api"), receive_empty, send_noop)
        self.assertEqual([error for error, _ in handler.events], [failure])
        self.assertEqual(handler.reports, [failure])

    async def testEndpointPolicyKeepsItsResponseAndOriginalFailure(self) -> None:
        """Retain policy translation while delivering the original error once."""
        app, kernel, handler, _, catcher = await reporting_kernel()
        expected = Response(content="policy", status_code=409)

        async def response_policy(response: Response) -> Response:
            """Keep the response selected by the endpoint exception policy."""
            return response

        policy = SimpleNamespace(
            before=lambda _adapter: None,
            exception=_AsyncCall(return_value=expected),
            response=response_policy,
            isExpectedFailure=lambda _error: True,
        )
        kernel._KernelHTTP__endpoint_policies["/boom"] = policy
        response = await app(make_asgi_scope("/boom"), receive_empty, send_noop)
        self.assertIs(response, expected)
        self.assertEqual(len(handler.events), 1)
        self.assertIs(policy.exception.calls[0][0][0], handler.events[0][0])
        self.assertTrue(handler.events[0][1].expected)
        self.assertEqual(handler.reports, [])
        self.assertEqual(catcher.handled, [])

    async def testSendAndCleanupFailuresAreBothObservedWithoutResending(self) -> None:
        """Preserve both incidents while attempting transport delivery once."""
        for interface in ("asgi", "rsgi"):
            with self.subTest(interface=interface):
                app, kernel, handler, _, _ = await reporting_kernel()
                primary = OSError("send failed")
                secondary = RuntimeError("request cleanup failed")
                sender = _AsyncCall(side_effect=primary)
                setattr(
                    kernel,
                    f"_KernelHTTP__{interface}_adapter",
                    SimpleNamespace(send=sender),
                )

                def close(_request: Request, secondary: Exception = secondary) -> None:
                    """Fail while releasing the request resources."""
                    raise secondary

                with (
                    replace_attribute(Request, "close", close),
                    self.assertRaises(OSError) as caught,
                ):
                    if interface == "asgi":
                        await app(make_asgi_scope("/api"), receive_empty, send_noop)
                    else:
                        await app.__rsgi__(
                            _StubRsgiScope("/api"),
                            _StubRsgiProtocol(),
                        )
                self.assertIs(caught.exception, primary)
                self.assertEqual(sender.awaitCount, 1)
                self.assertEqual(
                    [error for error, _ in handler.events],
                    [primary, secondary],
                )
                self.assertEqual(
                    handler.events[1][1].parent_event_id,
                    handler.events[0][1].event_id,
                )

    async def testRequestCleanupAttemptsEveryUploadedFile(self) -> None:
        """Observe a complete cleanup group after attempting all retained uploads."""
        for interface in ("asgi", "rsgi"):
            with self.subTest(interface=interface):
                app, kernel, handler, _, _ = await reporting_kernel()
                first, second = OSError("first close"), OSError("second close")
                closed = []

                def upload(
                    label: str,
                    error: Exception | None = None,
                    closed: list = closed,
                ) -> object:
                    """Create one upload whose closure can fail independently."""

                    def close() -> None:
                        """Record the attempt before raising its exact error."""
                        closed.append(label)
                        if error is not None:
                            raise error

                    return SimpleNamespace(close=close)

                form = FormData(
                    [
                        ("first", upload("first", first)),
                        ("second", upload("second", second)),
                        ("third", upload("third")),
                    ],
                )
                sender = _AsyncCall()
                setattr(
                    kernel,
                    f"_KernelHTTP__{interface}_adapter",
                    SimpleNamespace(send=sender),
                )

                def close_request(_request: Request, form: FormData = form) -> None:
                    """Release parsed request uploads at the real kernel boundary."""
                    form.close()

                with (
                    replace_attribute(Request, "close", close_request),
                    self.assertRaises(ExceptionGroup) as caught,
                ):
                    if interface == "asgi":
                        await app(make_asgi_scope("/api"), receive_empty, send_noop)
                    else:
                        await app.__rsgi__(
                            _StubRsgiScope("/api"),
                            _StubRsgiProtocol(),
                        )
                self.assertEqual(closed, ["first", "second", "third"])
                self.assertEqual(caught.exception.exceptions, (first, second))
                self.assertEqual(sender.awaitCount, 1)
                self.assertEqual(
                    [error for error, _ in handler.events],
                    [caught.exception],
                )

    async def testRequestCleanupFailurePreservesCallerCancellation(self) -> None:
        """Keep cancellation public after reporting an independent close failure."""
        for interface in ("asgi", "rsgi"):
            with self.subTest(interface=interface):
                app, kernel, handler, _, _ = await reporting_kernel()
                cancellation = asyncio.CancelledError("caller cancelled")
                secondary = OSError("close failed")
                sender = _AsyncCall(side_effect=cancellation)
                setattr(
                    kernel,
                    f"_KernelHTTP__{interface}_adapter",
                    SimpleNamespace(send=sender),
                )

                def close(_request: Request, error: Exception = secondary) -> None:
                    """Fail while releasing an already cancelled request."""
                    raise error

                with (
                    replace_attribute(Request, "close", close),
                    self.assertRaises(asyncio.CancelledError) as caught,
                ):
                    if interface == "asgi":
                        await app(make_asgi_scope("/api"), receive_empty, send_noop)
                    else:
                        await app.__rsgi__(
                            _StubRsgiScope("/api"),
                            _StubRsgiProtocol(),
                        )
                self.assertIs(caught.exception, cancellation)
                self.assertEqual([error for error, _ in handler.events], [secondary])
                self.assertEqual(sender.awaitCount, 1)

    async def testFallbackReceivesRouteErrorWithoutChangingResponse(self) -> None:
        """Observe an unmatched route before its custom fallback returns."""
        app, _, handler, _, _ = await reporting_kernel(
            fallback=(None, fallback_function),
        )
        response = await app(make_asgi_scope("/missing"), receive_empty, send_noop)
        self.assertEqual(response.getStatusCode(), 200)
        self.assertEqual(len(handler.events), 1)
        self.assertIsInstance(handler.events[0][0], RouteNotFound)
        self.assertEqual(handler.reports, [])

    async def testCapacityFailureIsAResultAndRetains503(self) -> None:
        """Notify a failed admission without manufacturing an exception."""
        app, kernel, handler, _, _ = await reporting_kernel()
        kernel._KernelHTTP__request_slots = 0
        response = await app(make_asgi_scope("/api"), receive_empty, send_noop)
        self.assertEqual(response.getStatusCode(), 503)
        self.assertEqual([value for value, _ in handler.results], [503])
        self.assertEqual(handler.events, [])

    async def testPolicyRejectionIsAResultAndPreservesItsStatus(self) -> None:
        """Deliver protocol admission results without rendering a new response."""
        for interface in ("asgi", "rsgi"):
            with self.subTest(interface=interface):
                app, kernel, handler, _, _ = await reporting_kernel()
                rejection = Response(status_code=403)
                kernel._KernelHTTP__endpoint_policies["/api"] = SimpleNamespace(
                    before=lambda _adapter, rejection=rejection: rejection,
                    response=_AsyncCall(return_value=rejection),
                )
                if interface == "asgi":
                    response = await app(
                        make_asgi_scope("/api"),
                        receive_empty,
                        send_noop,
                    )
                else:
                    response = await app.__rsgi__(
                        _StubRsgiScope("/api"),
                        _StubRsgiProtocol(),
                    )
                self.assertIs(response, rejection)
                self.assertEqual([value for value, _ in handler.results], [403])
                self.assertEqual(handler.events, [])

    async def testStreamPrimaryAndCleanupFailuresReachTheSameHandler(self) -> None:
        """Keep delivery and cleanup exceptions available to one handler."""
        app, handler = reporting_application()
        app._failure_runtime.activate(object())
        primary = ValueError("stream failed")
        secondary = OSError("stream close failed")
        stream = SimpleNamespace(aclose=_AsyncCall(side_effect=secondary))
        with (
            operation(app, flow="http", isolated=True),
            self.assertRaises(ValueError) as caught,
        ):
            await close_stream(stream, primary)
        self.assertIs(caught.exception, primary)
        self.assertEqual([error for error, _ in handler.events], [primary, secondary])

    async def testCancelledCleanupRetainsExistingCausalPolicy(self) -> None:
        """Preserve explicit, implicit and suppressed causes of owned cleanup."""
        for chaining in ("explicit", "implicit", "suppressed"):
            with self.subTest(chaining=chaining):
                app, handler = reporting_application()
                app._failure_runtime.activate(object())
                primary = OSError("cleanup failed")
                cause = LookupError("cleanup cause")
                primary.__context__ = cause
                if chaining == "explicit":
                    primary.__cause__ = cause
                elif chaining == "suppressed":
                    primary.__suppress_context__ = True
                chain = (
                    primary.__cause__,
                    primary.__context__,
                    primary.__suppress_context__,
                )
                started, release = asyncio.Event(), asyncio.Event()

                async def cleanup(
                    primary: OSError = primary,
                    started: asyncio.Event = started,
                    release: asyncio.Event = release,
                ) -> None:
                    """Fail only after the owner has requested cancellation."""
                    started.set()
                    await release.wait()
                    raise primary

                with operation(app, flow="http", isolated=True):
                    pending = asyncio.create_task(cleanup())
                    waiter = asyncio.create_task(await_cleanup(pending))
                    await started.wait()
                    waiter.cancel()
                    release.set()
                    with self.assertRaises(OSError) as caught:
                        await waiter
                self.assertIs(caught.exception, primary)
                self.assertEqual(
                    (
                        primary.__cause__,
                        primary.__context__,
                        primary.__suppress_context__,
                    ),
                    chain,
                )
                self.assertTrue(pending.done())
                self.assertEqual([error for error, _ in handler.events], [primary])

    async def testCancelledFileReadStillReportsItsLateFailure(self) -> None:
        """Observe the worker failure while retaining caller cancellation."""
        app, handler = reporting_application()
        app._failure_runtime.activate(object())
        loop = asyncio.get_running_loop()
        pending = loop.create_future()
        failure = OSError("late read failure")
        notifications = []
        previous_handler = loop.get_exception_handler()
        loop.set_exception_handler(lambda _loop, context: notifications.append(context))
        try:
            with operation(app, flow="http", isolated=True):
                task = asyncio.create_task(complete_file_read(pending))
                await asyncio.sleep(0)
                task.cancel("first cancellation")
                await asyncio.sleep(0)
                task.cancel("second cancellation")
                await asyncio.sleep(0)
                pending.set_exception(failure)
                with self.assertRaises(asyncio.CancelledError) as caught:
                    await task
        finally:
            loop.set_exception_handler(previous_handler)
        self.assertEqual([error for error, _ in handler.events], [failure])
        self.assertEqual(caught.exception.args, ("first cancellation",))
        self.assertEqual(notifications, [])

    async def testMultipartCleanupContinuesAfterAnUploadCloseFails(self) -> None:
        """Close every failed parse upload and report distinct cleanup errors."""
        app, handler = reporting_application()
        app._failure_runtime.activate(object())
        primary = ValueError("incomplete body")
        first = OSError("current upload close failed")
        second = OSError("completed upload close failed")
        closures = []

        def upload(error: Exception | None = None) -> SimpleNamespace:
            """Record file closure before optionally raising its cleanup error."""

            def close() -> None:
                """Attempt this file's closure exactly once."""
                closures.append(error)
                if error is not None:
                    raise error

            return SimpleNamespace(close=close)

        current = upload(first)
        completed = upload(second)
        healthy = upload()

        async def parse_parts(
            parser: MultipartStreamParser,
            form_items: list[tuple[str, object]],
        ) -> None:
            """Fail after owning both a partial upload and completed fields."""
            parser._currentPart = SimpleNamespace(is_file=True, data=current)
            form_items.extend(
                [
                    ("field", "value"),
                    ("completed", completed),
                    ("healthy", healthy),
                ],
            )
            raise primary

        parser = MultipartStreamParser(stream_chunks([]), b"boundary")
        with (
            operation(app, flow="http", isolated=True),
            replace_attribute(MultipartStreamParser, "_parseParts", parse_parts),
            self.assertRaises(OSError) as caught,
        ):
            await parser.parse()
        self.assertIs(caught.exception, first)
        self.assertIs(first.__context__, primary)
        self.assertEqual(
            [error for error, _ in handler.events],
            [primary, first, second],
        )
        self.assertEqual(closures, [first, second, None])

    async def testFileSeekAndCloseFailuresBothReachTheHandler(self) -> None:
        """Preserve the seek error or caller cancellation and observe cleanup."""
        for cancelled in (False, True):
            with self.subTest(cancelled=cancelled):
                app, handler = reporting_application()
                app._failure_runtime.activate(object())
                primary = OSError("seek failed")
                cause = ValueError("original seek cause")
                primary.__cause__ = cause
                secondary = OSError("close failed")
                started, release = Event(), Event()

                def seek(
                    _offset: int,
                    primary: OSError = primary,
                    started: Event = started,
                    release: Event = release,
                ) -> None:
                    """Keep the worker alive until cancellation can be requested."""
                    started.set()
                    release.wait(5)
                    raise primary

                def close(secondary: OSError = secondary) -> None:
                    """Fail independently while closing the partially opened file."""
                    raise secondary

                file = SimpleNamespace(seek=seek, close=close)
                path = SimpleNamespace(open=lambda _mode, file=file: file)
                with operation(app, flow="http", isolated=True):
                    task = asyncio.create_task(open_file(path, start=1))
                    try:
                        self.assertTrue(await asyncio.to_thread(started.wait, 5))
                        if cancelled:
                            task.cancel("first cancellation")
                    finally:
                        release.set()
                    expected = asyncio.CancelledError if cancelled else OSError
                    with self.assertRaises(expected) as caught:
                        await task
                if cancelled:
                    self.assertEqual(caught.exception.args, ("first cancellation",))
                else:
                    self.assertIs(caught.exception, primary)
                    self.assertIs(primary.__cause__, cause)
                self.assertEqual(
                    [error for error, _ in handler.events],
                    [primary, secondary],
                )

    async def _assertMultipartCancellationClosesUploads(self, phase: str) -> None:
        """Cancel a paused failure hook after every owned upload has been closed."""
        app, handler = reporting_application()
        app._failure_runtime.activate(object())
        primary = ValueError("parse failed")
        secondary = OSError("close failed")
        entered = asyncio.Event()
        closures = []
        original_handler = handler.handleFailure

        async def handle_failure(exception: BaseException, context: object) -> object:
            """Pause the selected delivery after recording its original exception."""
            handling = await original_handler(exception, context)
            if context.phase == phase:
                entered.set()
                await asyncio.Event().wait()
            return handling

        app._failure_runtime.handler = SimpleNamespace(handleFailure=handle_failure)

        def upload(name: str, error: Exception | None = None) -> SimpleNamespace:
            """Create an owned upload whose closure may fail independently."""

            def close() -> None:
                """Record resource closure before raising any cleanup failure."""
                closures.append(name)
                if error is not None:
                    raise error

            return SimpleNamespace(close=close)

        current = upload("current", secondary)
        first = upload("first")
        second = upload("second")

        async def parse_parts(
            parser: MultipartStreamParser,
            form_items: list[tuple[str, object]],
        ) -> None:
            """Leave one current upload and two completed uploads to clean up."""
            parser._currentPart = SimpleNamespace(is_file=True, data=current)
            form_items.extend([("first", first), ("second", second)])
            raise primary

        parser = MultipartStreamParser(stream_chunks([]), b"boundary")
        with (
            operation(app, flow="http", isolated=True),
            replace_attribute(MultipartStreamParser, "_parseParts", parse_parts),
        ):
            task = asyncio.create_task(parser.parse())
            try:
                await asyncio.wait_for(entered.wait(), 1)
                self.assertEqual(closures, ["current", "first", "second"])
            finally:
                task.cancel("request cancelled")
                with self.assertRaises(asyncio.CancelledError) as caught:
                    await task
        self.assertEqual(caught.exception.args, ("request cancelled",))
        self.assertEqual(closures, ["current", "first", "second"])
        self.assertEqual([error for error, _ in handler.events], [primary, secondary])

    async def testCancellingParseFailureHookLeavesEveryUploadClosed(self) -> None:
        """Close all uploads before awaiting the original parse failure hook."""
        await self._assertMultipartCancellationClosesUploads("payload.parse")

    async def testCancellingCleanupFailureHookLeavesEveryUploadClosed(self) -> None:
        """Finish remaining closures before awaiting a failed upload's hook."""
        await self._assertMultipartCancellationClosesUploads("payload.cleanup")
