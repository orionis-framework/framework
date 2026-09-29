from __future__ import annotations
import gzip
import re
import shutil
import time
from logging import Handler, LogRecord
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.logging.contracts.suffix_resolver import SuffixResolver

class AdvancedRotatingFileHandler(Handler):

    # ruff: noqa: PERF401, PLR0913

    def __init__(
        self,
        path_template: str,
        suffix_resolver: SuffixResolver,
        max_bytes: int | None = None,
        backup_count: int = 5,
        encoding: str = "utf-8",
        *,
        delay: bool = True,
        compress_rotated: bool = False,
        app_root: str = ".",
    ) -> None:
        """
        Initialize the advanced rotating file handler.

        Parameters
        ----------
        path_template : str
            Path template containing the {suffix} placeholder.
        suffix_resolver : SuffixResolver
            Resolver for determining the suffix for rotation.
        max_bytes : int | None, optional
            Maximum file size in bytes before rotation (for chunked rotation).
        backup_count : int, optional
            Maximum number of backup files to retain.
        encoding : str, optional
            File encoding.
        delay : bool, optional
            If True, delay file opening until the first log record.
        compress_rotated : bool, optional
            If True, compress rotated files using gzip.
        app_root : str, optional
            Application root directory.

        Returns
        -------
        None
            This method does not return a value.
        """
        super().__init__()

        self.path_template = path_template
        self.suffix_resolver = suffix_resolver
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.encoding = encoding
        self.delay = delay
        self.compress_rotated = compress_rotated
        self.app_root = Path(app_root)

        self.stream = None
        self.current_path = None
        self.current_suffix = None
        self.file_size = 0

        # Ensure thread safety for file operations.
        self._lock = Lock()

        # Cache to avoid repeated path resolution.
        self._path_cache: dict[str, str] = {}
        self._cache_monotonic_expiry: float = 0.0

        # Precompile cleanup pattern once; path_template is immutable after init.
        _basename = path_template.rsplit("/", 1)[-1].replace("{suffix}", r".*")
        self._cleanup_pattern: re.Pattern = re.compile(_basename)

        if not self.delay:
            self._ensureStream()

    def _resolvePath(self, suffix: str) -> str:
        """
        Resolve the full path by replacing the {suffix} placeholder.

        Parameters
        ----------
        suffix : str
            Suffix to use for replacing {suffix}.

        Returns
        -------
        str
            The fully resolved file path as a string.
        """
        # Fast cache check using monotonic clock — no datetime/tz overhead
        cache_key: str = f"{self.path_template}:{suffix}"
        now_mono: float = time.monotonic()

        if now_mono < self._cache_monotonic_expiry and cache_key in self._path_cache:
            return self._path_cache[cache_key]

        # Prevent unbounded growth for chunked rotation (unique suffix per chunk)
        if len(self._path_cache) > 50:  # noqa: PLR2004
            self._path_cache.clear()

        # Replace the placeholder with the provided suffix
        resolved_path: str = self.path_template.replace("{suffix}", suffix)
        full_path: Path = self.app_root / resolved_path

        # Ensure the parent directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Update cache with the resolved path (TTL: 5 minutes)
        str_path: str = str(full_path)
        self._path_cache[cache_key] = str_path
        self._cache_monotonic_expiry = now_mono + 300.0

        # Return the resolved path
        return str_path

    def _shouldRotate(self, current_suffix: str) -> bool:
        """
        Determine whether the log file should be rotated.

        Parameters
        ----------
        current_suffix : str
            The suffix already resolved by the caller, avoiding a redundant
            getSuffix() call (C1).

        Returns
        -------
        bool
            True if the file should be rotated, otherwise False.
        """
        # Rotate if the suffix has changed (e.g., time-based rotation)
        if current_suffix != self.current_suffix:
            return True

        # Rotate if file size exceeds max_bytes (chunked rotation)
        return self.max_bytes is not None and self.file_size >= self.max_bytes

    def _rotateFile(self) -> None:
        """
        Rotate the current log file if needed.

        This method closes the current stream, compresses the rotated file if
        enabled, cleans up old log files, and resets the handler's state.

        Returns
        -------
        None
            This method does not return a value.
        """
        if self.stream:
            self.stream.close()
            self.stream = None

        # Compress the previous file if compression is enabled
        if self.compress_rotated and self.current_path:
            self._compressFile(self.current_path)

        # Remove old log files exceeding backup_count
        self._cleanupOldFiles()

        # Reset handler state for the next log file
        self.current_path = None
        self.current_suffix = None
        self.file_size = 0

    def _compressFile(self, file_path: str) -> None:
        """
        Compress the specified file using gzip.

        Parameters
        ----------
        file_path : str
            Path to the file to compress.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Reuse two Path objects instead of five temporaries
        src = Path(file_path)
        dst = src.with_suffix(src.suffix + ".gz")
        try:
            # Open the original file and create a gzip-compressed copy.
            with src.open("rb") as f_in, gzip.open(dst, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
            # Remove the original file after compression.
            src.unlink()
        except OSError:
            # If compression fails, remove the incomplete compressed file.
            if dst.exists():
                dst.unlink()

    def _cleanupOldFiles(self) -> None:
        """
        Remove old log files exceeding the backup count.

        This method deletes log files that exceed the configured backup count,
        including compressed versions if present.

        Returns
        -------
        None
            This method does not return a value.
        """
        if not self.current_path:
            return

        try:
            # Get the directory and base pattern for matching log files
            current_path: Path = Path(self.current_path)
            directory: Path = current_path.parent

            # Use precompiled pattern to match related log files
            pattern = self._cleanup_pattern
            related_files: list[Path] = []

            # Collect files matching the pattern in the directory
            for file_path in directory.glob("*"):
                if file_path.is_file() and pattern.match(file_path.name):
                    related_files.append(file_path)

            # Sort files by modification time, newest first
            related_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            # Remove files exceeding the backup count
            for file_path in related_files[self.backup_count:]:
                try:
                    file_path.unlink()
                    # Also remove compressed version if it exists
                    gz_path: Path = file_path.with_suffix(file_path.suffix + ".gz")
                    if gz_path.exists():
                        gz_path.unlink()
                except OSError:
                    # Ignore errors during file removal
                    continue

        except OSError:
            # Ignore cleanup errors to avoid affecting logging
            pass

    def _ensureStream(self) -> None:
        """
        Ensure the stream is available and up to date.

        Checks if log rotation is needed and opens a new stream if required.
        Updates the current suffix and file size accordingly.

        Returns
        -------
        None
            This method does not return a value.
        """
        current_suffix: str = self.suffix_resolver.getSuffix()

        # Check if rotation is needed before writing
        if self._shouldRotate(current_suffix):
            self._rotateFile()

        # Open a new stream if necessary or if suffix has changed.
        # A suffix change always rotates first, so the stream is None here.
        if self.stream is None or current_suffix != self.current_suffix:
            self.current_suffix = current_suffix
            self.current_path = self._resolvePath(current_suffix)

            # Single Path object avoids duplicate construction
            _p = Path(self.current_path)
            self.file_size = _p.stat().st_size if _p.exists() else 0

            # Reuse the already-constructed _p for opening
            self.stream = _p.open("a", encoding=self.encoding, buffering=1)

    def emit(self, record: LogRecord) -> None:
        """
        Emit a log record.

        Parameters
        ----------
        record : LogRecord
            The log record to emit.

        Returns
        -------
        None
            This method does not return a value.
        """
        try:
            # Format outside the lock to reduce contention under concurrency
            msg: str = self.format(record)
            line: str = msg + "\n"
            with self._lock:
                # Ensure the stream is ready and rotate if needed
                self._ensureStream()

                if self.stream:
                    self.stream.write(line)
                    self.file_size += len(msg) + 1

        except OSError:

            # Handle errors during log emission
            self.handleError(record)

    def close(self) -> None:
        """
        Close the handler and release resources.

        Closes the underlying stream if open and releases any resources held by
        the handler. Ensures thread safety during the close operation.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self._lock:
            if self.stream:
                self.stream.close()
                self.stream = None
        super().close()
