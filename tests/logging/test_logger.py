import gc
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis.foundation.config.logging.enums.levels import Level
from orionis.logging.contracts.logger import ILogger
from orionis.logging.handlers.advanced_rotating_file_handler import (
    AdvancedRotatingFileHandler,
)
from orionis.logging.logger import Logger
from orionis.test import TestCase

# Alias registered by the framework for the internal logging channel.
_LOGGER_NAME = "__orionis__"

# Path alias requested by the logger when resolving the application root.
_ROOT_KEY = "root"

# Relative log paths used by the channels exercised in this module.
_STACK_PATH = "storage/logs/stack.log"
_DAILY_PATH = "storage/logs/daily_{suffix}.log"
_FALLBACK_PATH = "storage/logs/default.log"

class _StubApp:
    """Application double exposing the two hooks consumed by the logger."""

    __slots__ = ("config_error", "path_error", "root", "settings")

    def __init__(self, root: str, settings: dict) -> None:
        """Store the application root and the logging configuration."""
        self.root: str = root
        self.settings: dict = settings
        self.config_error: Exception | None = None
        self.path_error: Exception | None = None

    def config(self, key: str) -> dict:
        """Return the configuration section requested by the logger."""
        if self.config_error is not None:
            raise self.config_error
        return self.settings if key == "logging" else {}

    def path(self, key: str) -> str:
        """Return the absolute directory registered under the given alias."""
        if self.path_error is not None:
            raise self.path_error
        return self.root if key == _ROOT_KEY else f"{self.root}/{key}"

def _channel(level: object = logging.INFO, path: str = _STACK_PATH) -> dict:
    """Return a single channel configuration entry."""
    return {"path": path, "level": level}

def _make_app(
    root: str,
    *,
    default: str = "stack",
    channels: dict | None = None,
) -> _StubApp:
    """Return an application double wired to the given logging channels."""
    if channels is None:
        channels = {"stack": _channel()}
    return _StubApp(root, {"default": default, "channels": channels})

def _skip_initialisation() -> None:
    """Stand in for the private initialiser without building any logger."""

class TestLoggerDefinition(TestCase):

    def testImplementsTheLoggerContract(self) -> None:
        """
        Declare Logger as an implementation of the logging contract.

        Validates that the concrete service can be bound to the ILogger
        abstraction resolved through the container.
        """
        self.assertTrue(issubclass(Logger, ILogger))

    def testExposesTheFrameworkServiceName(self) -> None:
        """
        Publish the framework service name as a class level constant.

        Validates that the abstract property is shadowed by a plain attribute,
        keeping attribute access free of descriptor overhead.
        """
        self.assertEqual(Logger.name, _LOGGER_NAME)

    def testInstancesReportTheFrameworkServiceName(self) -> None:
        """
        Report the service name from any logger instance.

        Validates that consumers reading ``logger.name`` obtain the identifier
        used to register the underlying standard library logger.
        """
        with TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            logger = Logger(_make_app(tmp))
            try:
                self.assertEqual(logger.name, _LOGGER_NAME)
            finally:
                logger.close()

class TestLoggerLazyInitialisation(TestCase):

    def setUp(self) -> None:
        """Create a temporary application root and an idle logger."""
        self._tmp = TemporaryDirectory(ignore_cleanup_errors=True)
        self._app = _make_app(self._tmp.name)
        self._logger = Logger(self._app)

    def tearDown(self) -> None:
        """Release the logger handles and delete the temporary root."""
        self._logger.close()
        self._tmp.cleanup()

    def testLoggerIsNotBuiltUntilFirstUse(self) -> None:
        """
        Defer the construction of the standard library logger.

        Validates that instantiating the service performs no logging setup, so
        an unused logger never touches the filesystem.
        """
        self.assertIsNone(self._logger._Logger__logger)

    def testFirstMessageBuildsTheLogger(self) -> None:
        """
        Build the underlying logger on the first logged message.

        Validates the lazy initialisation triggered from the logging methods.
        """
        self._logger.info("first message")
        self.assertIsNotNone(self._logger._Logger__logger)

    def testSubsequentCallsReuseTheSameLogger(self) -> None:
        """
        Reuse the already initialised logger on every later call.

        Validates that the double checked guard returns the cached instance
        instead of rebuilding the handler stack.
        """
        self.assertIs(self._logger.getLogger(), self._logger.getLogger())

    def testInitialisationFailureIsWrappedInRuntimeError(self) -> None:
        """
        Wrap any initialisation failure in a RuntimeError.

        Validates that a broken application root lookup surfaces as an explicit
        framework error instead of the raw driver exception.
        """
        self._app.path_error = OSError("unreachable root")
        with self.assertRaises(RuntimeError) as captured:
            self._logger.info("cannot be written")
        self.assertIn("Failed to initialize logger", str(captured.exception))

    def testReadinessGuardRaisesWhenNoLoggerIsProduced(self) -> None:
        """
        Raise a RuntimeError when initialisation produces no logger.

        Validates the defensive guard protecting every caller from a silently
        unavailable logging backend.
        """
        self._logger._Logger__initializeLogger = _skip_initialisation
        with self.assertRaises(RuntimeError) as captured:
            self._logger.getLogger()
        self.assertIn("could not be initialized", str(captured.exception))

class TestLoggerMessages(TestCase):

    def setUp(self) -> None:
        """Create a temporary application root and an idle logger."""
        self._tmp = TemporaryDirectory(ignore_cleanup_errors=True)
        self._logger = Logger(_make_app(self._tmp.name))

    def tearDown(self) -> None:
        """Release the logger handles and delete the temporary root."""
        self._logger.close()
        self._tmp.cleanup()

    def _readStackLog(self) -> str:
        """Return the text stored in the default stack log file."""
        path = Path(self._tmp.name) / "storage" / "logs" / "stack.log"
        return path.read_text(encoding="utf-8")

    def testInfoIsWrittenToTheChannelFile(self) -> None:
        """
        Record an informational message in the active channel.

        Validates that info() reaches the file handler configured for the
        default channel.
        """
        self._logger.info("info message")
        self.assertIn("info message", self._readStackLog())

    def testWarningIsWrittenToTheChannelFile(self) -> None:
        """
        Record a warning message in the active channel.

        Validates that warning() reaches the file handler configured for the
        default channel.
        """
        self._logger.warning("warning message")
        self.assertIn("warning message", self._readStackLog())

    def testErrorIsWrittenToTheChannelFile(self) -> None:
        """
        Record an error message in the active channel.

        Validates that error() reaches the file handler configured for the
        default channel.
        """
        self._logger.error("error message")
        self.assertIn("error message", self._readStackLog())

    def testCriticalIsWrittenToTheChannelFile(self) -> None:
        """
        Record a critical message in the active channel.

        Validates that critical() reaches the file handler configured for the
        default channel.
        """
        self._logger.critical("critical message")
        self.assertIn("critical message", self._readStackLog())

    def testDebugIsDiscardedWhenTheChannelLevelIsHigher(self) -> None:
        """
        Discard debug records rejected by the channel level.

        Validates that the handler level configured for the channel filters
        messages below it even though the logger itself accepts them.
        """
        self._logger.info("keep the file alive")
        self._logger.debug("debug message")
        self.assertNotIn("debug message", self._readStackLog())

    def testDebugIsWrittenWhenTheChannelLevelAllowsIt(self) -> None:
        """
        Record a debug message on a channel configured for debugging.

        Validates that debug() reaches the file handler when the channel level
        is lowered to DEBUG.
        """
        self._logger.close()
        channels = {"stack": _channel(level=logging.DEBUG)}
        self._logger = Logger(_make_app(self._tmp.name, channels=channels))
        self._logger.debug("debug message")
        self.assertIn("debug message", self._readStackLog())

    def testMessagesAreForwardedWithoutSanitisation(self) -> None:
        """
        Forward blank messages to the logging backend untouched.

        Validates that the service performs no trimming or filtering, leaving
        message policy to the caller.
        """
        self._logger.info("")
        self._logger.info("   ")
        self.assertEqual(len(self._readStackLog().splitlines()), 2)

class TestLoggerFormatter(TestCase):

    def setUp(self) -> None:
        """Isolate the shared formatter cache and build a temporary root."""
        self._original_cache = dict(Logger._formatter_cache)
        Logger._formatter_cache.clear()
        self._tmp = TemporaryDirectory(ignore_cleanup_errors=True)

    def tearDown(self) -> None:
        """Restore the shared formatter cache and delete the temporary root."""
        Logger._formatter_cache.clear()
        Logger._formatter_cache.update(self._original_cache)
        self._tmp.cleanup()

    def testFormatterIsBuiltOnlyOnce(self) -> None:
        """
        Build a single formatter for the default pattern.

        Validates that the class level cache is populated once and reused by
        every logger sharing the same format and date format.
        """
        first = Logger(_make_app(self._tmp.name))
        second = Logger(_make_app(self._tmp.name))
        try:
            first.info("first")
            second.info("second")
            self.assertEqual(len(Logger._formatter_cache), 1)
        finally:
            first.close()
            second.close()

    def testCachedFormatterIsSharedBetweenInstances(self) -> None:
        """
        Share the very same formatter object between logger instances.

        Validates that the cache returns the stored formatter instead of an
        equivalent copy.
        """
        first = Logger(_make_app(self._tmp.name))
        second = Logger(_make_app(self._tmp.name))
        try:
            first_handler = first.getLogger().handlers[0]
            second_handler = second.getLogger().handlers[0]
            self.assertIs(first_handler.formatter, second_handler.formatter)
        finally:
            first.close()
            second.close()

    def testMessagesUseTheConfiguredPattern(self) -> None:
        """
        Render every record with the timestamp and level pattern.

        Validates the default format applied to all channels.
        """
        logger = Logger(_make_app(self._tmp.name))
        try:
            logger.info("formatted")
            path = Path(self._tmp.name) / "storage" / "logs" / "stack.log"
            content = path.read_text(encoding="utf-8")
            self.assertRegex(
                content,
                r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \[INFO\]: formatted",
            )
        finally:
            logger.close()

class TestLoggerDefaultChannel(TestCase):

    def setUp(self) -> None:
        """Create the temporary application root shared by the tests."""
        self._tmp = TemporaryDirectory(ignore_cleanup_errors=True)

    def tearDown(self) -> None:
        """Delete the temporary application root."""
        self._tmp.cleanup()

    def testStackChannelUsesAPlainFileHandler(self) -> None:
        """
        Attach a plain file handler for the stack channel.

        Validates the fast path that skips the rotating factory for the most
        common channel.
        """
        logger = Logger(_make_app(self._tmp.name))
        try:
            handler = logger.getLogger().handlers[0]
            self.assertIs(type(handler), logging.FileHandler)
        finally:
            logger.close()

    def testStackChannelAppliesTheConfiguredLevel(self) -> None:
        """
        Apply the channel level to the stack handler.

        Validates that the configured threshold reaches the handler instead of
        the framework default.
        """
        channels = {"stack": _channel(level=logging.ERROR)}
        logger = Logger(_make_app(self._tmp.name, channels=channels))
        try:
            self.assertEqual(logger.getLogger().handlers[0].level, logging.ERROR)
        finally:
            logger.close()

    def testStackChannelNormalisesEnumeratedLevels(self) -> None:
        """
        Translate an enumerated level before configuring the stack handler.

        Validates that a configuration declaring levels through the framework
        enumeration starts the logger instead of failing.
        """
        channels = {"stack": _channel(level=Level.WARNING)}
        logger = Logger(_make_app(self._tmp.name, channels=channels))
        try:
            self.assertEqual(logger.getLogger().handlers[0].level, logging.WARNING)
        finally:
            logger.close()

    def testStackChannelNormalisesTextualLevels(self) -> None:
        """
        Translate a textual level before configuring the stack handler.

        Validates that case insensitive level names are accepted by the
        default channel.
        """
        channels = {"stack": _channel(level="warning")}
        logger = Logger(_make_app(self._tmp.name, channels=channels))
        try:
            self.assertEqual(logger.getLogger().handlers[0].level, logging.WARNING)
        finally:
            logger.close()

    def testStackChannelFallsBackToInfoWhenNoLevelIsDeclared(self) -> None:
        """
        Fall back to INFO when the default channel declares no level.

        Validates the threshold applied to incomplete configurations.
        """
        channels = {"stack": {"path": _STACK_PATH}}
        logger = Logger(_make_app(self._tmp.name, channels=channels))
        try:
            self.assertEqual(logger.getLogger().handlers[0].level, logging.INFO)
        finally:
            logger.close()

    def testStackChannelCreatesTheParentDirectory(self) -> None:
        """
        Create the directory tree required by the stack log file.

        Validates that a missing storage folder never prevents the logger from
        starting.
        """
        channels = {"stack": _channel(path="deep/nested/logs/stack.log")}
        logger = Logger(_make_app(self._tmp.name, channels=channels))
        try:
            logger.info("nested")
            expected = Path(self._tmp.name) / "deep" / "nested" / "logs"
            self.assertTrue(expected.is_dir())
        finally:
            logger.close()

    def testRotatingChannelIsBuiltByTheFactory(self) -> None:
        """
        Delegate non stack channels to the rotating handler factory.

        Validates that a rotating channel selected as default produces an
        advanced rotating handler.
        """
        channels = {"daily": _channel(path=_DAILY_PATH)}
        logger = Logger(_make_app(self._tmp.name, default="daily", channels=channels))
        try:
            handler = logger.getLogger().handlers[0]
            self.assertIsInstance(handler, AdvancedRotatingFileHandler)
            self.assertEqual(logger.getActiveChannels(), ["daily"])
        finally:
            logger.close()

    def testRotatingChannelWritesToTheResolvedPath(self) -> None:
        """
        Write records to the file resolved by the rotating suffix.

        Validates that the placeholder of the configured path is replaced
        before the first record is emitted.
        """
        channels = {"daily": _channel(path=_DAILY_PATH)}
        logger = Logger(_make_app(self._tmp.name, default="daily", channels=channels))
        try:
            logger.info("rotating message")
            produced = list((Path(self._tmp.name) / "storage" / "logs").glob("*.log"))
            self.assertEqual(len(produced), 1)
            self.assertIn(
                "rotating message",
                produced[0].read_text(encoding="utf-8"),
            )
        finally:
            logger.close()

    def testRotatingChannelNormalisesEnumeratedLevels(self) -> None:
        """
        Translate an enumerated level before configuring a rotating handler.

        Validates that the normalised threshold is applied to the handler and
        not only forwarded to the factory.
        """
        channels = {"daily": _channel(level=Level.ERROR, path=_DAILY_PATH)}
        logger = Logger(_make_app(self._tmp.name, default="daily", channels=channels))
        try:
            self.assertEqual(logger.getLogger().handlers[0].level, logging.ERROR)
        finally:
            logger.close()

    def testUnsupportedChannelLeavesTheLoggerWithoutHandlers(self) -> None:
        """
        Skip handler registration for an unsupported channel type.

        Validates that a configured channel with no matching factory leaves the
        logger usable but silent instead of raising.
        """
        channels = {"custom": _channel(path="storage/logs/custom.log")}
        logger = Logger(_make_app(self._tmp.name, default="custom", channels=channels))
        try:
            logger.info("discarded message")
            self.assertEqual(logger.getLogger().handlers, [])
            self.assertEqual(logger.getActiveChannels(), [])
        finally:
            logger.close()

    def testMissingDefaultChannelFallsBackToADefaultFile(self) -> None:
        """
        Fall back to a default file when the channel is not configured.

        Validates that an unknown default channel never leaves the application
        without logging output.
        """
        logger = Logger(_make_app(self._tmp.name, default="missing"))
        try:
            logger.info("fallback message")
            self.assertEqual(logger.getActiveChannels(), ["fallback"])
            fallback = Path(self._tmp.name) / _FALLBACK_PATH
            self.assertIn("fallback message", fallback.read_text(encoding="utf-8"))
        finally:
            logger.close()

    def testInitialisationClearsPreviouslyRegisteredHandlers(self) -> None:
        """
        Replace the handlers left by a previous logger instance.

        Validates that the shared standard library logger never accumulates
        duplicated handlers across initialisations.
        """
        first = Logger(_make_app(self._tmp.name))
        second = Logger(_make_app(self._tmp.name))
        try:
            first.info("first instance")
            second.info("second instance")
            self.assertEqual(len(second.getLogger().handlers), 1)
        finally:
            first.close()
            second.close()

class TestLoggerChannelIntrospection(TestCase):

    def setUp(self) -> None:
        """Create the temporary application root shared by the tests."""
        self._tmp = TemporaryDirectory(ignore_cleanup_errors=True)

    def tearDown(self) -> None:
        """Delete the temporary application root."""
        self._tmp.cleanup()

    def testAvailableChannelsListEveryConfiguredName(self) -> None:
        """
        List every channel declared in the configuration.

        Validates that availability is reported from the configuration and not
        from the handlers currently attached.
        """
        channels = {"stack": _channel(), "daily": _channel(path=_DAILY_PATH)}
        logger = Logger(_make_app(self._tmp.name, channels=channels))
        try:
            self.assertEqual(
                sorted(logger.getAvailableChannels()),
                ["daily", "stack"],
            )
        finally:
            logger.close()

    def testAvailableChannelsAreEmptyWithoutConfiguration(self) -> None:
        """
        Report no available channel when none is configured.

        Validates the default applied when the channels section is missing.
        """
        logger = Logger(_StubApp(self._tmp.name, {"default": "stack"}))
        try:
            self.assertEqual(logger.getAvailableChannels(), [])
        finally:
            logger.close()

    def testActiveChannelsAreEmptyBeforeInitialisation(self) -> None:
        """
        Report no active channel while the logger stays idle.

        Validates that activation is only recorded once a handler is built.
        """
        logger = Logger(_make_app(self._tmp.name))
        try:
            self.assertEqual(logger.getActiveChannels(), [])
            self.assertIsNone(logger.getActiveChannel())
        finally:
            logger.close()

    def testActiveChannelIsTheDefaultChannelAfterInitialisation(self) -> None:
        """
        Report the default channel as the single active one.

        Validates that exactly one channel is active at a time.
        """
        logger = Logger(_make_app(self._tmp.name))
        try:
            logger.info("activate")
            self.assertEqual(logger.getActiveChannels(), ["stack"])
            self.assertEqual(logger.getActiveChannel(), "stack")
        finally:
            logger.close()

class TestLoggerSwitchChannel(TestCase):

    def setUp(self) -> None:
        """Create the temporary application root shared by the tests."""
        self._tmp = TemporaryDirectory(ignore_cleanup_errors=True)

    def tearDown(self) -> None:
        """Delete the temporary application root."""
        self._tmp.cleanup()

    def _makeLogger(self, level: object = logging.INFO) -> Logger:
        """Return a logger configured with a stack and a daily channel."""
        channels = {
            "stack": _channel(),
            "daily": {"path": _DAILY_PATH, "level": level},
        }
        return Logger(_make_app(self._tmp.name, channels=channels))

    def _makeLoggerWithoutLevel(self) -> Logger:
        """Return a logger whose daily channel declares no level."""
        channels = {"stack": _channel(), "daily": {"path": _DAILY_PATH}}
        return Logger(_make_app(self._tmp.name, channels=channels))

    def testSwitchToConfiguredChannelReplacesTheHandler(self) -> None:
        """
        Activate the requested channel and drop the previous handler.

        Validates that only one channel remains active after switching.
        """
        logger = self._makeLogger()
        try:
            logger.info("before switch")
            self.assertTrue(logger.switchChannel("daily"))
            self.assertEqual(logger.getActiveChannels(), ["daily"])
            self.assertEqual(len(logger.getLogger().handlers), 1)
        finally:
            logger.close()

    def testSwitchWritesTheConfirmationToTheNewChannel(self) -> None:
        """
        Confirm the switch through the newly activated channel.

        Validates that the acknowledgement message is emitted by the handler
        created for the target channel.
        """
        logger = self._makeLogger()
        try:
            logger.info("before switch")
            logger.switchChannel("daily")
            produced = list(
                (Path(self._tmp.name) / "storage" / "logs").glob("daily_*.log"),
            )
            self.assertEqual(len(produced), 1)
            self.assertIn(
                "Successfully switched to channel: daily",
                produced[0].read_text(encoding="utf-8"),
            )
        finally:
            logger.close()

    def testSwitchBeforeInitialisationStartsTheLogger(self) -> None:
        """
        Initialise the logger when switching before the first message.

        Validates that the target channel becomes active even though no record
        has been logged yet.
        """
        logger = self._makeLogger()
        try:
            self.assertTrue(logger.switchChannel("daily"))
            self.assertEqual(logger.getActiveChannels(), ["daily"])
        finally:
            logger.close()

    def testSwitchToUnknownChannelIsRejected(self) -> None:
        """
        Reject a channel absent from the configuration.

        Validates that the guard runs before any handler is built, leaving the
        logger untouched.
        """
        logger = self._makeLogger()
        try:
            self.assertFalse(logger.switchChannel("unknown"))
            self.assertIsNone(logger.getActiveChannel())
        finally:
            logger.close()

    def testSwitchIsRejectedWhenTheHandlerCannotBeCreated(self) -> None:
        """
        Report a failed switch when the target handler cannot be built.

        Validates that a filesystem error raised by the factory is converted
        into a False result instead of propagating.
        """
        blocked = Path(self._tmp.name) / "blocked"
        blocked.write_text("not a directory", encoding="utf-8")
        channels = {
            "daily": _channel(path=_DAILY_PATH),
            "stack": _channel(path="blocked/nested/stack.log"),
        }
        app = _make_app(self._tmp.name, default="daily", channels=channels)
        logger = Logger(app)
        try:
            logger.info("before switch")
            self.assertFalse(logger.switchChannel("stack"))
            self.assertEqual(logger.getActiveChannels(), [])
        finally:
            logger.close()

    def testSwitchIsRejectedWhenTheRootPathIsUnavailable(self) -> None:
        """
        Report a failed switch when the application root cannot be resolved.

        Validates that runtime errors raised while preparing the new handler
        are contained inside the method.
        """
        channels = {"stack": _channel(), "daily": _channel(path=_DAILY_PATH)}
        app = _make_app(self._tmp.name, channels=channels)
        logger = Logger(app)
        try:
            logger.info("before switch")
            app.path_error = RuntimeError("root unavailable")
            self.assertFalse(logger.switchChannel("daily"))
        finally:
            app.path_error = None
            logger.close()

    def testSwitchNormalisesEnumeratedLevels(self) -> None:
        """
        Translate an enumerated level into its integer value.

        Validates the normalisation applied to configurations declaring levels
        through the framework enumeration.
        """
        logger = self._makeLogger(level=Level.WARNING)
        try:
            logger.switchChannel("daily")
            self.assertEqual(logger.getLogger().handlers[0].level, logging.WARNING)
        finally:
            logger.close()

    def testSwitchNormalisesTextualLevels(self) -> None:
        """
        Translate a textual level into its integer value.

        Validates the normalisation applied to configurations declaring levels
        as case insensitive names.
        """
        logger = self._makeLogger(level="warning")
        try:
            logger.switchChannel("daily")
            self.assertEqual(logger.getLogger().handlers[0].level, logging.WARNING)
        finally:
            logger.close()

    def testSwitchFallsBackToInfoForUnknownTextualLevels(self) -> None:
        """
        Fall back to INFO when the textual level is not recognised.

        Validates that an invalid level never prevents the channel from being
        activated.
        """
        logger = self._makeLogger(level="not-a-level")
        try:
            logger.switchChannel("daily")
            self.assertEqual(logger.getLogger().handlers[0].level, logging.INFO)
        finally:
            logger.close()

    def testSwitchFallsBackToInfoWhenNoLevelIsDeclared(self) -> None:
        """
        Fall back to INFO when the channel declares no level.

        Validates the default threshold applied to incomplete configurations.
        """
        logger = self._makeLoggerWithoutLevel()
        try:
            logger.switchChannel("daily")
            self.assertEqual(logger.getLogger().handlers[0].level, logging.INFO)
        finally:
            logger.close()

    def testSwitchKeepsIntegerLevelsUnchanged(self) -> None:
        """
        Preserve levels already expressed as integers.

        Validates that the normalisation leaves standard library values alone.
        """
        logger = self._makeLogger(level=logging.ERROR)
        try:
            logger.switchChannel("daily")
            self.assertEqual(logger.getLogger().handlers[0].level, logging.ERROR)
        finally:
            logger.close()

class TestLoggerReloadConfiguration(TestCase):

    def setUp(self) -> None:
        """Create a temporary application root and an idle logger."""
        self._tmp = TemporaryDirectory(ignore_cleanup_errors=True)
        self._app = _make_app(self._tmp.name)
        self._logger = Logger(self._app)

    def tearDown(self) -> None:
        """Release the logger handles and delete the temporary root."""
        self._app.config_error = None
        self._logger.close()
        self._tmp.cleanup()

    def testReloadKeepsTheLoggerUsable(self) -> None:
        """
        Keep logging available after a configuration reload.

        Validates that the handler stack is rebuilt instead of being left
        empty.
        """
        self._logger.info("before reload")
        self._logger.reloadConfiguration()
        self._logger.info("after reload")
        path = Path(self._tmp.name) / "storage" / "logs" / "stack.log"
        self.assertIn("after reload", path.read_text(encoding="utf-8"))

    def testReloadRecordsAConfirmationMessage(self) -> None:
        """
        Record the outcome of the reload in the active channel.

        Validates the acknowledgement emitted once the new configuration is
        applied.
        """
        self._logger.reloadConfiguration()
        path = Path(self._tmp.name) / "storage" / "logs" / "stack.log"
        self.assertIn(
            "Logger configuration reloaded successfully",
            path.read_text(encoding="utf-8"),
        )

    def testReloadAppliesTheUpdatedConfiguration(self) -> None:
        """
        Adopt the configuration published after the first initialisation.

        Validates that the reload re-reads the application configuration
        instead of reusing the cached one.
        """
        self._logger.info("before reload")
        self._app.settings = {
            "default": "daily",
            "channels": {"daily": _channel(path=_DAILY_PATH)},
        }
        self._logger.reloadConfiguration()
        self.assertEqual(self._logger.getActiveChannels(), ["daily"])

    def testReloadBeforeInitialisationStartsTheLogger(self) -> None:
        """
        Start the logger when reloading before the first message.

        Validates that the reload path tolerates an idle logger with no
        handler to close.
        """
        self._logger.reloadConfiguration()
        self.assertEqual(self._logger.getActiveChannel(), "stack")

    def testReloadFailureIsWrappedInRuntimeError(self) -> None:
        """
        Wrap a failing configuration lookup in a RuntimeError.

        Validates that a broken application configuration surfaces as an
        explicit framework error.
        """
        self._logger.info("before reload")
        self._app.config_error = ValueError("broken configuration")
        with self.assertRaises(RuntimeError) as captured:
            self._logger.reloadConfiguration()
        self.assertIn("Failed to reload logger", str(captured.exception))

class TestLoggerClose(TestCase):

    def setUp(self) -> None:
        """Create a temporary application root and an idle logger."""
        self._tmp = TemporaryDirectory(ignore_cleanup_errors=True)
        self._logger = Logger(_make_app(self._tmp.name))

    def tearDown(self) -> None:
        """Release the logger handles and delete the temporary root."""
        self._logger.close()
        self._tmp.cleanup()

    def testCloseResetsTheInternalLogger(self) -> None:
        """
        Drop the reference to the standard library logger.

        Validates that the next call rebuilds the logging stack from scratch.
        """
        self._logger.info("populate")
        self._logger.close()
        self.assertIsNone(self._logger._Logger__logger)

    def testCloseClearsTheActiveChannels(self) -> None:
        """
        Forget every active channel once the logger is closed.

        Validates that cached handlers are released together with the logger.
        """
        self._logger.info("populate")
        self._logger.close()
        self.assertEqual(self._logger.getActiveChannels(), [])

    def testCloseReleasesHandlersRegisteredByThirdParties(self) -> None:
        """
        Detach every handler attached to the underlying logger.

        Validates that handlers registered outside the service are closed too,
        which requires iterating over a copy of the handler list.
        """
        self._logger.info("populate")
        internal = self._logger.getLogger()
        extra = logging.FileHandler(
            str(Path(self._tmp.name) / "extra.log"),
            encoding="utf-8",
            delay=True,
        )
        internal.addHandler(extra)
        self._logger.close()
        self.assertEqual(internal.handlers, [])

    def testCloseIsIdempotent(self) -> None:
        """
        Allow repeated close calls without raising.

        Validates that shutting down an already closed logger is a no-op.
        """
        self._logger.info("populate")
        self._logger.close()
        self._logger.close()
        self.assertIsNone(self._logger._Logger__logger)

    def testCloseBeforeInitialisationDoesNotRaise(self) -> None:
        """
        Close an idle logger without raising.

        Validates the guard protecting the teardown of a logger that never
        built any handler.
        """
        self._logger.close()
        self.assertEqual(self._logger.getActiveChannels(), [])

    def testLoggerIsRebuiltAfterClose(self) -> None:
        """
        Rebuild the logging stack after a shutdown.

        Validates that the service can be reused once closed, restoring the
        default channel.
        """
        self._logger.info("first cycle")
        self._logger.close()
        self._logger.info("second cycle")
        path = Path(self._tmp.name) / "storage" / "logs" / "stack.log"
        self.assertIn("second cycle", path.read_text(encoding="utf-8"))

class TestLoggerDestructor(TestCase):

    def testGarbageCollectionReleasesTheHandlers(self) -> None:
        """
        Release the handlers when the logger is garbage collected.

        Validates that a discarded logger never keeps file descriptors open.
        """
        with TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            logger = Logger(_make_app(tmp))
            logger.info("before collection")
            internal = logger.getLogger()
            del logger
            gc.collect()
            self.assertEqual(internal.handlers, [])
