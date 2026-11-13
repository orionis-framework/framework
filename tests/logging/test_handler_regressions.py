# ruff: noqa: PT009, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Protect logging byte counts, retained archives, and runtime annotations."""

import gzip
import logging
import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import get_type_hints
from unittest.mock import Mock, patch

from orionis.logging.contracts.suffix_resolver import SuffixResolver
from orionis.logging.handlers.advanced_rotating_file_handler import (
    AdvancedRotatingFileHandler,
)
from orionis.logging.handlers.queued import observe_sink_error
from orionis.logging.handlers.rotating_handler_factory import RotatingHandlerFactory
from orionis.test import TestCase


class TestLoggingHandlerRegressions(TestCase):
    """Check handler behavior using owned files and deterministic suffixes."""

    def setUp(self) -> None:
        """Create a directory owned exclusively by this test."""
        super().setUp()
        self._root = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def _handler(self, encoding: str = "utf-8") -> AdvancedRotatingFileHandler:
        """Create an owned handler with a stable rotation suffix.

        Parameters
        ----------
        encoding : str
            Text encoding exercised by the handler.

        Returns
        -------
        AdvancedRotatingFileHandler
            Handler scheduled for cleanup after the test.
        """
        resolver = Mock(spec=SuffixResolver)
        resolver.getSuffix.return_value = "fixed"
        handler = AdvancedRotatingFileHandler(
            "log_{suffix}.log",
            resolver,
            backup_count=1,
            encoding=encoding,
            app_root=str(self._root / encoding),
        )
        self.addCleanup(handler.close)
        return handler

    def testCountsByteOrderMarksOnlyWhenWritten(self) -> None:
        """Track actual bytes after repeated writes with a byte-order-mark codec."""
        for encoding in ("utf-16", "utf-32", "utf-8-sig"):
            with self.subTest(encoding=encoding):
                handler = self._handler(encoding)
                for message in ("first", "second"):
                    handler.emit(
                        logging.LogRecord("test", 20, "", 1, message, (), None),
                    )
                path = Path(handler.current_path)
                self.assertEqual(handler.file_size, path.stat().st_size)
                self.assertEqual(path.read_text(encoding=encoding), "first\nsecond\n")

    def testPreservesTheNewestArchiveWhenItsPlainSiblingExpires(self) -> None:
        """Remove only retention candidates without deleting a retained sibling."""
        plain = self._root / "log_fixed.log"
        plain.write_text("older", encoding="utf-8")
        archive = self._root / "log_fixed.log.gz"
        with gzip.open(archive, "wb") as stream:
            stream.write(b"newest")
        os.utime(plain, (1000, 1000))
        os.utime(archive, (2000, 2000))
        handler = self._handler()
        handler.current_path = str(plain)
        handler._cleanupOldFiles()
        self.assertTrue(archive.exists())
        self.assertFalse(plain.exists())

    def testPreservesExistingArchiveWhenCompressionFails(self) -> None:
        """Keep prior compressed content when a replacement cannot complete."""
        source = self._root / "collision.log"
        source.write_bytes(b"new content")
        archive = self._root / "collision.log.gz"
        with gzip.open(archive, "wb") as stream:
            stream.write(b"previous content")
        handler = self._handler()
        with patch(
            "orionis.logging.handlers.advanced_rotating_file_handler.shutil.copyfileobj",
            side_effect=OSError("compression unavailable"),
        ):
            handler._compressFile(str(source))
        self.assertTrue(archive.exists())
        with gzip.open(archive, "rb") as stream:
            self.assertEqual(stream.read(), b"previous content")
        self.assertEqual(source.read_bytes(), b"new content")

    def testResolvesHandlerAnnotations(self) -> None:
        """Resolve runtime types used by handler factories and callbacks."""
        for function, parameter, expected in (
            (AdvancedRotatingFileHandler.__init__, "suffix_resolver", SuffixResolver),
            (RotatingHandlerFactory.createHandler, "return", logging.Handler | None),
            (observe_sink_error, "original", Callable[[logging.LogRecord], None]),
        ):
            with self.subTest(function=function.__qualname__):
                self.assertEqual(get_type_hints(function)[parameter], expected)
