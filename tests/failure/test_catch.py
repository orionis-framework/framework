from __future__ import annotations
import asyncio
import inspect
from unittest.mock import AsyncMock, MagicMock
from typing import get_args
from orionis.failure.catch import Catch
from orionis.failure.contracts.catch import ICatch
from orionis.failure.enums.kernel_type import KernelContext
from orionis.http.adapters.request.contracts.transport import TransportAdapter
from orionis.test import TestCase

# Minimum number of positional args expected in app.call(handler, method, ...)
_CALL_MIN_POSITIONAL = 2

def _make_catch(
    scope: object | None = None,
    kernel: object | None = None,
    exception_handler: object | None = None,
) -> Catch:
    """
    Build a Catch instance backed by a fully mocked IApplication.

    Parameters
    ----------
    scope : object or None
        Value returned by app.getCurrentScope(); None simulates no scope.
    kernel : object or None
        Value returned by scope.get('kernel'); None simulates no kernel.
    exception_handler : object or None
        Value returned by app.getExceptionHandler().

    Returns
    -------
    Catch
        A Catch instance ready for testing.
    """
    mock_scope = AsyncMock()
    mock_scope.get = AsyncMock(return_value=kernel)

    mock_app = MagicMock()
    mock_app.getCurrentScope.return_value = scope if scope is not None else mock_scope
    mock_app.getExceptionHandler = AsyncMock(return_value=exception_handler)
    mock_app.call = AsyncMock(return_value=None)

    return Catch(app=mock_app)

class TestCatchIsICatch(TestCase):

    def testIsSubclassOfICatch(self) -> None:
        """Confirm that Catch is a subclass of ICatch.

        Validates the interface contract so that the dependency injection
        container can resolve ICatch to Catch transparently.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(Catch, ICatch))

    def testExceptionMethodIsCoroutine(self) -> None:
        """Confirm that the exception method is a coroutine function.

        Validates that callers can safely await Catch.exception without
        any additional async wrapping.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(inspect.iscoroutinefunction(Catch.exception))

    def testRequestAnnotationIncludesTransportAdapter(self) -> None:
        """Keep the transport request type available to runtime inspection.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        annotation = inspect.signature(Catch.exception).parameters["request"].annotation
        self.assertIn(TransportAdapter, get_args(annotation))

class TestCatchNoScope(TestCase):

    async def testRaisesRuntimeErrorWhenNoScope(self) -> None:
        """Raise RuntimeError when no active application scope is found.

        Validates the guard that prevents exception handling from
        continuing without a valid scope, signalling a misconfiguration.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        mock_app = MagicMock()
        mock_app.getCurrentScope.return_value = None
        mock_app.getExceptionHandler = AsyncMock(return_value=MagicMock())
        mock_app.call = AsyncMock(return_value=None)

        catch = Catch(app=mock_app)
        with self.assertRaises(RuntimeError):
            await catch.exception(RuntimeError("no scope"))

class TestCatchNoKernel(TestCase):

    async def testRaisesRuntimeErrorWhenNoKernel(self) -> None:
        """Raise RuntimeError when the scope contains no kernel entry.

        Validates the guard that prevents exception handling from
        continuing without an identified kernel context.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        mock_scope = AsyncMock()
        mock_scope.get = AsyncMock(return_value=None)

        mock_app = MagicMock()
        mock_app.getCurrentScope.return_value = mock_scope
        mock_app.getExceptionHandler = AsyncMock(return_value=MagicMock())
        mock_app.call = AsyncMock(return_value=None)

        catch = Catch(app=mock_app)
        with self.assertRaises(RuntimeError):
            await catch.exception(RuntimeError("no kernel"))

class TestCatchConsoleContext(TestCase):

    async def testDelegatesHandleCLIInConsoleContext(self) -> None:
        """Invoke the handler's handleCLI path in a CONSOLE kernel context.

        Validates that when the current scope identifies the CONSOLE kernel
        the app.call dispatcher is directed to handleCLI.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        mock_scope = AsyncMock()
        mock_scope.get = AsyncMock(return_value=KernelContext.CONSOLE)

        handler = MagicMock()
        mock_app = MagicMock()
        mock_app.getCurrentScope.return_value = mock_scope
        mock_app.getExceptionHandler = AsyncMock(return_value=handler)
        mock_app.call = AsyncMock(return_value=None)

        catch = Catch(app=mock_app)
        exc = RuntimeError("console error")
        await catch.exception(exc)

        calls = mock_app.call.call_args_list
        method_names = [
            c[0][1]
            for c in calls
            if len(c[0]) >= _CALL_MIN_POSITIONAL
        ]
        self.assertIn("handleCLI", method_names)

    async def testCallsReportBeforeHandleCLI(self) -> None:
        """Invoke report before handleCLI in the CONSOLE context.

        Validates the expected call ordering so that exceptions are always
        logged prior to being rendered in the CLI.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        mock_scope = AsyncMock()
        mock_scope.get = AsyncMock(return_value=KernelContext.CONSOLE)

        handler = MagicMock()
        call_order: list[str] = []

        async def _track_call(
            _obj: object, method: str, **_kwargs: object,
        ) -> None:
            """Record the dispatched handler method.

            Parameters
            ----------
            _obj : object
                Value supplied for ``_obj``.
            method : str
                Value supplied for ``method``.
            **_kwargs : object
                Arguments passed to the wrapped callable.

            Returns
            -------
            None
                Completes the operation described above.
            """
            call_order.append(method)

        mock_app = MagicMock()
        mock_app.getCurrentScope.return_value = mock_scope
        mock_app.getExceptionHandler = AsyncMock(return_value=handler)
        mock_app.call = _track_call  # type: ignore[assignment]

        catch = Catch(app=mock_app)
        await catch.exception(RuntimeError("ordered"))

        self.assertEqual(call_order[0], "report")
        self.assertEqual(call_order[1], "handleCLI")

class TestCatchHTTPContext(TestCase):

    async def testDelegatesHandleHTTPInHTTPContext(self) -> None:
        """Invoke the handler's handleHTTP path in an HTTP kernel context.

        Validates that when the current scope identifies the HTTP kernel
        the app.call dispatcher is directed to handleHTTP.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        mock_scope = AsyncMock()
        mock_scope.get = AsyncMock(return_value=KernelContext.HTTP)

        handler = MagicMock()
        mock_app = MagicMock()
        mock_app.getCurrentScope.return_value = mock_scope
        mock_app.getExceptionHandler = AsyncMock(return_value=handler)
        mock_app.call = AsyncMock(return_value=None)

        catch = Catch(app=mock_app)
        req = MagicMock()
        exc = RuntimeError("http error")
        await catch.exception(exc, request=req)

        calls = mock_app.call.call_args_list
        method_names = [
            c[0][1]
            for c in calls
            if len(c[0]) >= _CALL_MIN_POSITIONAL
        ]
        self.assertIn("handleHTTP", method_names)

    async def testCallsReportBeforeHandleHTTP(self) -> None:
        """Invoke report before handleHTTP in the HTTP context.

        Validates the expected call ordering so that exceptions are always
        logged prior to being rendered as HTTP error responses.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        mock_scope = AsyncMock()
        mock_scope.get = AsyncMock(return_value=KernelContext.HTTP)

        handler = MagicMock()
        call_order: list[str] = []

        async def _track_call(
            _obj: object, method: str, **_kwargs: object,
        ) -> None:
            """Record the dispatched handler method.

            Parameters
            ----------
            _obj : object
                Value supplied for ``_obj``.
            method : str
                Value supplied for ``method``.
            **_kwargs : object
                Arguments passed to the wrapped callable.

            Returns
            -------
            None
                Completes the operation described above.
            """
            call_order.append(method)

        mock_app = MagicMock()
        mock_app.getCurrentScope.return_value = mock_scope
        mock_app.getExceptionHandler = AsyncMock(return_value=handler)
        mock_app.call = _track_call  # type: ignore[assignment]

        catch = Catch(app=mock_app)
        await catch.exception(ValueError("ordered http"))

        self.assertEqual(call_order[0], "report")
        self.assertEqual(call_order[1], "handleHTTP")

    async def testPassesRequestToHandleHTTP(self) -> None:
        """Forward the request argument when dispatching handleHTTP.

        Validates that the request object supplied to exception() is
        propagated through app.call to the handler.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        mock_scope = AsyncMock()
        mock_scope.get = AsyncMock(return_value=KernelContext.HTTP)

        handler = MagicMock()
        mock_app = MagicMock()
        mock_app.getCurrentScope.return_value = mock_scope
        mock_app.getExceptionHandler = AsyncMock(return_value=handler)
        mock_app.call = AsyncMock(return_value=None)

        catch = Catch(app=mock_app)
        req = MagicMock()
        await catch.exception(RuntimeError("with req"), request=req)

        http_call = next(
            c
            for c in mock_app.call.call_args_list
            if len(c[0]) >= _CALL_MIN_POSITIONAL and c[0][1] == "handleHTTP"
        )
        self.assertIs(http_call[1]["request"], req)

class TestCatchUnknownContext(TestCase):

    async def testReturnsNoneForUnknownContext(self) -> None:
        """Return None when the kernel context is not CONSOLE or HTTP.

        Validates the fallback path so that unrecognised kernel types do
        not raise an unhandled exception.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        mock_scope = AsyncMock()
        mock_scope.get = AsyncMock(return_value="UNKNOWN_CONTEXT")

        handler = MagicMock()
        mock_app = MagicMock()
        mock_app.getCurrentScope.return_value = mock_scope
        mock_app.getExceptionHandler = AsyncMock(return_value=handler)
        mock_app.call = AsyncMock(return_value=None)

        catch = Catch(app=mock_app)
        result = await catch.exception(RuntimeError("unknown ctx"))
        self.assertIsNone(result)

    async def testHandlerCachedAcrossCalls(self) -> None:
        """Resolve the exception handler only once across multiple calls.

        Validates that the handler is cached so that getExceptionHandler
        is not invoked on every exception dispatch.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        mock_scope = AsyncMock()
        mock_scope.get = AsyncMock(return_value=KernelContext.CONSOLE)

        handler = MagicMock()
        mock_app = MagicMock()
        mock_app.getCurrentScope.return_value = mock_scope
        mock_app.getExceptionHandler = AsyncMock(return_value=handler)
        mock_app.call = AsyncMock(return_value=None)

        catch = Catch(app=mock_app)
        await catch.exception(RuntimeError("first"))
        await catch.exception(RuntimeError("second"))

        self.assertEqual(mock_app.getExceptionHandler.call_count, 1)

    async def testHandlerResolutionIsSharedAcrossConcurrentCalls(self) -> None:
        """Resolve the shared handler once when first use overlaps.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        mock_scope = AsyncMock()
        mock_scope.get = AsyncMock(return_value=KernelContext.CONSOLE)

        handler = MagicMock()

        async def resolve_handler():
            """Wait for overlapping calls before returning the handler.

            Returns
            -------
            object
                Value produced by the helper.
            """
            await asyncio.sleep(0)
            return handler

        mock_app = MagicMock()
        mock_app.getCurrentScope.return_value = mock_scope
        mock_app.getExceptionHandler = AsyncMock(side_effect=resolve_handler)
        mock_app.call = AsyncMock(return_value=None)

        catch = Catch(app=mock_app)
        await asyncio.gather(*(
            catch.exception(RuntimeError("concurrent"))
            for _ in range(8)
        ))

        mock_app.getExceptionHandler.assert_awaited_once()
