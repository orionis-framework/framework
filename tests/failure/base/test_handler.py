# ruff: noqa: B904, PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Exercise native implicit exception context as well as explicit causes.
from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock

from orionis.failure.base.handler import BaseExceptionHandler
from orionis.failure.entities.context import FailureContext
from orionis.failure.entities.handling import FailureHandling
from orionis.failure.entities.throwable import Throwable
from orionis.http.default.contracts.responses import IDefaultResponses
from orionis.http.layer.web.exceptions import CSRFTokenMismatchException
from orionis.http.payload.body import PayloadTooLargeException
from orionis.http.request import UnsupportedMediaTypeException
from orionis.http.routes.exceptions.method_not_allowed import MethodNotAllowed
from orionis.http.routes.exceptions.route_not_found import RouteNotFound
from orionis.logging.contracts.logger import ILogger
from orionis.test import TestCase


def _make_application() -> MagicMock:
    """
    Build an application mock with debug mode enabled for HTTP tests.

    Returns
    -------
    MagicMock
        A mocked application instance with debug mode enabled.
    """
    application = MagicMock()
    application.config.return_value = True
    return application


def _make_handler(
    dont_catch: frozenset[type[BaseException]] | None = None,
) -> BaseExceptionHandler:
    """
    Build a BaseExceptionHandler with a mocked DefaultResponses dependency.

    Parameters
    ----------
    dont_catch : frozenset or None
        Optional set of exception types the handler should ignore.

    Returns
    -------
    BaseExceptionHandler
        A ready-to-use handler instance.
    """
    mock_responses = MagicMock(spec=IDefaultResponses)
    handler_type = BaseExceptionHandler
    if dont_catch is not None:
        handler_type = type(
            "ConfiguredHandler",
            (BaseExceptionHandler,),
            {"dont_catch": dont_catch},
        )
    return handler_type(
        default_responses=mock_responses,
        application=_make_application(),
    )


async def _complete(
    handler: BaseExceptionHandler,
    exception: BaseException,
    logger: MagicMock,
) -> FailureHandling:
    """Execute default logging with an explicit isolated logger dependency."""
    handler._BaseExceptionHandler__application.make = AsyncMock(return_value=logger)
    handling = await handler.handleFailure(exception, FailureContext())
    await handling.complete()
    return handling


async def _present(
    handler: BaseExceptionHandler,
    exception: BaseException,
    *,
    flow: str,
    request: object | None = None,
    console: MagicMock | None = None,
) -> object:
    """Request protocol presentation from the unified hook's deferred plan."""
    if console is not None:
        handler._BaseExceptionHandler__application.make = AsyncMock(
            return_value=console,
        )
    handling = await handler.handleFailure(exception, FailureContext(flow=flow))
    return await handling.present(flow=flow, request=request)


class TestBaseExceptionHandlerToThrowable(TestCase):
    def testConvertsExceptionToThrowable(self) -> None:
        """Convert a standard exception into a Throwable structure.

        Validates that toThrowable returns a Throwable whose classtype,
        message, and args fields reflect the supplied exception.

        Returns
        -------
        None
            No return value.
        """
        handler = _make_handler()
        exc = ValueError("bad input")
        result = handler.toThrowable(exc)
        self.assertIsInstance(result, Throwable)
        self.assertIs(result.classtype, ValueError)
        self.assertEqual(result.message, "bad input")

    def testArgsAreStringified(self) -> None:
        """Stringify all exception arguments inside the Throwable args tuple.

        Validates that every element in the resulting args tuple is a str,
        regardless of the original argument type.

        Returns
        -------
        None
            No return value.
        """
        handler = _make_handler()
        exc = TypeError(42, "extra")
        result = handler.toThrowable(exc)
        self.assertEqual(result.args, ("42", "extra"))

    def testSingleMessageArgMatchesFirstArg(self) -> None:
        """Preserve a single-argument RuntimeError message.

        The native RuntimeError text matches its sole string argument.

        Returns
        -------
        None
            No return value.
        """
        handler = _make_handler()
        exc = RuntimeError("runtime failure")
        result = handler.toThrowable(exc)
        self.assertEqual(result.message, result.args[0])

    def testNoArgsProducesEmptyStringMessage(self) -> None:
        """Produce an empty-string message for zero-argument exceptions.

        The native text of a plain Exception without arguments is empty.

        Returns
        -------
        None
            No return value.
        """
        handler = _make_handler()
        exc = Exception()
        result = handler.toThrowable(exc)
        self.assertEqual(result.message, "")

    def testTracebackIsNoneWhenNoExceptionRaised(self) -> None:
        """Store None in the traceback field for exceptions not yet raised.

        Validates that constructing an exception without raising it leaves
        __traceback__ as None, which is propagated faithfully.

        Returns
        -------
        None
            No return value.
        """
        handler = _make_handler()
        exc = OSError("no tb")
        result = handler.toThrowable(exc)
        self.assertIsNone(result.traceback)

    def testTracebackCapturedAfterRaise(self) -> None:
        """Capture a live traceback when the exception has been raised.

        Validates that toThrowable faithfully stores __traceback__ when
        the exception was actually raised, enabling downstream reporting.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        KeyError
            Raised by this helper to exercise the failure path.
        """
        handler = _make_handler()
        exc: Exception | None = None
        error_msg = "key missing"
        try:
            raise KeyError(error_msg)
        except KeyError as caught:
            exc = caught
        if exc is None:
            self.fail("Exception was not raised")
        result = handler.toThrowable(exc)
        self.assertIs(result.traceback, exc.__traceback__)
        self.assertIsNotNone(result.traceback)


class TestBaseExceptionHandlerIsExceptionIgnored(TestCase):
    def testReturnsFalseWhenDontCatchIsEmpty(self) -> None:
        """Return False for any exception when dont_catch is an empty frozenset.

        Validates the default behavior where all exceptions are considered
        reportable.

        Returns
        -------
        None
            No return value.
        """
        handler = _make_handler(dont_catch=frozenset())
        exc = ValueError("x")
        self.assertFalse(handler.isExceptionIgnored(exc))

    def testReturnsTrueWhenExceptionTypeInDontCatch(self) -> None:
        """Return True when the exception type is listed in dont_catch.

        Validates that the membership check uses type identity so that
        exceptions on the ignore-list are not reported.

        Returns
        -------
        None
            No return value.
        """
        handler = _make_handler(dont_catch=frozenset({ValueError}))
        exc = ValueError("ignored")
        self.assertTrue(handler.isExceptionIgnored(exc))

    def testReturnsFalseForSubclassNotInDontCatch(self) -> None:
        """Return False for a subclass whose base is in dont_catch.

        Validates that the check uses exact type membership, not
        isinstance, so subclasses are not automatically silenced.

        Returns
        -------
        None
            No return value.
        """

        class _Sub(ValueError):
            pass

        handler = _make_handler(dont_catch=frozenset({ValueError}))
        exc = _Sub("sub")
        self.assertFalse(handler.isExceptionIgnored(exc))

    def testRaisesTypeErrorForNonException(self) -> None:
        """Raise TypeError when the argument is not a BaseException.

        Validates the guard that prevents non-exception objects from
        passing through the ignore-list check unnoticed.

        Returns
        -------
        None
            No return value.
        """
        handler = _make_handler()
        with self.assertRaises(TypeError):
            handler.isExceptionIgnored("not an exception")  # type: ignore[arg-type]

    def testMultipleTypesInDontCatch(self) -> None:
        """Recognise each listed type individually in a populated dont_catch.

        Validates that having multiple exception types in dont_catch works
        correctly for every member.

        Returns
        -------
        None
            No return value.
        """
        handler = _make_handler(dont_catch=frozenset({ValueError, KeyError}))
        self.assertTrue(handler.isExceptionIgnored(ValueError("v")))
        self.assertTrue(handler.isExceptionIgnored(KeyError("k")))
        self.assertFalse(handler.isExceptionIgnored(RuntimeError("r")))


class TestBaseExceptionHandlerLogging(TestCase):
    async def testReturnsCompletedPlanWhenNotIgnored(self) -> None:
        """Return a completed plan when the exception is not on the ignore list.

        Validates that the plan records completed logging through the supplied logger.

        Returns
        -------
        None
            No return value.
        """
        handler = _make_handler(dont_catch=frozenset())
        log = MagicMock()
        exc = RuntimeError("boom")
        result = await _complete(handler, exc, log)
        self.assertIsInstance(result, FailureHandling)
        self.assertTrue(result.reported)

    async def testCallsLogErrorWhenNotIgnored(self) -> None:
        """Invoke the native logger once when the exception is not ignored.

        Validate that the error record includes the class, message and
        explicit exception information without a separate traceback entry.

        Returns
        -------
        None
            No return value.
        """
        handler = _make_handler(dont_catch=frozenset())
        log = MagicMock(spec=ILogger)
        exc = RuntimeError("test error")
        await _complete(handler, exc, log)
        log.getLogger.assert_called_once_with()
        log.getLogger.return_value.error.assert_called_once_with(
            "[%s] %s",
            "RuntimeError",
            "test error",
            exc_info=(RuntimeError, exc, None),
        )
        log.error.assert_not_called()

    async def testLogsFullTracebackOutsideExcept(self) -> None:
        """Preserve the original traceback, full message and exception notes.

        Returns
        -------
        None
            Assertions verify the rendered error and original exception info.

        Raises
        ------
        ValueError
            Raised and caught to capture the original traceback.
        """
        handler = _make_handler()
        logger = logging.getLogger(__name__)
        log = MagicMock(spec=ILogger)
        log.getLogger.return_value = logger
        exc = ValueError("bad input", 42)
        exc.add_note("Request ID: test-request")
        try:
            raise exc
        except ValueError:
            pass

        with self.assertLogs(logger, level="ERROR") as captured:
            result = await _complete(handler, exc, log)

        self.assertTrue(result.reported)
        self.assertEqual(len(captured.records), 1)
        self.assertEqual(
            captured.records[0].exc_info,
            (ValueError, exc, exc.__traceback__),
        )
        output = captured.output[0]
        self.assertIn(f"[ValueError] {exc}", output)
        self.assertIn("Traceback (most recent call last):", output)
        self.assertIn(__file__, output)
        self.assertIn("testLogsFullTracebackOutsideExcept", output)
        self.assertIn("ValueError: ('bad input', 42)", output)
        self.assertIn("Request ID: test-request", output)

    async def testLogsExceptionChaining(self) -> None:
        """Preserve causes and context while respecting context suppression.

        Returns
        -------
        None
            Assertions verify native exception chaining in one error record.

        Raises
        ------
        RuntimeError
            Raised and caught with each supported chaining behavior.
        ValueError
            Raised and caught as the original failure.
        """
        handler = _make_handler()
        logger = logging.getLogger(__name__)
        log = MagicMock(spec=ILogger)
        log.getLogger.return_value = logger

        for chaining in ("cause", "context", "suppressed"):
            with self.subTest(chaining=chaining):
                exc = RuntimeError("operation failed")
                cause = ValueError("original failure")
                try:
                    try:
                        raise cause
                    except ValueError as caught:
                        if chaining == "cause":
                            raise exc from caught
                        if chaining == "suppressed":
                            raise exc from None
                        raise exc
                except RuntimeError:
                    pass

                with self.assertLogs(logger, level="ERROR") as captured:
                    await _complete(handler, exc, log)

                self.assertEqual(len(captured.records), 1)
                output = captured.output[0]
                self.assertIn("RuntimeError: operation failed", output)
                if chaining == "suppressed":
                    self.assertNotIn("ValueError: original failure", output)
                else:
                    self.assertIn("ValueError: original failure", output)
                    self.assertIn(
                        "direct cause"
                        if chaining == "cause"
                        else "During handling of the above exception",
                        output,
                    )

    async def testLogsNestedExceptionGroups(self) -> None:
        """Include nested exception groups, their individual errors and notes.

        Returns
        -------
        None
            Assertions verify the complete group in one error record.
        """
        handler = _make_handler()
        logger = logging.getLogger(__name__)
        log = MagicMock(spec=ILogger)
        log.getLogger.return_value = logger
        child = ValueError("invalid item")
        child.add_note("Item ID: 42")
        exc = ExceptionGroup(
            "batch failed",
            [child, ExceptionGroup("nested failure", [TypeError("wrong type")])],
        )

        with self.assertLogs(logger, level="ERROR") as captured:
            await _complete(handler, exc, log)

        self.assertEqual(len(captured.records), 1)
        output = captured.output[0]
        self.assertIn("ExceptionGroup: batch failed", output)
        self.assertIn("ExceptionGroup: nested failure", output)
        self.assertIn("ValueError: invalid item", output)
        self.assertIn("TypeError: wrong type", output)
        self.assertIn("Item ID: 42", output)

    async def testLogsSuppliedExceptionWithoutTraceback(self) -> None:
        """Log an unraised exception instead of an unrelated active exception.

        Returns
        -------
        None
            Assertions verify explicit exception info without a traceback.

        Raises
        ------
        ValueError
            Raised and caught to create an unrelated active exception.
        """
        handler = _make_handler()
        logger = logging.getLogger(__name__)
        log = MagicMock(spec=ILogger)
        log.getLogger.return_value = logger
        exc = RuntimeError("never raised")
        active = ValueError("unrelated active exception")
        try:
            raise active
        except ValueError:
            with self.assertLogs(logger, level="ERROR") as captured:
                await _complete(handler, exc, log)

        self.assertEqual(len(captured.records), 1)
        self.assertEqual(
            captured.records[0].exc_info,
            (RuntimeError, exc, None),
        )
        output = captured.output[0]
        self.assertIn("RuntimeError: never raised", output)
        self.assertNotIn("unrelated active exception", output)
        self.assertNotIn("NoneType: None", output)
        self.assertNotIn("No traceback available.", output)

    async def testIgnoredPlanDoesNotLog(self) -> None:
        """Return an empty plan when the exception type is ignored.

        Validates that the selected plan produces no side effects
        for exceptions listed in dont_catch.

        Returns
        -------
        None
            No return value.
        """
        handler = _make_handler(dont_catch=frozenset({ValueError}))
        log = MagicMock()
        exc = ValueError("ignored")
        result = await _complete(handler, exc, log)
        self.assertFalse(result.reported)
        self.assertIsNone(result.logging)
        self.assertIsNone(result.presentation)

    async def testDoesNotCallLogWhenIgnored(self) -> None:
        """Skip logging when the exception is on the ignore list.

        Validates that no logging side effects occur for silenced
        exception types.

        Returns
        -------
        None
            No return value.
        """
        handler = _make_handler(dont_catch=frozenset({ValueError}))
        log = MagicMock(spec=ILogger)
        exc = ValueError("silent")
        await _complete(handler, exc, log)
        log.error.assert_not_called()
        log.getLogger.assert_not_called()


class TestBaseExceptionHandlerCLIPresentation(TestCase):
    async def testCallsConsoleExceptionWhenNotIgnored(self) -> None:
        """Forward the exception to console.exception when not ignored.

        Validates that CLI presentation delegates output to the console so the
        error is visible in CLI sessions.

        Returns
        -------
        None
            No return value.
        """
        handler = _make_handler(dont_catch=frozenset())
        console = MagicMock()
        exc = RuntimeError("cli error")
        await _present(handler, exc, flow="cli", console=console)
        console.exception.assert_called_once_with(exc)

    async def testDoesNotCallConsoleWhenIgnored(self) -> None:
        """Skip console.exception when the exception type is ignored.

        Validates that CLI presentation produces no output for silenced
        exception types.

        Returns
        -------
        None
            No return value.
        """
        handler = _make_handler(dont_catch=frozenset({KeyError}))
        console = MagicMock()
        exc = KeyError("silent")
        await _present(handler, exc, flow="cli", console=console)
        console.exception.assert_not_called()

    async def testReturnsNone(self) -> None:
        """Return None from CLI presentation regardless of the exception.

        Validates that the method is purely a side-effect producer and
        never returns a meaningful value.

        Returns
        -------
        None
            No return value.
        """
        handler = _make_handler()
        console = MagicMock()
        result = await _present(handler, RuntimeError("x"), flow="cli", console=console)
        self.assertIsNone(result)


class TestBaseExceptionHandlerHTTPPresentationKnownExceptions(TestCase):
    def _makeRequestMock(self, *, wants_json: bool = False) -> MagicMock:
        """
        Build a mock that mimics a plain HTTP Request object.

        Parameters
        ----------
        wants_json : bool
            Whether wantsJson() should return True.

        Returns
        -------
        MagicMock
            Mock with path and method attributes and wantsJson callable.
        """
        req = MagicMock()
        req.wantsJson.return_value = wants_json
        req.path = "/test"
        req.method = "GET"
        # Ensure isinstance(req, TransportAdapter) returns False
        req.__class__ = MagicMock
        return req

    async def testRouteNotFoundReturns404(self) -> None:
        """Return a 404 error response for RouteNotFound exceptions.

        Validates that the predefined HTTP status map is consulted and
        the correct status code is forwarded to the default responses.

        Returns
        -------
        None
            No return value.
        """
        mock_responses = MagicMock(spec=IDefaultResponses)
        mock_responses.error.return_value = MagicMock(status_code=404)
        handler = BaseExceptionHandler(
            default_responses=mock_responses,
            application=_make_application(),
        )

        exc = RouteNotFound("not found")
        req = self._makeRequestMock()
        await _present(handler, exc, flow="http", request=req)

        mock_responses.error.assert_awaited_once()
        call_kwargs = mock_responses.error.call_args[1]
        self.assertEqual(call_kwargs["status_code"], 404)

    async def testMethodNotAllowedReturns405(self) -> None:
        """Return a 405 error response for MethodNotAllowed exceptions.

        Validates that the predefined HTTP status map is consulted and
        the correct status code is forwarded to the default responses.

        Returns
        -------
        None
            No return value.
        """
        mock_responses = MagicMock(spec=IDefaultResponses)
        mock_responses.error.return_value = MagicMock(status_code=405)
        handler = BaseExceptionHandler(
            default_responses=mock_responses,
            application=_make_application(),
        )

        exc = MethodNotAllowed("not allowed")
        req = self._makeRequestMock()
        await _present(handler, exc, flow="http", request=req)

        mock_responses.error.assert_awaited_once()
        call_kwargs = mock_responses.error.call_args[1]
        self.assertEqual(call_kwargs["status_code"], 405)

    async def testPayloadTooLargeReturns413(self) -> None:
        """Return a 413 error response for PayloadTooLargeException.

        Validates that the predefined HTTP status map is consulted and
        the correct status code is forwarded to the default responses.

        Returns
        -------
        None
            No return value.
        """
        mock_responses = MagicMock(spec=IDefaultResponses)
        mock_responses.error.return_value = MagicMock(status_code=413)
        handler = BaseExceptionHandler(
            default_responses=mock_responses,
            application=_make_application(),
        )

        exc = PayloadTooLargeException("too large")
        req = self._makeRequestMock()
        await _present(handler, exc, flow="http", request=req)

        mock_responses.error.assert_awaited_once()
        call_kwargs = mock_responses.error.call_args[1]
        self.assertEqual(call_kwargs["status_code"], 413)

    async def testUnsupportedMediaTypeReturns415(self) -> None:
        """Return a 415 error response for UnsupportedMediaTypeException.

        Validates that the predefined HTTP status map is consulted and
        the correct status code is forwarded to the default responses.

        Returns
        -------
        None
            No return value.
        """
        mock_responses = MagicMock(spec=IDefaultResponses)
        mock_responses.error.return_value = MagicMock(status_code=415)
        handler = BaseExceptionHandler(
            default_responses=mock_responses,
            application=_make_application(),
        )

        exc = UnsupportedMediaTypeException("unsupported")
        req = self._makeRequestMock()
        await _present(handler, exc, flow="http", request=req)

        mock_responses.error.assert_awaited_once()
        call_kwargs = mock_responses.error.call_args[1]
        self.assertEqual(call_kwargs["status_code"], 415)

    async def testCsrfTokenMismatchReturns419(self) -> None:
        """Return a 419 error response for CSRFTokenMismatchException.

        Validates that a rejected CSRF token is reported as an expired
        page instead of an unhandled server error.

        Returns
        -------
        None
            No return value.
        """
        mock_responses = MagicMock(spec=IDefaultResponses)
        mock_responses.error.return_value = MagicMock(status_code=419)
        handler = BaseExceptionHandler(
            default_responses=mock_responses,
            application=_make_application(),
        )

        exc = CSRFTokenMismatchException("token mismatch")
        req = self._makeRequestMock()
        await _present(handler, exc, flow="http", request=req)

        mock_responses.error.assert_awaited_once()
        call_kwargs = mock_responses.error.call_args[1]
        self.assertEqual(call_kwargs["status_code"], 419)

    async def testReturnsNoneForIgnoredException(self) -> None:
        """Return None without calling default_responses for ignored exceptions.

        Validates that HTTP presentation short-circuits and produces no response
        for exception types listed in dont_catch.

        Returns
        -------
        None
            No return value.
        """
        mock_responses = MagicMock(spec=IDefaultResponses)
        handler = type(
            "IgnoredRouteHandler",
            (BaseExceptionHandler,),
            {"dont_catch": frozenset({RouteNotFound})},
        )(mock_responses, _make_application())

        exc = RouteNotFound("ignored")
        req = self._makeRequestMock()
        result = await _present(handler, exc, flow="http", request=req)

        self.assertIsNone(result)
        mock_responses.error.assert_not_called()
        mock_responses.exception.assert_not_called()


class TestBaseExceptionHandlerHTTPPresentationGenericException(TestCase):
    async def testGenericExceptionCallsExceptionResponse(self) -> None:
        """Delegate to default_responses.exception for unmapped exceptions.

        Validates that any exception type not present in _HTTP_STATUS_MAP
        triggers the 500 exception-response path.

        Returns
        -------
        None
            No return value.
        """
        mock_responses = MagicMock(spec=IDefaultResponses)
        mock_responses.exception.return_value = MagicMock(status_code=500)
        handler = BaseExceptionHandler(
            default_responses=mock_responses,
            application=_make_application(),
        )

        exc = RuntimeError("unknown")
        req = MagicMock()
        req.wantsJson.return_value = False
        req.path = "/crash"
        req.method = "POST"
        req.__class__ = MagicMock

        await _present(handler, exc, flow="http", request=req)

        mock_responses.exception.assert_awaited_once()
        call_kwargs = mock_responses.exception.call_args[1]
        self.assertEqual(call_kwargs["status_code"], 500)

    async def testPassesExceptionObjectToExceptionResponse(self) -> None:
        """Supply the original exception object to default_responses.exception.

        Validates that the exception argument is forwarded unchanged so
        that response templates can render traceback details.

        Returns
        -------
        None
            No return value.
        """
        mock_responses = MagicMock(spec=IDefaultResponses)
        handler = BaseExceptionHandler(
            default_responses=mock_responses,
            application=_make_application(),
        )

        exc = RuntimeError("pass me through")
        req = MagicMock()
        req.wantsJson.return_value = False
        req.path = "/err"
        req.method = "GET"
        req.__class__ = MagicMock

        await _present(handler, exc, flow="http", request=req)

        call_kwargs = mock_responses.exception.call_args[1]
        self.assertIs(call_kwargs["exception"], exc)

    async def testWantsJsonPassedToErrorResponse(self) -> None:
        """Forward the wantsJson flag to the mapped error response builder.

        Validates that the request's content-type preference is respected
        when constructing 4xx responses from the status map.

        Returns
        -------
        None
            No return value.
        """
        mock_responses = MagicMock(spec=IDefaultResponses)
        handler = BaseExceptionHandler(
            default_responses=mock_responses,
            application=_make_application(),
        )

        exc = RouteNotFound("not found")
        req = MagicMock()
        req.wantsJson.return_value = True
        req.path = "/api"
        req.method = "GET"
        req.__class__ = MagicMock

        await _present(handler, exc, flow="http", request=req)

        call_kwargs = mock_responses.error.call_args[1]
        self.assertTrue(call_kwargs["expects_json"])


class TestBaseExceptionHandlerDontCatch(TestCase):
    def testDontCatchIsClassVar(self) -> None:
        """Confirm that dont_catch is a class-level attribute.

        Validates that dont_catch is accessible directly on the class
        without creating an instance.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(hasattr(BaseExceptionHandler, "dont_catch"))

    def testDontCatchDefaultIsEmptyFrozenset(self) -> None:
        """Confirm that dont_catch defaults to an empty frozenset.

        Validates the out-of-the-box behavior where every exception
        is considered reportable.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(BaseExceptionHandler.dont_catch, frozenset())

    def testDontCatchIsFrozenset(self) -> None:
        """Confirm that dont_catch is of type frozenset.

        Validates the type contract so downstream code can rely on
        O(1) membership testing with no mutation risk.

        Returns
        -------
        None
            No return value.
        """
        self.assertIsInstance(BaseExceptionHandler.dont_catch, frozenset)


class TestBaseExceptionHandlerPolicy(TestCase):
    """Select effects once without executing them inside the observation hook."""

    async def testObservationDefersLoggingAndPresentation(self) -> None:
        """Verify observation defers logging and presentation.

        Returning the default plan cannot log before custom policy finishes.
        """
        application = _make_application()
        logger = MagicMock(spec=ILogger)
        application.make = AsyncMock(return_value=logger)
        responses = MagicMock(spec=IDefaultResponses)
        handler = BaseExceptionHandler(responses, application)
        handling = await handler.handleFailure(ValueError("original"), FailureContext())
        application.make.assert_not_called()
        responses.exception.assert_not_called()
        await handling.complete()
        logger.getLogger.return_value.error.assert_called_once()
        responses.exception.assert_not_called()

    async def testExpectedAndClosedLoggerContextsDoNotResolveLogger(self) -> None:
        """Verify expected and closed logger contexts do not resolve logger.

        Both policy gates keep deferred presentation available without logging.
        """
        for context in (
            FailureContext(expected=True),
            FailureContext(reporting_allowed=False),
        ):
            with self.subTest(context=context):
                application = _make_application()
                application.make = AsyncMock()
                responses = MagicMock(spec=IDefaultResponses)
                handler = BaseExceptionHandler(responses, application)
                plan = await handler.handleFailure(ValueError("expected"), context)
                await plan.complete()
                self.assertFalse(plan.reported)
                self.assertIsNotNone(plan.presentation)
                application.make.assert_not_called()

    async def testDefaultFailedResultHasNoLoggingOrPresentation(self) -> None:
        """Verify default failed result has no logging or presentation.

        A declared result keeps protocol ownership and gains no fake exception.
        """
        application = _make_application()
        responses = MagicMock(spec=IDefaultResponses)
        handler = BaseExceptionHandler(responses, application)
        self.assertIsNone(await handler.handleResult(7, FailureContext(flow="cli")))
        application.make.assert_not_called()
        responses.exception.assert_not_called()
