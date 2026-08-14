from __future__ import annotations
from unittest.mock import MagicMock
from orionis.failure.base.handler import BaseExceptionHandler
from orionis.failure.entities.throwable import Throwable
from orionis.http.payload.body import PayloadTooLargeException
from orionis.http.request import UnsupportedMediaTypeException
from orionis.http.layer.web.exceptions import CSRFTokenMismatchException
from orionis.http.routes.exceptions.method_not_allowed import MethodNotAllowed
from orionis.http.routes.exceptions.route_not_found import RouteNotFound
from orionis.test import TestCase

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
    mock_responses = MagicMock()
    handler = BaseExceptionHandler(default_responses=mock_responses)
    if dont_catch is not None:
        type(handler).dont_catch = dont_catch  # type: ignore[assignment]
    return handler

class TestBaseExceptionHandlerToThrowable(TestCase):

    def testConvertsExceptionToThrowable(self) -> None:
        """
        Convert a standard exception into a Throwable structure.

        Validates that toThrowable returns a Throwable whose classtype,
        message, and args fields reflect the supplied exception.
        """
        handler = _make_handler()
        exc = ValueError("bad input")
        result = handler.toThrowable(exc)
        self.assertIsInstance(result, Throwable)
        self.assertIs(result.classtype, ValueError)
        self.assertEqual(result.message, "bad input")

    def testArgsAreStringified(self) -> None:
        """
        Stringify all exception arguments inside the Throwable args tuple.

        Validates that every element in the resulting args tuple is a str,
        regardless of the original argument type.
        """
        handler = _make_handler()
        exc = TypeError(42, "extra")
        result = handler.toThrowable(exc)
        for arg in result.args:
            self.assertIsInstance(arg, str)

    def testSingleMessageArgMatchesFirstArg(self) -> None:
        """
        Set the message field to the first stringified exception argument.

        Validates that the message matches args[0] when the exception
        carries exactly one argument.
        """
        handler = _make_handler()
        exc = RuntimeError("runtime failure")
        result = handler.toThrowable(exc)
        self.assertEqual(result.message, result.args[0])

    def testNoArgsProducesEmptyStringMessage(self) -> None:
        """
        Produce an empty-string message for zero-argument exceptions.

        Validates the fallback path when exception.args is empty, so the
        message field is always a string.
        """
        handler = _make_handler()
        exc = Exception()
        result = handler.toThrowable(exc)
        self.assertEqual(result.message, "")

    def testTracebackIsNoneWhenNoExceptionRaised(self) -> None:
        """
        Store None in the traceback field for exceptions not yet raised.

        Validates that constructing an exception without raising it leaves
        __traceback__ as None, which is propagated faithfully.
        """
        handler = _make_handler()
        exc = OSError("no tb")
        result = handler.toThrowable(exc)
        self.assertIsNone(result.traceback)

    def testTracebackCapturedAfterRaise(self) -> None:
        """
        Capture a live traceback when the exception has been raised.

        Validates that toThrowable faithfully stores __traceback__ when
        the exception was actually raised, enabling downstream reporting.
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
        self.assertIsNotNone(result.traceback)

class TestBaseExceptionHandlerIsExceptionIgnored(TestCase):

    def tearDown(self) -> None:
        """
        Reset dont_catch to the original frozenset after each test.

        Ensures that class-level mutation in individual tests does not
        bleed across the test suite.
        """
        BaseExceptionHandler.dont_catch = frozenset()

    def testReturnsFalseWhenDontCatchIsEmpty(self) -> None:
        """
        Return False for any exception when dont_catch is an empty frozenset.

        Validates the default behavior where all exceptions are considered
        reportable.
        """
        handler = _make_handler(dont_catch=frozenset())
        exc = ValueError("x")
        self.assertFalse(handler.isExceptionIgnored(exc))

    def testReturnsTrueWhenExceptionTypeInDontCatch(self) -> None:
        """
        Return True when the exception type is listed in dont_catch.

        Validates that the membership check uses type identity so that
        exceptions on the ignore-list are not reported.
        """
        handler = _make_handler(dont_catch=frozenset({ValueError}))
        exc = ValueError("ignored")
        self.assertTrue(handler.isExceptionIgnored(exc))

    def testReturnsFalseForSubclassNotInDontCatch(self) -> None:
        """
        Return False for a subclass whose base is in dont_catch.

        Validates that the check uses exact type membership, not
        isinstance, so subclasses are not automatically silenced.
        """

        class _Sub(ValueError):
            pass

        handler = _make_handler(dont_catch=frozenset({ValueError}))
        exc = _Sub("sub")
        self.assertFalse(handler.isExceptionIgnored(exc))

    def testRaisesTypeErrorForNonException(self) -> None:
        """
        Raise TypeError when the argument is not a BaseException.

        Validates the guard that prevents non-exception objects from
        passing through the ignore-list check unnoticed.
        """
        handler = _make_handler()
        with self.assertRaises(TypeError):
            handler.isExceptionIgnored("not an exception")  # type: ignore[arg-type]

    def testMultipleTypesInDontCatch(self) -> None:
        """
        Recognise each listed type individually in a populated dont_catch.

        Validates that having multiple exception types in dont_catch works
        correctly for every member.
        """
        handler = _make_handler(dont_catch=frozenset({ValueError, KeyError}))
        self.assertTrue(handler.isExceptionIgnored(ValueError("v")))
        self.assertTrue(handler.isExceptionIgnored(KeyError("k")))
        self.assertFalse(handler.isExceptionIgnored(RuntimeError("r")))

class TestBaseExceptionHandlerReport(TestCase):

    def tearDown(self) -> None:
        """
        Reset dont_catch to the original frozenset after each test.

        Ensures that class-level mutation in individual tests does not
        bleed across the test suite.
        """
        BaseExceptionHandler.dont_catch = frozenset()

    async def testReturnsThrowableWhenNotIgnored(self) -> None:
        """
        Return a Throwable when the exception is not on the ignore list.

        Validates that report converts and returns the exception details
        after logging them through the supplied logger.
        """
        handler = _make_handler(dont_catch=frozenset())
        log = MagicMock()
        exc = RuntimeError("boom")
        result = await handler.report(exc, log)
        self.assertIsInstance(result, Throwable)

    async def testCallsLogErrorWhenNotIgnored(self) -> None:
        """
        Invoke log.error exactly once when the exception is not ignored.

        Validates that the logger receives one call containing both the
        exception class name and the message.
        """
        handler = _make_handler(dont_catch=frozenset())
        log = MagicMock()
        exc = RuntimeError("test error")
        await handler.report(exc, log)
        log.error.assert_called_once()
        call_args = log.error.call_args[0][0]
        self.assertIn("RuntimeError", call_args)
        self.assertIn("test error", call_args)

    async def testReturnsNoneWhenIgnored(self) -> None:
        """
        Return None without logging when the exception type is ignored.

        Validates that report short-circuits and produces no side effects
        for exceptions listed in dont_catch.
        """
        handler = _make_handler(dont_catch=frozenset({ValueError}))
        log = MagicMock()
        exc = ValueError("ignored")
        result = await handler.report(exc, log)
        self.assertIsNone(result)

    async def testDoesNotCallLogWhenIgnored(self) -> None:
        """
        Skip the log.error call when the exception is on the ignore list.

        Validates that no logging side effects occur for silenced
        exception types.
        """
        handler = _make_handler(dont_catch=frozenset({ValueError}))
        log = MagicMock()
        exc = ValueError("silent")
        await handler.report(exc, log)
        log.error.assert_not_called()

class TestBaseExceptionHandlerHandleCLI(TestCase):

    def tearDown(self) -> None:
        """
        Reset dont_catch to the original frozenset after each test.

        Ensures that class-level mutation in individual tests does not
        bleed across the test suite.
        """
        BaseExceptionHandler.dont_catch = frozenset()

    async def testCallsConsoleExceptionWhenNotIgnored(self) -> None:
        """
        Forward the exception to console.exception when not ignored.

        Validates that handleCLI delegates output to the console so the
        error is visible in CLI sessions.
        """
        handler = _make_handler(dont_catch=frozenset())
        console = MagicMock()
        exc = RuntimeError("cli error")
        await handler.handleCLI(exc, console)
        console.exception.assert_called_once_with(exc)

    async def testDoesNotCallConsoleWhenIgnored(self) -> None:
        """
        Skip console.exception when the exception type is ignored.

        Validates that handleCLI produces no output for silenced
        exception types.
        """
        handler = _make_handler(dont_catch=frozenset({KeyError}))
        console = MagicMock()
        exc = KeyError("silent")
        await handler.handleCLI(exc, console)
        console.exception.assert_not_called()

    async def testReturnsNone(self) -> None:
        """
        Return None from handleCLI regardless of the exception.

        Validates that the method is purely a side-effect producer and
        never returns a meaningful value.
        """
        handler = _make_handler()
        console = MagicMock()
        result = await handler.handleCLI(RuntimeError("x"), console)
        self.assertIsNone(result)

class TestBaseExceptionHandlerHandleHTTPKnownExceptions(TestCase):

    def tearDown(self) -> None:
        """
        Reset dont_catch to the original frozenset after each test.

        Ensures that class-level mutation in individual tests does not
        bleed across the test suite.
        """
        BaseExceptionHandler.dont_catch = frozenset()

    def _make_request_mock(self, *, wants_json: bool = False) -> MagicMock:
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
        """
        Return a 404 error response for RouteNotFound exceptions.

        Validates that the predefined HTTP status map is consulted and
        the correct status code is forwarded to the default responses.
        """
        mock_responses = MagicMock()
        mock_responses.error.return_value = MagicMock(status_code=404)
        handler = BaseExceptionHandler(default_responses=mock_responses)

        exc = RouteNotFound("not found")
        req = self._make_request_mock()
        await handler.handleHTTP(exc, req)

        mock_responses.error.assert_called_once()
        call_kwargs = mock_responses.error.call_args[1]
        self.assertEqual(call_kwargs["status_code"], 404)

    async def testMethodNotAllowedReturns405(self) -> None:
        """
        Return a 405 error response for MethodNotAllowed exceptions.

        Validates that the predefined HTTP status map is consulted and
        the correct status code is forwarded to the default responses.
        """
        mock_responses = MagicMock()
        mock_responses.error.return_value = MagicMock(status_code=405)
        handler = BaseExceptionHandler(default_responses=mock_responses)

        exc = MethodNotAllowed("not allowed")
        req = self._make_request_mock()
        await handler.handleHTTP(exc, req)

        mock_responses.error.assert_called_once()
        call_kwargs = mock_responses.error.call_args[1]
        self.assertEqual(call_kwargs["status_code"], 405)

    async def testPayloadTooLargeReturns413(self) -> None:
        """
        Return a 413 error response for PayloadTooLargeException.

        Validates that the predefined HTTP status map is consulted and
        the correct status code is forwarded to the default responses.
        """
        mock_responses = MagicMock()
        mock_responses.error.return_value = MagicMock(status_code=413)
        handler = BaseExceptionHandler(default_responses=mock_responses)

        exc = PayloadTooLargeException("too large")
        req = self._make_request_mock()
        await handler.handleHTTP(exc, req)

        mock_responses.error.assert_called_once()
        call_kwargs = mock_responses.error.call_args[1]
        self.assertEqual(call_kwargs["status_code"], 413)

    async def testUnsupportedMediaTypeReturns415(self) -> None:
        """
        Return a 415 error response for UnsupportedMediaTypeException.

        Validates that the predefined HTTP status map is consulted and
        the correct status code is forwarded to the default responses.
        """
        mock_responses = MagicMock()
        mock_responses.error.return_value = MagicMock(status_code=415)
        handler = BaseExceptionHandler(default_responses=mock_responses)

        exc = UnsupportedMediaTypeException("unsupported")
        req = self._make_request_mock()
        await handler.handleHTTP(exc, req)

        mock_responses.error.assert_called_once()
        call_kwargs = mock_responses.error.call_args[1]
        self.assertEqual(call_kwargs["status_code"], 415)

    async def testCsrfTokenMismatchReturns419(self) -> None:
        """
        Return a 419 error response for CSRFTokenMismatchException.

        Validates that a rejected CSRF token is reported as an expired
        page instead of an unhandled server error.
        """
        mock_responses = MagicMock()
        mock_responses.error.return_value = MagicMock(status_code=419)
        handler = BaseExceptionHandler(default_responses=mock_responses)

        exc = CSRFTokenMismatchException("token mismatch")
        req = self._make_request_mock()
        await handler.handleHTTP(exc, req)

        mock_responses.error.assert_called_once()
        call_kwargs = mock_responses.error.call_args[1]
        self.assertEqual(call_kwargs["status_code"], 419)

    async def testReturnsNoneForIgnoredException(self) -> None:
        """
        Return None without calling default_responses for ignored exceptions.

        Validates that handleHTTP short-circuits and produces no response
        for exception types listed in dont_catch.
        """
        mock_responses = MagicMock()
        handler = BaseExceptionHandler(default_responses=mock_responses)
        type(handler).dont_catch = frozenset({RouteNotFound})  # type: ignore[assignment]

        exc = RouteNotFound("ignored")
        req = self._make_request_mock()
        result = await handler.handleHTTP(exc, req)

        self.assertIsNone(result)
        mock_responses.error.assert_not_called()
        mock_responses.exception.assert_not_called()

class TestBaseExceptionHandlerHandleHTTPGenericException(TestCase):

    def tearDown(self) -> None:
        """
        Reset dont_catch to the original frozenset after each test.

        Ensures that class-level mutation in individual tests does not
        bleed across the test suite.
        """
        BaseExceptionHandler.dont_catch = frozenset()

    async def testGenericExceptionCallsExceptionResponse(self) -> None:
        """
        Delegate to default_responses.exception for unmapped exceptions.

        Validates that any exception type not present in _HTTP_STATUS_MAP
        triggers the 500 exception-response path.
        """
        mock_responses = MagicMock()
        mock_responses.exception.return_value = MagicMock(status_code=500)
        handler = BaseExceptionHandler(default_responses=mock_responses)

        exc = RuntimeError("unknown")
        req = MagicMock()
        req.wantsJson.return_value = False
        req.path = "/crash"
        req.method = "POST"
        req.__class__ = MagicMock

        await handler.handleHTTP(exc, req)

        mock_responses.exception.assert_called_once()
        call_kwargs = mock_responses.exception.call_args[1]
        self.assertEqual(call_kwargs["status_code"], 500)

    async def testPassesExceptionObjectToExceptionResponse(self) -> None:
        """
        Supply the original exception object to default_responses.exception.

        Validates that the exception argument is forwarded unchanged so
        that response templates can render traceback details.
        """
        mock_responses = MagicMock()
        handler = BaseExceptionHandler(default_responses=mock_responses)

        exc = RuntimeError("pass me through")
        req = MagicMock()
        req.wantsJson.return_value = False
        req.path = "/err"
        req.method = "GET"
        req.__class__ = MagicMock

        await handler.handleHTTP(exc, req)

        call_kwargs = mock_responses.exception.call_args[1]
        self.assertIs(call_kwargs["exception"], exc)

    async def testWantsJsonPassedToErrorResponse(self) -> None:
        """
        Forward the wantsJson flag to the mapped error response builder.

        Validates that the request's content-type preference is respected
        when constructing 4xx responses from the status map.
        """
        mock_responses = MagicMock()
        handler = BaseExceptionHandler(default_responses=mock_responses)

        exc = RouteNotFound("not found")
        req = MagicMock()
        req.wantsJson.return_value = True
        req.path = "/api"
        req.method = "GET"
        req.__class__ = MagicMock

        await handler.handleHTTP(exc, req)

        call_kwargs = mock_responses.error.call_args[1]
        self.assertTrue(call_kwargs["expects_json"])

class TestBaseExceptionHandlerDontCatch(TestCase):

    def tearDown(self) -> None:
        """
        Reset dont_catch to the original frozenset after each test.

        Ensures that class-level mutation in individual tests does not
        bleed across the test suite.
        """
        BaseExceptionHandler.dont_catch = frozenset()

    def testDontCatchIsClassVar(self) -> None:
        """
        Confirm that dont_catch is a class-level attribute.

        Validates that dont_catch is accessible directly on the class
        without creating an instance.
        """
        self.assertTrue(hasattr(BaseExceptionHandler, "dont_catch"))

    def testDontCatchDefaultIsEmptyFrozenset(self) -> None:
        """
        Confirm that dont_catch defaults to an empty frozenset.

        Validates the out-of-the-box behavior where every exception
        is considered reportable.
        """
        self.assertEqual(BaseExceptionHandler.dont_catch, frozenset())

    def testDontCatchIsFrozenset(self) -> None:
        """
        Confirm that dont_catch is of type frozenset.

        Validates the type contract so downstream code can rely on
        O(1) membership testing with no mutation risk.
        """
        self.assertIsInstance(BaseExceptionHandler.dont_catch, frozenset)
