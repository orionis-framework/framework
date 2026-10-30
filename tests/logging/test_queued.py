import asyncio
import logging
import threading
from queue import Full
from types import SimpleNamespace
from typing import TYPE_CHECKING, Never, Self
from orionis.foundation.application import Application
from orionis.foundation.enums.lifespan import Lifespan
from orionis.foundation.enums.runtimes import Runtime
from orionis.logging.handlers.queued import BoundedQueueHandler, LoggingDeliveryError
from orionis.test import TestCase

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from orionis.logging.contracts.logger import ILogger

class TestQueuedLogging(TestCase):
    """Verify explicit overload and draining of accepted log records."""

    async def testFullQueueAndDrain(self: Self) -> None:
        """
        Reject overflow, including critical records, while draining accepted ones.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        entered, released = threading.Event(), threading.Event()
        seen = []

        class Sink(logging.Handler):
            def emit(self: Self, record: logging.LogRecord) -> None:
                """
                Exercise the configured sink behavior for an emitted record.

                Parameters
                ----------
                record : logging.LogRecord
                    Log record to deliver to the sink.

                Returns
                -------
                None
                    Complete the operation without returning a value.
                """
                entered.set()
                released.wait(5)
                seen.append(record.getMessage())

        handler = BoundedQueueHandler(Sink(), 1)

        def record(text: str) -> logging.LogRecord:
            """
            Create a critical log record with the supplied message.

            Parameters
            ----------
            text : str
                Message stored in the critical log record.

            Returns
            -------
            logging.LogRecord
                New critical log record containing the supplied message.
            """
            return logging.LogRecord("bounded", logging.CRITICAL, "", 1, text, (), None)

        try:
            handler.handle(record("one"))
            await asyncio.to_thread(entered.wait, 5)
            handler.handle(record("two"))
            with self.assertRaises(Full):
                handler.handle(record("three"))
        finally:
            released.set()
            await asyncio.to_thread(handler.close)
        self.assertEqual(seen, ["one", "two"])

    async def testSinkFailureIsReportedAndDoesNotDeadlockClose(self: Self) -> None:
        """
        Expose background sink exceptions during flush or close.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """

        class Sink(logging.Handler):
            def emit(self: Self, _record: logging.LogRecord) -> None:
                """
                Exercise the configured sink behavior for an emitted record.

                Parameters
                ----------
                _record : logging.LogRecord
                    Log record associated with the simulated sink failure.

                Returns
                -------
                None
                    Complete the operation without returning a value.
                """
                error_msg = "unavailable"
                raise OSError(error_msg)

        handler = BoundedQueueHandler(Sink(), 2)
        handler.handle(logging.LogRecord("failure", 40, "", 1, "message", (), None))
        with self.assertRaises(LoggingDeliveryError):
            await asyncio.to_thread(handler.close)
        handler.close()

    async def testApplicationDrainsAfterShutdownHookFailure(self: Self) -> None:
        """
        Execute final logger cleanup even when a user shutdown hook raises.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        events = []

        async def close() -> None:
            """
            Record completion of the owned logging resource cleanup.

            Returns
            -------
            None
                Complete the operation without returning a value.
            """
            events.append("drained")

        async def make(_contract: type[ILogger]) -> SimpleNamespace:
            """
            Return a logger double with asynchronous cleanup.

            Parameters
            ----------
            _contract : type[ILogger]
                Logger contract requested by the application.

            Returns
            -------
            SimpleNamespace
                Logger double exposing its asynchronous close callback.
            """
            return SimpleNamespace(aclose=close)

        async def hook() -> Never:
            """
            Record shutdown hook execution and raise its configured failure.

            Returns
            -------
            Never
                Never return normally; raise the configured failure.
            """
            events.append("hook")
            error_msg = "hook failed"
            raise ValueError(error_msg)

        async def invoke(callback: Callable[[], Awaitable[None]]) -> None:
            """
            Await the supplied application lifecycle callback.

            Parameters
            ----------
            callback : Callable[[], Awaitable[None]]
                Lifecycle callback to await.

            Returns
            -------
            None
                Complete the operation without returning a value.
            """
            await callback()

        app = SimpleNamespace(config=lambda _key: 2, make=make, invoke=invoke)
        app._Application__configured = True
        app._Application__hook_events = {
            None: {Lifespan.SHUTDOWN: {hook: None}},
            Runtime.CLI: {Lifespan.SHUTDOWN: {}},
        }
        with self.assertRaisesRegex(ValueError, "hook failed"):
            await Application._Application__onShutdown(app, Runtime.CLI)
        self.assertEqual(events, ["hook", "drained"])

    async def testFlushFailureStillClosesTheOwnedSink(self: Self) -> None:
        """
        Translate flush errors while still closing the sink and listener.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        closed = []

        class Sink(logging.Handler):
            def flush(self: Self) -> None:
                """
                Raise a flush failure while the test sink remains open.

                Returns
                -------
                None
                    Complete the operation without returning a value.
                """
                if not closed:
                    error_msg = "flush unavailable"
                    raise OSError(error_msg)

            def close(self: Self) -> None:
                """
                Record completion of the owned logging resource cleanup.

                Returns
                -------
                None
                    Complete the operation without returning a value.
                """
                closed.append(True)
                super().close()

        handler = BoundedQueueHandler(Sink(), 1)
        with self.assertRaises(LoggingDeliveryError):
            await asyncio.to_thread(handler.close)
        self.assertTrue(closed)
        handler.close()
