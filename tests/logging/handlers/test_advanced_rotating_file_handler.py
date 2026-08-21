import gzip
import logging
import os
from contextlib import redirect_stderr
from datetime import datetime, timedelta
from io import StringIO
from logging import LogRecord
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis.logging.contracts.suffix_resolver import SuffixResolver
from orionis.logging.handlers.advanced_rotating_file_handler import (
    AdvancedRotatingFileHandler,
)
from orionis.test import TestCase

# Template shared by every handler built in this module.
_PATH_TEMPLATE = "logs/app_{suffix}.log"

# Directory, relative to the application root, holding the produced files.
_LOG_DIR = "logs"

# Number of distinct suffixes required to overflow the internal path cache.
_CACHE_OVERFLOW = 52

class _FixedSuffixResolver(SuffixResolver):
    """Rotation strategy returning a suffix controlled by the test."""

    __slots__ = ("suffix",)

    def __init__(self, suffix: str = "fixed") -> None:
        """Store the suffix reported to the handler."""
        self.suffix = suffix

    def getSuffix(self, _dt: object = None) -> str:
        """Return the suffix currently configured."""
        return self.suffix

    def getNextRotationTime(self, current_time: datetime) -> datetime:
        """Return the moment one hour after the supplied one."""
        return current_time + timedelta(hours=1)

class _ExplodingStream:
    """Stream double failing on every write attempt."""

    __slots__ = ("attempts", "closed")

    def __init__(self) -> None:
        """Prepare the counters inspected by the assertions."""
        self.attempts: int = 0
        self.closed: bool = False

    def write(self, _line: str) -> int:
        """Fail instead of writing the supplied line."""
        self.attempts += 1
        error_msg = "the stream is not writable"
        raise OSError(error_msg)

    def close(self) -> None:
        """Mark the stream as closed."""
        self.closed = True

class _ExplodingPattern:
    """Pattern double failing on every file name inspection."""

    __slots__ = ()

    def match(self, _name: str) -> None:
        """Fail instead of matching the supplied file name."""
        error_msg = "the file name cannot be inspected"
        raise OSError(error_msg)

def _make_handler(  # noqa: PLR0913
    root: str,
    *,
    resolver: SuffixResolver | None = None,
    path_template: str = _PATH_TEMPLATE,
    max_bytes: int | None = None,
    backup_count: int = 5,
    delay: bool = True,
    compress_rotated: bool = False,
) -> AdvancedRotatingFileHandler:
    """Return a rotating handler anchored to the given application root."""
    return AdvancedRotatingFileHandler(
        path_template=path_template,
        suffix_resolver=resolver or _FixedSuffixResolver(),
        max_bytes=max_bytes,
        backup_count=backup_count,
        delay=delay,
        compress_rotated=compress_rotated,
        app_root=root,
    )

def _make_record(message: str = "log record") -> LogRecord:
    """Return a minimal informational record."""
    return LogRecord(
        name="tests.logging",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )

def _seed_file(directory: Path, name: str, mtime: float) -> Path:
    """Create a file with a deterministic modification time."""
    path = directory / name
    path.write_text("seeded content", encoding="utf-8")
    os.utime(path, (mtime, mtime))
    return path

class TestAdvancedRotatingFileHandlerInitialisation(TestCase):

    def setUp(self) -> None:
        """Create a temporary application root and the handler registry."""
        self._tmp = TemporaryDirectory(ignore_cleanup_errors=True)
        self._handlers: list[AdvancedRotatingFileHandler] = []

    def tearDown(self) -> None:
        """Close every built handler and delete the temporary root."""
        for handler in self._handlers:
            handler.close()
        self._tmp.cleanup()

    def testDelayedHandlerKeepsTheStreamClosed(self) -> None:
        """
        Postpone opening the file until the first record.

        Validates that configuring a channel never creates an empty log file.
        """
        handler = _make_handler(self._tmp.name)
        self._handlers.append(handler)
        self.assertIsNone(handler.stream)

    def testEagerHandlerOpensTheStreamImmediately(self) -> None:
        """
        Open the file as soon as the handler is built.

        Validates the eager mode used when logging must never be delayed.
        """
        handler = _make_handler(self._tmp.name, delay=False)
        self._handlers.append(handler)
        self.assertIsNotNone(handler.stream)

    def testConstructorStoresTheRotationSettings(self) -> None:
        """
        Keep every rotation setting supplied to the constructor.

        Validates that the factory options survive untouched in the handler.
        """
        handler = _make_handler(
            self._tmp.name,
            path_template="logs/custom_{suffix}.log",
            max_bytes=1024,
            backup_count=10,
            compress_rotated=True,
        )
        self._handlers.append(handler)
        self.assertEqual(handler.path_template, "logs/custom_{suffix}.log")
        self.assertEqual(handler.max_bytes, 1024)
        self.assertEqual(handler.backup_count, 10)
        self.assertTrue(handler.compress_rotated)

    def testConstructorAnchorsTheApplicationRoot(self) -> None:
        """
        Convert the application root into a path object.

        Validates that relative templates are always resolved from the project
        directory.
        """
        handler = _make_handler(self._tmp.name)
        self._handlers.append(handler)
        self.assertEqual(handler.app_root, Path(self._tmp.name))

    def testConstructorCompilesTheCleanupPattern(self) -> None:
        """
        Compile the pattern matching the files owned by the channel.

        Validates that only the files produced by this template are eligible
        for removal.
        """
        handler = _make_handler(self._tmp.name)
        self._handlers.append(handler)
        self.assertTrue(handler._cleanup_pattern.match("app_2025-04-09.log"))
        self.assertIsNone(handler._cleanup_pattern.match("other.log"))

class TestAdvancedRotatingFileHandlerPathResolution(TestCase):

    def setUp(self) -> None:
        """Create a temporary application root and a delayed handler."""
        self._tmp = TemporaryDirectory(ignore_cleanup_errors=True)
        self._handler = _make_handler(self._tmp.name)

    def tearDown(self) -> None:
        """Close the handler and delete the temporary root."""
        self._handler.close()
        self._tmp.cleanup()

    def testResolvedPathReplacesThePlaceholder(self) -> None:
        """
        Replace the suffix placeholder of the configured template.

        Validates the file name produced for a given rotation window.
        """
        resolved = self._handler._resolvePath("2025-04-09_14")
        self.assertEqual(Path(resolved).name, "app_2025-04-09_14.log")

    def testResolvedPathIsAnchoredToTheApplicationRoot(self) -> None:
        """
        Resolve the template against the application root.

        Validates that relative templates never depend on the working
        directory.
        """
        resolved = Path(self._handler._resolvePath("anchored"))
        self.assertEqual(resolved.parent, Path(self._tmp.name) / _LOG_DIR)

    def testResolvedPathCreatesTheParentDirectory(self) -> None:
        """
        Create the directory tree required by the resolved path.

        Validates that a missing folder never prevents the file from opening.
        """
        handler = _make_handler(
            self._tmp.name,
            path_template="deep/nested/logs/app_{suffix}.log",
        )
        try:
            handler._resolvePath("nested")
            expected = Path(self._tmp.name) / "deep" / "nested" / "logs"
            self.assertTrue(expected.is_dir())
        finally:
            handler.close()

    def testResolvedPathIsCachedPerSuffix(self) -> None:
        """
        Reuse the cached path when the suffix has not changed.

        Validates the cache that keeps the hot logging path free of filesystem
        work.
        """
        first = self._handler._resolvePath("cached")
        second = self._handler._resolvePath("cached")
        self.assertIs(first, second)

    def testDifferentSuffixesResolveToDifferentPaths(self) -> None:
        """
        Produce one path per rotation window.

        Validates that the cache never mixes two different suffixes.
        """
        self.assertNotEqual(
            self._handler._resolvePath("2025-04-09_14"),
            self._handler._resolvePath("2025-04-09_15"),
        )

    def testPathCacheIsClearedWhenItGrowsTooMuch(self) -> None:
        """
        Discard the cached paths once the cache grows beyond its limit.

        Validates the guard protecting size based rotation, which produces a
        unique suffix on every chunk.
        """
        for index in range(_CACHE_OVERFLOW):
            self._handler._resolvePath(f"suffix-{index}")
        self.assertEqual(len(self._handler._path_cache), 1)

class TestAdvancedRotatingFileHandlerRotationDecision(TestCase):

    def setUp(self) -> None:
        """Create a temporary application root and the handler registry."""
        self._tmp = TemporaryDirectory(ignore_cleanup_errors=True)
        self._handlers: list[AdvancedRotatingFileHandler] = []

    def tearDown(self) -> None:
        """Close every built handler and delete the temporary root."""
        for handler in self._handlers:
            handler.close()
        self._tmp.cleanup()

    def testRotationIsRequiredWhenTheSuffixChanges(self) -> None:
        """
        Rotate as soon as the rotation window changes.

        Validates the time based rotation trigger.
        """
        handler = _make_handler(self._tmp.name)
        self._handlers.append(handler)
        handler.current_suffix = "1970-01-01"
        self.assertTrue(handler._shouldRotate("2025-04-09"))

    def testRotationIsRequiredWhenTheSizeReachesTheThreshold(self) -> None:
        """
        Rotate as soon as the file reaches the configured size.

        Validates the size based rotation trigger.
        """
        handler = _make_handler(self._tmp.name, max_bytes=100)
        self._handlers.append(handler)
        handler.current_suffix = "stable"
        handler.file_size = 100
        self.assertTrue(handler._shouldRotate("stable"))

    def testRotationIsSkippedBelowTheThreshold(self) -> None:
        """
        Keep writing while the file stays below the configured size.

        Validates the steady state of a size based channel.
        """
        handler = _make_handler(self._tmp.name, max_bytes=100)
        self._handlers.append(handler)
        handler.current_suffix = "stable"
        handler.file_size = 99
        self.assertFalse(handler._shouldRotate("stable"))

    def testRotationIsSkippedWithoutASizeThreshold(self) -> None:
        """
        Keep writing when no size threshold is configured.

        Validates the steady state of a purely time based channel.
        """
        handler = _make_handler(self._tmp.name)
        self._handlers.append(handler)
        handler.current_suffix = "stable"
        handler.file_size = 10_000
        self.assertFalse(handler._shouldRotate("stable"))

class TestAdvancedRotatingFileHandlerEmit(TestCase):

    def setUp(self) -> None:
        """Create a temporary application root and a delayed handler."""
        self._tmp = TemporaryDirectory(ignore_cleanup_errors=True)
        self._resolver = _FixedSuffixResolver("emit")
        self._handler = _make_handler(self._tmp.name, resolver=self._resolver)

    def tearDown(self) -> None:
        """Close the handler and delete the temporary root."""
        self._handler.close()
        self._tmp.cleanup()

    def _readLog(self) -> str:
        """Return the content of the file currently written by the handler."""
        return Path(self._tmp.name, _LOG_DIR, "app_emit.log").read_text(
            encoding="utf-8",
        )

    def testEmitCreatesTheLogFile(self) -> None:
        """
        Create the log file on the first emitted record.

        Validates the lazy stream opening performed by the handler.
        """
        self._handler.emit(_make_record())
        self.assertTrue(Path(self._tmp.name, _LOG_DIR, "app_emit.log").exists())

    def testEmitWritesTheFormattedRecord(self) -> None:
        """
        Write the formatted message followed by a line break.

        Validates the payload handed over to the underlying stream.
        """
        self._handler.emit(_make_record("first message"))
        self.assertEqual(self._readLog(), "first message\n")

    def testEmitAppendsEveryRecord(self) -> None:
        """
        Append each record to the file already opened.

        Validates that the stream is reused instead of truncating the file.
        """
        self._handler.emit(_make_record("first message"))
        self._handler.emit(_make_record("second message"))
        self.assertEqual(self._readLog(), "first message\nsecond message\n")

    def testEmitTracksTheWrittenSize(self) -> None:
        """
        Account for every written byte, including the line break.

        Validates the counter driving size based rotation.
        """
        self._handler.emit(_make_record("12345"))
        self.assertEqual(self._handler.file_size, 6)

    def testEmitReportsWriteFailuresThroughTheHandlerHook(self) -> None:
        """
        Report a failing stream through the standard error hook.

        Validates that a broken log file never propagates an exception into
        the caller of the logging methods.
        """
        stream = _ExplodingStream()
        self._handler.current_suffix = self._resolver.suffix
        self._handler.current_path = str(
            Path(self._tmp.name, _LOG_DIR, "app_emit.log"),
        )
        self._handler.stream = stream  # type: ignore[assignment]
        buffer = StringIO()
        with redirect_stderr(buffer):
            self._handler.emit(_make_record("never written"))
        self.assertEqual(stream.attempts, 1)
        self.assertIn("--- Logging error ---", buffer.getvalue())

class TestAdvancedRotatingFileHandlerRotation(TestCase):

    def setUp(self) -> None:
        """Create a temporary application root and the handler registry."""
        self._tmp = TemporaryDirectory(ignore_cleanup_errors=True)
        self._handlers: list[AdvancedRotatingFileHandler] = []

    def tearDown(self) -> None:
        """Close every built handler and delete the temporary root."""
        for handler in self._handlers:
            handler.close()
        self._tmp.cleanup()

    def testSuffixChangeOpensANewFile(self) -> None:
        """
        Write to a new file once the rotation window changes.

        Validates that records never leak into the closed window.
        """
        resolver = _FixedSuffixResolver("first")
        handler = _make_handler(self._tmp.name, resolver=resolver)
        self._handlers.append(handler)
        handler.emit(_make_record("first window"))
        resolver.suffix = "second"
        handler.emit(_make_record("second window"))
        produced = sorted(
            path.name
            for path in Path(self._tmp.name, _LOG_DIR).glob("*.log")
        )
        self.assertEqual(produced, ["app_first.log", "app_second.log"])

    def testRotationCompressesTheClosedFile(self) -> None:
        """
        Archive the closed file when compression is enabled.

        Validates the size based channel policy of compressing every chunk.
        """
        resolver = _FixedSuffixResolver("first")
        handler = _make_handler(
            self._tmp.name,
            resolver=resolver,
            compress_rotated=True,
        )
        self._handlers.append(handler)
        handler.emit(_make_record("first window"))
        resolver.suffix = "second"
        handler.emit(_make_record("second window"))
        archive = Path(self._tmp.name, _LOG_DIR, "app_first.log.gz")
        self.assertTrue(archive.exists())
        self.assertFalse(Path(self._tmp.name, _LOG_DIR, "app_first.log").exists())

    def testRotationResetsTheHandlerState(self) -> None:
        """
        Forget the current file once the rotation completes.

        Validates that the next record reopens a stream from scratch.
        """
        handler = _make_handler(self._tmp.name)
        self._handlers.append(handler)
        handler.emit(_make_record())
        handler._rotateFile()
        self.assertIsNone(handler.stream)
        self.assertIsNone(handler.current_path)
        self.assertIsNone(handler.current_suffix)
        self.assertEqual(handler.file_size, 0)

    def testRotationWithoutAnOpenStreamDoesNotRaise(self) -> None:
        """
        Rotate an idle handler without raising.

        Validates the guard protecting a rotation requested before the first
        record.
        """
        handler = _make_handler(self._tmp.name)
        self._handlers.append(handler)
        handler._rotateFile()
        self.assertIsNone(handler.current_path)

    def testReopeningAWindowKeepsTheExistingSize(self) -> None:
        """
        Restore the size of a file written by a previous run.

        Validates that an existing file is appended to instead of being
        measured as empty, which would postpone size based rotation.
        """
        resolver = _FixedSuffixResolver("resumed")
        first = _make_handler(self._tmp.name, resolver=resolver)
        first.emit(_make_record("12345"))
        first.close()
        written = Path(self._tmp.name, _LOG_DIR, "app_resumed.log").stat().st_size
        second = _make_handler(self._tmp.name, resolver=resolver)
        self._handlers.append(second)
        second.emit(_make_record("67890"))
        self.assertEqual(second.file_size, written + len("67890\n"))

class TestAdvancedRotatingFileHandlerCompression(TestCase):

    def setUp(self) -> None:
        """Create a temporary application root and a compressing handler."""
        self._tmp = TemporaryDirectory(ignore_cleanup_errors=True)
        self._handler = _make_handler(self._tmp.name, compress_rotated=True)

    def tearDown(self) -> None:
        """Close the handler and delete the temporary root."""
        self._handler.close()
        self._tmp.cleanup()

    def testCompressionCreatesAGzipArchive(self) -> None:
        """
        Archive the supplied file next to the original one.

        Validates the naming scheme of the produced archive.
        """
        source = Path(self._tmp.name) / "rotated.log"
        source.write_text("archived content", encoding="utf-8")
        self._handler._compressFile(str(source))
        self.assertTrue(Path(self._tmp.name, "rotated.log.gz").exists())

    def testCompressionRemovesTheOriginalFile(self) -> None:
        """
        Remove the original file once it has been archived.

        Validates that compression never duplicates the stored data.
        """
        source = Path(self._tmp.name) / "rotated.log"
        source.write_text("archived content", encoding="utf-8")
        self._handler._compressFile(str(source))
        self.assertFalse(source.exists())

    def testArchiveContainsTheOriginalBytes(self) -> None:
        """
        Preserve the original content inside the archive.

        Validates that the produced file is a readable gzip stream.
        """
        source = Path(self._tmp.name) / "rotated.log"
        source.write_bytes(b"verifiable gzip content")
        self._handler._compressFile(str(source))
        with gzip.open(Path(self._tmp.name, "rotated.log.gz"), "rb") as archive:
            self.assertEqual(archive.read(), b"verifiable gzip content")

    def testMissingSourceIsIgnored(self) -> None:
        """
        Ignore a compression request for a missing file.

        Validates that a failed rotation never interrupts logging.
        """
        missing = Path(self._tmp.name) / "ghost.log"
        self._handler._compressFile(str(missing))
        self.assertFalse(Path(self._tmp.name, "ghost.log.gz").exists())

    def testFailedCompressionRemovesThePartialArchive(self) -> None:
        """
        Remove the archive left behind by a failed compression.

        Validates that an unreadable source never leaves a truncated file
        pretending to hold the rotated records.
        """
        unreadable = Path(self._tmp.name) / "rotated.log"
        unreadable.mkdir()
        archive = Path(self._tmp.name) / "rotated.log.gz"
        archive.write_text("stale archive", encoding="utf-8")
        self._handler._compressFile(str(unreadable))
        self.assertFalse(archive.exists())
        self.assertTrue(unreadable.is_dir())

class TestAdvancedRotatingFileHandlerCleanup(TestCase):

    def setUp(self) -> None:
        """Create a temporary application root and the log directory."""
        self._tmp = TemporaryDirectory(ignore_cleanup_errors=True)
        self._logs = Path(self._tmp.name) / _LOG_DIR
        self._logs.mkdir(parents=True, exist_ok=True)
        self._handlers: list[AdvancedRotatingFileHandler] = []

    def tearDown(self) -> None:
        """Close every built handler and delete the temporary root."""
        for handler in self._handlers:
            handler.close()
        self._tmp.cleanup()

    def _makeHandler(self, backup_count: int) -> AdvancedRotatingFileHandler:
        """Return a tracked handler keeping the given number of files."""
        handler = _make_handler(self._tmp.name, backup_count=backup_count)
        self._handlers.append(handler)
        return handler

    def testCleanupIsSkippedWithoutAnActiveFile(self) -> None:
        """
        Skip the cleanup while no file has been opened.

        Validates that an idle handler never inspects the log directory.
        """
        stale = _seed_file(self._logs, "app_stale.log", 1000)
        self._makeHandler(1)._cleanupOldFiles()
        self.assertTrue(stale.exists())

    def testCleanupRemovesTheFilesBeyondTheBackupCount(self) -> None:
        """
        Keep only the newest files allowed by the backup count.

        Validates the retention policy applied after every rotation.
        """
        newest = _seed_file(self._logs, "app_3.log", 3000)
        middle = _seed_file(self._logs, "app_2.log", 2000)
        oldest = _seed_file(self._logs, "app_1.log", 1000)
        handler = self._makeHandler(2)
        handler.current_path = str(newest)
        handler._cleanupOldFiles()
        self.assertTrue(newest.exists())
        self.assertTrue(middle.exists())
        self.assertFalse(oldest.exists())

    def testCleanupRemovesTheArchiveOfADiscardedFile(self) -> None:
        """
        Remove the archive belonging to a discarded log file.

        Validates that compressed rotations are subject to the same retention
        policy, and that a file removed twice is silently ignored.
        """
        newest = _seed_file(self._logs, "app_keep.log", 3000)
        discarded = _seed_file(self._logs, "app_drop.log", 2000)
        archive = _seed_file(self._logs, "app_drop.log.gz", 1000)
        handler = self._makeHandler(1)
        handler.current_path = str(newest)
        handler._cleanupOldFiles()
        self.assertTrue(newest.exists())
        self.assertFalse(discarded.exists())
        self.assertFalse(archive.exists())

    def testCleanupIgnoresFilesOwnedByAnotherChannel(self) -> None:
        """
        Preserve the files produced by another channel.

        Validates that the compiled pattern scopes the retention policy to the
        files of this template.
        """
        newest = _seed_file(self._logs, "app_1.log", 2000)
        foreign = _seed_file(self._logs, "other.log", 1000)
        handler = self._makeHandler(1)
        handler.current_path = str(newest)
        handler._cleanupOldFiles()
        self.assertTrue(foreign.exists())

    def testCleanupNeverPropagatesFilesystemErrors(self) -> None:
        """
        Swallow any error raised while inspecting the log directory.

        Validates that a failing cleanup never breaks the logging pipeline.
        """
        stale = _seed_file(self._logs, "app_1.log", 1000)
        handler = self._makeHandler(1)
        handler.current_path = str(stale)
        handler._cleanup_pattern = _ExplodingPattern()  # type: ignore[assignment]
        handler._cleanupOldFiles()
        self.assertTrue(stale.exists())

class TestAdvancedRotatingFileHandlerClose(TestCase):

    def setUp(self) -> None:
        """Create a temporary application root and a delayed handler."""
        self._tmp = TemporaryDirectory(ignore_cleanup_errors=True)
        self._handler = _make_handler(self._tmp.name)

    def tearDown(self) -> None:
        """Delete the temporary root."""
        self._tmp.cleanup()

    def testCloseReleasesTheStream(self) -> None:
        """
        Release the file descriptor held by the handler.

        Validates that a closed handler never keeps the log file locked.
        """
        self._handler.emit(_make_record())
        self._handler.close()
        self.assertIsNone(self._handler.stream)

    def testCloseWithoutAnOpenStreamDoesNotRaise(self) -> None:
        """
        Close an idle handler without raising.

        Validates the guard protecting a handler that never emitted a record.
        """
        self._handler.close()
        self.assertIsNone(self._handler.stream)

    def testCloseIsIdempotent(self) -> None:
        """
        Allow repeated close calls without raising.

        Validates that shutting down an already closed handler is a no-op.
        """
        self._handler.emit(_make_record())
        self._handler.close()
        self._handler.close()
        self.assertIsNone(self._handler.stream)
