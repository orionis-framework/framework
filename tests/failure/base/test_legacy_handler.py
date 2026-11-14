# ruff: noqa: PT009
# Preserve native TestCase assertions and warning capture.
"""Keep existing application handlers usable while their hooks are deprecated."""

from __future__ import annotations

import logging
import warnings
from typing import TYPE_CHECKING, ClassVar
from unittest.mock import AsyncMock, MagicMock, patch

from orionis.auth.exceptions import AuthenticationException
from orionis.failure.base.handler import BaseExceptionHandler
from orionis.failure.entities.context import FailureContext
from orionis.failure.entities.throwable import Throwable
from orionis.http.adapters.request.contracts.transport import TransportAdapter
from orionis.http.default.contracts.responses import IDefaultResponses
from orionis.http.routes.exceptions.route_not_found import RouteNotFound
from orionis.logging.contracts.logger import ILogger
from orionis.test import TestCase

if TYPE_CHECKING:
    from orionis.console.output.console import Console
    from orionis.http.request import Request
    from orionis.http.responses import Response


class _LegacyHandler(BaseExceptionHandler):
    """Represent the application template that delegates each hook to super."""

    async def report(self, exception: Exception, log: ILogger) -> Throwable | None:
        """Delegate reporting through the existing application signature."""
        return await super().report(exception, log)

    async def handleCLI(self, exception: Exception, console: Console) -> None:
        """Delegate CLI output through the existing application signature."""
        return await super().handleCLI(exception, console)

    async def handleHTTP(
        self,
        exception: Exception,
        request: Request,
    ) -> Response | None:
        """Delegate HTTP output through the existing application signature."""
        return await super().handleHTTP(exception, request)


class _IgnoredLegacyHandler(_LegacyHandler):
    """Keep the original per-application ignore configuration."""

    dont_catch: ClassVar[frozenset[type[BaseException]]] = frozenset({ValueError})


class TestLegacyExceptionHandler(TestCase):
    """Exercise caller-visible compatibility and deprecation diagnostics."""

    def setUp(self) -> None:
        """Create isolated dependencies without booting an application."""
        self.application = MagicMock()
        self.application.config.return_value = True
        self.responses = MagicMock(spec=IDefaultResponses)
        self.handler = _LegacyHandler(self.responses, self.application)

    async def testReportReturnsThrowableAndPreservesOriginalTraceback(self) -> None:
        """Log once through the supplied logger and return structured details.

        Raises
        ------
        ValueError
            Caught to give the reported exception a real traceback.
        """
        exception = ValueError("bad input", 42)
        try:
            raise exception
        except ValueError:
            traceback = exception.__traceback__
        logger = logging.getLogger(__name__)
        service = MagicMock(spec=ILogger)
        service.getLogger.return_value = logger

        with (
            self.assertWarnsRegex(DeprecationWarning, "report") as warning,
            self.assertLogs(logger, level="ERROR") as captured,
        ):
            result = await self.handler.report(exception, service)

        self.assertIsInstance(result, Throwable)
        self.assertIs(result.classtype, ValueError)
        self.assertEqual(result.message, str(exception))
        self.assertEqual(result.args, ("bad input", "42"))
        self.assertIs(result.traceback, traceback)
        self.assertEqual(len(captured.records), 1)
        self.assertEqual(captured.records[0].getMessage(), f"[ValueError] {exception}")
        self.assertEqual(
            captured.records[0].exc_info, (ValueError, exception, traceback),
        )
        self.assertEqual(warning.filename, __file__)
        self.assertIn("deprecated", str(warning.warning))
        self.assertIn("future", str(warning.warning))
        self.assertIn("handleFailure", str(warning.warning))
        self.application.make.assert_not_called()

    async def testCLIUsesSuppliedConsoleAndReturnsNone(self) -> None:
        """Preserve immediate CLI output and identify the application call site."""
        exception = RuntimeError("cli failure")
        console = MagicMock()
        with self.assertWarnsRegex(DeprecationWarning, "handleCLI") as warning:
            result = await self.handler.handleCLI(exception, console)
        self.assertIsNone(result)
        console.exception.assert_called_once_with(exception)
        self.assertEqual(warning.filename, __file__)
        self.application.make.assert_not_called()

    async def testIgnoredExceptionsStillWarnWithoutSideEffects(self) -> None:
        """Return None for every ignored legacy call while announcing removal."""
        handler = _IgnoredLegacyHandler(self.responses, self.application)
        for method in ("report", "handleCLI", "handleHTTP"):
            with self.subTest(method=method):
                dependency = MagicMock()
                with self.assertWarnsRegex(DeprecationWarning, method) as warning:
                    result = await getattr(handler, method)(
                        ValueError("ignored"), dependency,
                    )
                self.assertIsNone(result)
                self.assertEqual(dependency.mock_calls, [])
                self.assertIn("future", str(warning.warning))
                self.assertIn("handleFailure", str(warning.warning))
        self.assertEqual(self.responses.mock_calls, [])
        self.assertEqual(self.application.mock_calls, [])

    async def testHTTPPreservesKnownStatusInDebugAndProduction(self) -> None:
        """Return the original response and preserve content negotiation."""
        request = MagicMock()
        request.wantsJson.return_value = True
        for debug in (False, True):
            with self.subTest(debug=debug):
                self.application.config.return_value = debug
                self.responses.reset_mock()
                with self.assertWarnsRegex(DeprecationWarning, "handleHTTP") as warning:
                    result = await self.handler.handleHTTP(
                        RouteNotFound("missing"), request,
                    )
                self.assertIs(result, self.responses.error.return_value)
                self.responses.error.assert_awaited_once_with(
                    status_code=404,
                    content="Route not found",
                    expects_json=True,
                )
                self.responses.exception.assert_not_called()
                self.assertEqual(warning.filename, __file__)

    async def testHTTPHidesUnexpectedDetailsInProduction(self) -> None:
        """Keep production failures generic and honor HTML response requests."""
        self.application.config.return_value = False
        request = MagicMock()
        request.wantsJson.return_value = False
        with self.assertWarns(DeprecationWarning):
            result = await self.handler.handleHTTP(RuntimeError("secret"), request)
        self.assertIs(result, self.responses.error.return_value)
        self.responses.error.assert_awaited_once_with(
            status_code=500,
            content="Internal Server Error",
            expects_json=False,
        )
        self.responses.exception.assert_not_called()

    async def testHTTPDebugSupportsRequestsAndTransportAdapters(self) -> None:
        """Read both request property and adapter method representations."""
        request = MagicMock(path="/orders", method="POST")
        adapter = MagicMock(spec=TransportAdapter)
        adapter.path.return_value = "/orders"
        adapter.method.return_value = "POST"
        exception = RuntimeError("debug failure")
        for incoming in (request, adapter):
            with self.subTest(request=incoming):
                self.responses.reset_mock()
                with self.assertWarns(DeprecationWarning):
                    result = await self.handler.handleHTTP(exception, incoming)
                self.assertIs(result, self.responses.exception.return_value)
                self.responses.exception.assert_awaited_once_with(
                    request_path="/orders",
                    request_method="POST",
                    exception=exception,
                    status_code=500,
                )
                self.responses.error.assert_not_called()

    async def testHTTPPreservesBearerChallenge(self) -> None:
        """Retain the authentication challenge used by token clients."""
        request = MagicMock()
        request.wantsJson.return_value = True
        with (
            patch(
                "orionis.failure.base.handler.current_auth_context",
                return_value=MagicMock(guard="token"),
            ),
            self.assertWarns(DeprecationWarning),
        ):
            result = await self.handler.handleHTTP(
                AuthenticationException("login required"), request,
            )
        self.responses.error.assert_awaited_once_with(
            status_code=401,
            content="Unauthenticated",
            expects_json=True,
        )
        result.setHeader.assert_called_once_with("WWW-Authenticate", "Bearer")

    async def testModernFailurePlanDoesNotEmitLegacyWarnings(self) -> None:
        """Keep the modern observation path deferred and free of deprecations."""
        logger = MagicMock(spec=ILogger)
        self.application.make = AsyncMock(return_value=logger)
        request = MagicMock()
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always", DeprecationWarning)
            plan = await self.handler.handleFailure(
                RouteNotFound("missing"), FailureContext(flow="http"),
            )
            self.application.make.assert_not_called()
            self.responses.error.assert_not_called()
            await plan.complete()
            result = await plan.present(flow="http", request=request)
        self.assertEqual(captured, [])
        self.assertIs(result, self.responses.error.return_value)
        logger.getLogger.return_value.error.assert_called_once()
