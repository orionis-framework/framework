# ruff: noqa: LOG001, PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Capture real records with a standalone logger without changing the global registry.
"""Protect native exception messages and tracebacks in deferred default logging."""

import logging
from unittest.mock import AsyncMock, MagicMock
from orionis.failure.base.handler import BaseExceptionHandler
from orionis.failure.entities.context import FailureContext
from orionis.http.default.contracts.responses import IDefaultResponses
from orionis.logging.contracts.logger import ILogger
from orionis.test import TestCase


class _OrderFailure(Exception):
    """Format the domain message independently of the raw constructor argument."""

    def __str__(self) -> str:
        """Return the complete diagnostic message for the failed order."""
        return f"Cannot process order {self.args[0]}"


class _Records(logging.Handler):
    """Collect real logging records without opening files or external services."""

    def __init__(self) -> None:
        """Initialize an isolated record collector."""
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        """Retain the log record for assertions after deferred reporting."""
        self.records.append(record)


class TestHandlerRegressions(TestCase):
    """Exercise exception conversion and its real standard-library log consumer."""

    def testThrowablePreservesNativeMessagesAndArgumentCount(self) -> None:
        """Preserve custom and multi-argument messages without fabricating arguments."""
        handler = BaseExceptionHandler(
            default_responses=MagicMock(spec=IDefaultResponses),
            application=MagicMock(),
        )
        for exception in (
            Exception(),
            TypeError(42, "extra"),
            FileNotFoundError(2, "missing", "example.txt"),
            _OrderFailure(17),
        ):
            with self.subTest(exception=type(exception).__name__):
                throwable = handler.toThrowable(exception)
                self.assertEqual(throwable.message, str(exception))
                self.assertEqual(throwable.args, tuple(map(str, exception.args)))

    async def testDeferredLogPreservesTheOriginalMessageAndTraceback(self) -> None:
        """Write the custom message once with the original exception information."""
        records = _Records()
        self.addCleanup(records.close)
        logger = logging.Logger("failure-regression")
        logger.addHandler(records)
        service = MagicMock(spec=ILogger)
        service.getLogger.return_value = logger
        application = MagicMock()
        application.make = AsyncMock(return_value=service)
        handler = BaseExceptionHandler(
            default_responses=MagicMock(spec=IDefaultResponses),
            application=application,
        )
        exception = _OrderFailure(17)
        try:
            raise exception
        except _OrderFailure:
            traceback = exception.__traceback__
        plan = await handler.handleFailure(exception, FailureContext())
        self.assertEqual(records.records, [])
        await plan.complete()
        await plan.complete()
        application.make.assert_awaited_once_with(ILogger)
        self.assertEqual(len(records.records), 1)
        record = records.records[0]
        self.assertEqual(record.getMessage(), "[_OrderFailure] Cannot process order 17")
        self.assertEqual(record.exc_info, (_OrderFailure, exception, traceback))
