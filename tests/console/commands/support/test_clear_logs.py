from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
from orionis.console.commands.support.clear_logs import ClearLogsCommand
from orionis.logging.contracts.logger import ILogger
from orionis.test import TestCase

class _Application:
    """Expose the configured logs directory to the command."""

    __slots__ = ("basePath", "channels", "logs_path")

    def __init__(
        self,
        logs_path: Path,
        *,
        base_path: Path | None = None,
        channels: dict[str, dict[str, str]] | None = None,
    ) -> None:
        """Store the configured logs directory.

        Parameters
        ----------
        logs_path : Path
            Directory containing application log files.
        base_path : Path | None, optional
            Application root used to resolve relative channel paths.
        channels : dict[str, dict[str, str]] | None, optional
            Channel paths declared by the application.
        """
        self.logs_path = logs_path
        self.basePath = base_path or logs_path.parent
        self.channels = channels

    def config(self, key: str) -> object:
        """Return configured logging channels.

        Parameters
        ----------
        key : str
            Configuration key requested by the command.

        Returns
        -------
        object
            Configured channels or None for another key.
        """
        return self.channels if key == "logging.channels" else None

    def path(self, key: str) -> Path:
        """Return the configured logs directory by its path key.

        Parameters
        ----------
        key : str
            Application path key requested by the command.

        Returns
        -------
        Path
            Configured logs directory.

        Raises
        ------
        KeyError
            If the requested path key is unsupported.
        """
        if key != "storage_logs":
            raise KeyError(key)
        return self.logs_path


class TestClearLogsCommand(TestCase):
    """Verify cleanup of framework log files."""

    def testRemovesNestedLogsAndCompressedArchivesOnly(self) -> None:
        """Delete logs below the configured directory and preserve other data.

        Returns
        -------
        None
            Assertions verify recursive deletion and directory preservation.
        """
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            logs = root / "custom" / "framework-logs"
            nested = logs / "daily" / "older"
            nested.mkdir(parents=True)
            generated = (
                logs / "stack.log",
                nested / "daily_2026-09-30.log",
                nested / "chunked_1.log.gz",
            )
            for log in generated:
                log.write_text("generated", encoding="utf-8")
            metadata = nested / "notes.txt"
            metadata.write_text("keep", encoding="utf-8")
            outside = root / "storage" / "logs" / "outside.log"
            outside.parent.mkdir(parents=True)
            outside.write_text("keep", encoding="utf-8")
            console = Mock()
            logger = Mock(spec=ILogger)

            result = ClearLogsCommand().handle(_Application(logs), console, logger)

            self.assertEqual(result, 0)
            for log in generated:
                self.assertFalse(log.exists())
            self.assertTrue(metadata.is_file())
            self.assertTrue(nested.is_dir())
            self.assertTrue(outside.is_file())
            logger.close.assert_called_once_with()
            console.error.assert_not_called()

    def testMissingLogsDirectoryIsAnIdempotentSuccess(self) -> None:
        """Succeed when the configured logs directory is absent.

        Returns
        -------
        None
            Assertions verify repeated cleanup without a directory succeeds.
        """
        with TemporaryDirectory() as temporary:
            logs = Path(temporary) / "missing" / "logs"
            app = _Application(logs)
            console = Mock()
            logger = Mock(spec=ILogger)
            command = ClearLogsCommand()

            self.assertEqual(command.handle(app, console, logger), 0)
            self.assertEqual(command.handle(app, console, logger), 0)
            self.assertFalse(logs.exists())
            console.error.assert_not_called()

    def testClearsOnlyConfiguredLogsOutsideTheStandardDirectory(self) -> None:
        """Delete external channel logs without clearing adjacent files.

        Returns
        -------
        None
            Assertions verify exact and rotated configured paths.
        """
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            logs = root / "storage" / "logs"
            logs.mkdir(parents=True)
            standard_log = logs / "stack.log"
            standard_log.write_text("standard", encoding="utf-8")
            external = root / "external"
            external.mkdir()
            configured = (
                external / "service.log",
                external / "daily_2026-09-30.log",
                external / "daily_2026-09-29.log.gz",
            )
            for path in configured:
                path.write_text("generated", encoding="utf-8")
            unrelated = external / "other.log"
            unrelated.write_text("keep", encoding="utf-8")
            app = _Application(
                logs,
                base_path=root,
                channels={
                    "stack": {"path": str(configured[0])},
                    "daily": {"path": "external/daily_{suffix}.log"},
                },
            )

            result = ClearLogsCommand().handle(app, Mock(), Mock(spec=ILogger))

            self.assertEqual(result, 0)
            self.assertFalse(standard_log.exists())
            for path in configured:
                self.assertFalse(path.exists())
            self.assertTrue(unrelated.is_file())

    def testReportsRemovalErrorsAndContinuesCleaning(self) -> None:
        """Report a failed unlink and remove other log files.

        Returns
        -------
        None
            Assertions verify a nonzero result and continued cleanup.
        """
        with TemporaryDirectory() as temporary:
            logs = Path(temporary) / "logs"
            logs.mkdir()
            protected = logs / "protected.log"
            removable = logs / "removable.log"
            protected.write_text("keep", encoding="utf-8")
            removable.write_text("remove", encoding="utf-8")
            original_unlink = Path.unlink

            def unlink_with_failure(
                path: Path, *args: object, **kwargs: object,
            ) -> None:
                """Raise for one log and unlink all other paths.

                Parameters
                ----------
                path : Path
                    Path selected for removal.
                *args : object
                    Positional arguments for ``Path.unlink``.
                **kwargs : object
                    Keyword arguments for ``Path.unlink``.

                Raises
                ------
                PermissionError
                    If the protected log is selected.
                """
                if path == protected:
                    message = "permission denied"
                    raise PermissionError(message)
                original_unlink(path, *args, **kwargs)

            console = Mock()
            logger = Mock(spec=ILogger)
            with patch.object(Path, "unlink", new=unlink_with_failure):
                result = ClearLogsCommand().handle(
                    _Application(logs), console, logger,
                )

            self.assertEqual(result, 1)
            self.assertTrue(protected.is_file())
            self.assertFalse(removable.exists())
            logger.close.assert_called_once_with()
            self.assertTrue(console.error.called)
            self.assertIn("permission denied", console.error.call_args.args[0])

    def testClosesLoggerBeforeRemovingItsFile(self) -> None:
        """Release logger file handles before deleting log files.

        Returns
        -------
        None
            Assertions verify closing precedes the first unlink operation.
        """
        with TemporaryDirectory() as temporary:
            logs = Path(temporary) / "logs"
            logs.mkdir()
            log = logs / "stack.log"
            log.write_text("entry", encoding="utf-8")
            original_unlink = Path.unlink
            logger = Mock(spec=ILogger)

            def unlink_after_close(path: Path, *args: object, **kwargs: object) -> None:
                """Verify the logger is closed before a file is removed.

                Parameters
                ----------
                path : Path
                    Path selected for removal.
                *args : object
                    Positional arguments for ``Path.unlink``.
                **kwargs : object
                    Keyword arguments for ``Path.unlink``.
                """
                if path == log:
                    self.assertTrue(logger.close.called)
                original_unlink(path, *args, **kwargs)

            with patch.object(Path, "unlink", new=unlink_after_close):
                result = ClearLogsCommand().handle(
                    _Application(logs), Mock(), logger,
                )

            self.assertEqual(result, 0)
            self.assertFalse(log.exists())
            logger.close.assert_called_once_with()
