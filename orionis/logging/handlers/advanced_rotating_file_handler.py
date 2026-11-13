# ruff: noqa: PLR0913, TC001
# Preserve handler configuration parameters and runtime resolver annotations.
"""Rotate log files using size limits and resolved time suffixes."""

from __future__ import annotations
import codecs
import gzip
import re
import shutil
import time
from logging import Handler, LogRecord
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Lock
from orionis.failure import runtime as failure_runtime
from orionis.logging.contracts.suffix_resolver import SuffixResolver

_PATH_CACHE_LIMIT = 50
"""Threshold for clearing previously resolved suffix paths."""


class AdvancedRotatingFileHandler(Handler):
    """Rotate log files using size limits and resolved time suffixes."""

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
        suffix_resolver : orionis.logging.contracts.suffix_resolver.SuffixResolver
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
        utf8_encoding = codecs.lookup(encoding).name == "utf-8"
        super().__init__()

        self.path_template = path_template
        """Path template containing the {suffix} placeholder."""
        self.suffix_resolver = suffix_resolver
        """Resolver for determining the suffix for rotation."""
        self.max_bytes = max_bytes
        """Maximum file size in bytes before rotation (for chunked rotation)."""
        self.backup_count = backup_count
        """Maximum number of backup files to retain."""
        self.encoding = encoding
        """File encoding."""
        self._utf8_encoding = utf8_encoding
        """Whether independent UTF-8 encoding gives the exact appended byte count."""
        self.delay = delay
        """If True, delay file opening until the first log record."""
        self.compress_rotated = compress_rotated
        """If True, compress rotated files using gzip."""
        self.app_root = Path(app_root)
        """Application root directory."""

        self.stream = None
        """Text stream receiving records for the active log file."""
        self.current_path = None
        """Filesystem path of the active log file."""
        self.current_suffix = None
        """Suffix identifying the active log-rotation window."""
        self.file_size = 0
        """File size value used by ``AdvancedRotatingFileHandler``."""

        # Ensure thread safety for file operations.
        self._lock = Lock()
        """Ensure thread safety for file operations."""

        # Store resolved paths for recent suffixes.
        self._path_cache: dict[str, str] = {}
        """Store resolved paths for recent suffixes."""
        self._cache_monotonic_expiry: float = 0.0
        """Cache monotonic expiry value used by ``AdvancedRotatingFileHandler``."""

        # Match rotated files belonging to this path template.
        basename = Path(path_template).name
        escaped = re.escape(basename).replace(re.escape("{suffix}"), ".*")
        self._cleanup_pattern: re.Pattern = re.compile(rf"{escaped}(?:\.gz)?\Z")
        """Compiled pattern used to recognize cleanup pattern."""

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
        # Return a path whose cache entry has not expired.
        cache_key: str = f"{self.path_template}:{suffix}"
        now_mono: float = time.monotonic()

        if now_mono < self._cache_monotonic_expiry and cache_key in self._path_cache:
            return self._path_cache[cache_key]

        # Clear old suffix paths when the cache exceeds its size limit.
        if len(self._path_cache) > _PATH_CACHE_LIMIT:
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
            The suffix already resolved by the caller.

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
        src = Path(file_path)
        dst = src.with_suffix(src.suffix + ".gz")
        temporary: Path | None = None
        try:
            # Publish only complete archives; a prior archive survives failures.
            with (
                src.open("rb") as f_in,
                NamedTemporaryFile(
                    dir=src.parent,
                    prefix=f".{src.name}.",
                    suffix=".tmp",
                    delete=False,
                ) as output,
            ):
                temporary = Path(output.name)
                with gzip.GzipFile(
                    filename=src.name,
                    mode="wb",
                    fileobj=output,
                ) as f_out:
                    shutil.copyfileobj(f_in, f_out)
            temporary.replace(dst)
            temporary = None
            # Remove the original file after compression.
            src.unlink()
        except OSError as error:
            self._observeFailure(error, phase="compression")
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError as error:
                    self._observeFailure(error, phase="compression")

    def _cleanupOldFiles(self) -> None:
        """
        Remove old log files exceeding the backup count.

        Count plain and compressed log files independently and retain the newest
        files up to the configured backup count.

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
            # Collect files matching the pattern in the directory
            related_files = [
                file_path
                for file_path in directory.glob("*")
                if file_path.is_file() and pattern.match(file_path.name)
            ]

            # Sort files by modification time, newest first
            related_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            # Remove files exceeding the backup count
            for file_path in related_files[self.backup_count :]:
                try:
                    file_path.unlink()
                except OSError as error:
                    self._observeFailure(error, phase="cleanup")
                    # Ignore errors during file removal
                    continue

        except OSError as error:
            self._observeFailure(error, phase="cleanup")
            # Ignore cleanup errors to avoid affecting logging

    def _observeFailure(self, error: BaseException, *, phase: str) -> None:
        """
        Observe a recovered sink error without changing rotation behavior.

        Parameters
        ----------
        error : BaseException
            Recovered error to submit to the failure runtime.
        phase : str
            Logging operation associated with the failure.

        Returns
        -------
        None
            This method does not return a value.
        """
        failure_runtime.capture_nowait(
            error,
            app=getattr(self, "_orionis_failure_app", None),
            flow="logging",
            phase=phase,
        )

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
        if (
            self.max_bytes is not None
            and self.current_suffix is not None
            and self.file_size < self.max_bytes
        ):
            # Request unique chunk suffixes only when a new chunk is needed.
            current_suffix = self.current_suffix
        else:
            current_suffix = self.suffix_resolver.getSuffix()

        # Check if rotation is needed before writing
        if self._shouldRotate(current_suffix):
            self._rotateFile()

        # Open a new stream if necessary or if suffix has changed.
        # A suffix change always rotates first, so the stream is None here.
        if self.stream is None or current_suffix != self.current_suffix:
            self.current_suffix = current_suffix
            self.current_path = self._resolvePath(current_suffix)

            _p = Path(self.current_path)
            self.file_size = _p.stat().st_size if _p.exists() else 0

            # Open the current file for appended log lines.
            self.stream = _p.open(
                "a",
                encoding=self.encoding,
                buffering=1,
                newline="\n",
            )

    def emit(self, record: LogRecord) -> None:
        """
        Emit a log record.

        Parameters
        ----------
        record : ``logging.LogRecord``
            The log record to emit.

        Returns
        -------
        None
            This method does not return a value.
        """
        try:
            # Format the record before acquiring the stream lock.
            msg: str = self.format(record)
            line: str = msg + "\n"
            written_bytes = len(line.encode("utf-8")) if self._utf8_encoding else None
            with self._lock:
                # Ensure the stream is ready and rotate if needed
                self._ensureStream()

                if self.stream:
                    self.stream.write(line)
                    if written_bytes is None:
                        # Preserve codec state, including BOMs and shift sequences.
                        self.file_size = self.stream.tell()
                    else:
                        self.file_size += written_bytes

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
