# ruff: noqa: LOG001, PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Real isolated loggers preserve the application runner's handlers.
"""Exercise logger lifecycle changes during concurrent public calls."""

import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from unittest.mock import patch
from orionis.logging import Logger
from orionis.test import TestCase


class _LoggingApp:
    """Provide configuration rooted in a temporary application directory."""

    def __init__(self, root: str) -> None:
        """Retain the temporary application root.

        Parameters
        ----------
        root : str
            Directory containing every log file created by the test.
        """
        self.root = root
        self.settings = {
            "default": "stack",
            "channels": {"stack": {"path": "app.log", "level": "DEBUG"}},
        }

    def config(self, _name: str) -> dict:
        """Return one local file channel.

        Parameters
        ----------
        _name : str
            Configuration section requested by the logger.

        Returns
        -------
        dict
            Logging configuration using only the temporary directory.
        """
        return self.settings

    def path(self, _name: str) -> str:
        """Return the temporary application root.

        Parameters
        ----------
        _name : str
            Application path requested by the logger.

        Returns
        -------
        str
            Temporary application directory.
        """
        return self.root


class _CloseProbe(logging.Handler):
    """Record close attempts and optionally fail the first attempt."""

    def __init__(self, failure: Exception | None = None) -> None:
        """Configure the failure injected during the first close.

        Parameters
        ----------
        failure : Exception | None
            Original exception to raise once after closing the handler.
        """
        super().__init__()
        self.failure = failure
        self.calls = 0

    def close(self) -> None:
        """Close the handler and preserve the injected failure identity."""
        self.calls += 1
        failure, self.failure = self.failure, None
        super().close()
        if failure is not None:
            raise failure


class TestLoggingLifecycleRegressions(TestCase):
    """Coordinate shutdown at the boundary between initialization and use."""

    def testPublicCallsRetainTheLoggerAcrossConcurrentClose(self) -> None:
        """Keep a valid logger reference when another thread closes the service."""
        for method in (
            "info",
            "error",
            "warning",
            "debug",
            "critical",
            "getLogger",
            "switchChannel",
        ):
            with self.subTest(method=method), TemporaryDirectory() as directory:
                native = logging.Logger("__orionis__")
                native.disabled = True
                with patch.dict(
                    logging.Logger.manager.loggerDict,
                    {"__orionis__": native},
                ):
                    self._exerciseConcurrentClose(directory, method, native)
                self.assertTrue((Path(directory) / "app.log").is_file())

    def testConfigurationClosesEveryHandlerBeforeReportingFailure(self) -> None:
        """Drain all handlers and retain the first cleanup error as the cause."""
        for operation in ("initialize", "reload"):
            with self.subTest(operation=operation), TemporaryDirectory() as directory:
                native = logging.Logger("__orionis__")
                with patch.dict(
                    logging.Logger.manager.loggerDict,
                    {"__orionis__": native},
                ):
                    logger = Logger(_LoggingApp(directory))
                    first_error = RuntimeError("first cleanup failure")
                    second_error = LookupError("second cleanup failure")
                    handlers = (
                        _CloseProbe(first_error),
                        _CloseProbe(second_error),
                        _CloseProbe(),
                    )
                    try:
                        if operation == "reload":
                            logger.getLogger()
                        for handler in handlers:
                            native.addHandler(handler)
                        with (
                            patch("orionis.failure.runtime.capture_nowait") as capture,
                            self.assertRaises(RuntimeError) as raised,
                        ):
                            if operation == "reload":
                                logger.reloadConfiguration()
                            else:
                                logger.getLogger()
                        self.assertIs(raised.exception.__cause__, first_error)
                        self.assertEqual(
                            [handler.calls for handler in handlers],
                            [1, 1, 1],
                        )
                        self.assertEqual(native.handlers, [])
                        self.assertEqual(logger.getActiveChannels(), [])
                        capture.assert_called_once()
                        self.assertIs(capture.call_args.args[0], second_error)
                    finally:
                        for handler in handlers:
                            native.removeHandler(handler)
                            handler.failure = None
                            handler.close()
                        logger.close()

    def testAbortedConfigurationClosesTheUnpublishedSink(self) -> None:
        """Close newly created file streams when queue configuration fails."""
        for operation in ("initialize", "switch"):
            with self.subTest(operation=operation), TemporaryDirectory() as directory:
                native = logging.Logger("__orionis__")
                with patch.dict(
                    logging.Logger.manager.loggerDict,
                    {"__orionis__": native},
                ):
                    app = _LoggingApp(directory)
                    logger = Logger(app)
                    handler = logging.FileHandler(Path(directory) / "new.log")
                    try:
                        if operation == "switch":
                            logger.getLogger()
                        app.settings["queue_capacity"] = -1
                        target = "orionis.logging.logger." + (
                            "logging.FileHandler"
                            if operation == "initialize"
                            else "RotatingHandlerFactory.createHandler"
                        )
                        with patch(target, return_value=handler):
                            if operation == "initialize":
                                with self.assertRaises(RuntimeError):
                                    logger.getLogger()
                            else:
                                self.assertFalse(logger.switchChannel("stack"))
                        self.assertIsNone(handler.stream)
                        self.assertEqual(native.handlers, [])
                        self.assertEqual(logger.getActiveChannels(), [])
                    finally:
                        handler.close()
                        logger.close()

    def testInitialStackHonorsAnAbsoluteConfiguredPath(self) -> None:
        """Resolve the initial stack path like the channel factory does."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "outside.log"
            app = _LoggingApp(str(root / "application"))
            app.settings["channels"]["stack"]["path"] = str(target)
            native = logging.Logger("__orionis__")
            with patch.dict(logging.Logger.manager.loggerDict, {"__orionis__": native}):
                logger = Logger(app)
                try:
                    logger.info("absolute path record")
                finally:
                    logger.close()
            self.assertIn("absolute path record", target.read_text(encoding="utf-8"))

    def testUnknownLevelNamesDoNotResolveOtherLoggingAttributes(self) -> None:
        """Apply INFO when a name exists on logging but is not a severity."""
        with TemporaryDirectory() as directory:
            app = _LoggingApp(directory)
            app.settings["channels"]["stack"]["level"] = "BASIC_FORMAT"
            native = logging.Logger("__orionis__")
            with patch.dict(logging.Logger.manager.loggerDict, {"__orionis__": native}):
                logger = Logger(app)
                try:
                    self.assertEqual(logger.getLogger().handlers[0].level, logging.INFO)
                finally:
                    logger.close()

    def _exerciseConcurrentClose(
        self,
        directory: str,
        method: str,
        native: logging.Logger,
    ) -> None:
        """Pause a public call after readiness while the main thread closes it.

        Parameters
        ----------
        directory : str
            Temporary application directory for this scenario.
        method : str
            Public logger operation executed by the worker.
        native : logging.Logger
            Real standard logger isolated from the application runner.
        """
        logger = Logger(_LoggingApp(directory))
        ready, release = Event(), Event()
        original = Logger._Logger__ensureLoggerReady

        def wait_after_ready(instance: Logger) -> logging.Logger | None:
            """Pause after initialization until the concurrent close completes.

            Parameters
            ----------
            instance : Logger
                Service being initialized by the worker.

            Returns
            -------
            logging.Logger | None
                Original readiness result, preserved without changing it.
            """
            result = original(instance)
            ready.set()
            if not release.wait(5):
                message = "Concurrent logger close did not release the worker."
                raise TimeoutError(message)
            return result

        try:
            with (
                patch.object(Logger, "_Logger__ensureLoggerReady", wait_after_ready),
                ThreadPoolExecutor(max_workers=1) as executor,
            ):
                arguments = () if method == "getLogger" else ("event",)
                if method == "switchChannel":
                    arguments = ("stack",)
                future = executor.submit(getattr(logger, method), *arguments)
                try:
                    self.assertTrue(ready.wait(5))
                    logger.close()
                finally:
                    release.set()
                result = future.result(timeout=5)
                if method == "getLogger":
                    self.assertIs(result, native)
                elif method == "switchChannel":
                    self.assertTrue(result)
        finally:
            logger.close()
