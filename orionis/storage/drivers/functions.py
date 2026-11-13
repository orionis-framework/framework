# ruff: noqa: BLE001, PLC0415, TC003
# Preserve primary failures while observing secondary cleanup errors centrally.
# Expose public helper annotations to runtime dependency reflection.
"""Provide shared binary buffers, dependency loading and object-key helpers."""

from __future__ import annotations
import importlib
import asyncio
from collections.abc import Iterable, Iterator
from io import BufferedIOBase, UnsupportedOperation
from pathlib import Path, PurePosixPath
from types import ModuleType
from typing import BinaryIO
from orionis.storage.exceptions import (
    MissingStorageDependencyException,
    UnsupportedStorageOperationException,
)

# Binary modes accepted by driver open() implementations.
_ALLOWED_MODES: frozenset[str] = frozenset(
    {"rb", "wb", "ab", "rb+", "wb+", "ab+"},
)
"""Binary modes accepted by driver open() implementations."""


class _ModeBuffer(BufferedIOBase):
    """Enforce binary access modes while owning a buffered storage payload."""

    __slots__ = ("_mode", "raw")
    """Reserve the binary mode and the owned underlying buffer."""

    def __init__(self, raw: BinaryIO, mode: str) -> None:
        """Own a buffer and apply the driver's validated binary mode.

        Parameters
        ----------
        raw : typing.BinaryIO
            Buffer used by internal persistence callbacks.
        mode : str
            Validated binary read, write or append mode.

        Returns
        -------
        None
            No return value.
        """
        self.raw = raw
        """Keep the underlying buffer available to persistence callbacks."""
        self._mode = mode
        """Store the binary mode controlling the wrapper's I/O permissions."""
        assert_binary_mode(mode)

    @property
    def closed(self) -> bool:
        """Report whether the wrapper or its owned buffer has closed.

        Returns
        -------
        bool
            Whether further I/O is unavailable.
        """
        raw = getattr(self, "raw", None)
        return raw is None or raw.closed or super().closed

    def _requireOpen(self) -> None:
        """Reject operations after the buffer has closed.

        Returns
        -------
        None
            No return value.
        """
        if self.closed:
            message = "I/O operation on closed file."
            raise ValueError(message)

    def readable(self) -> bool:
        """Report whether the selected mode permits reading.

        Returns
        -------
        bool
            Whether reads are permitted on the open buffer.
        """
        self._requireOpen()
        return self._mode.startswith("r") or "+" in self._mode

    def writable(self) -> bool:
        """Report whether the selected mode permits writing.

        Returns
        -------
        bool
            Whether writes are permitted on the open buffer.
        """
        self._requireOpen()
        return self._mode != "rb"

    def seekable(self) -> bool:
        """Report whether the owned buffer supports seeking.

        Returns
        -------
        bool
            Whether the open buffer supports random access.
        """
        self._requireOpen()
        return self.raw.seekable()

    def _requireReadable(self) -> None:
        """Reject reads disallowed by the selected mode.

        Returns
        -------
        None
            No return value.
        """
        if not self.readable():
            message = "Buffer is not readable."
            raise UnsupportedOperation(message)

    def _requireWritable(self) -> None:
        """Reject writes disallowed by the selected mode.

        Returns
        -------
        None
            No return value.
        """
        if not self.writable():
            message = "Buffer is not writable."
            raise UnsupportedOperation(message)

    def read(self, size: int = -1) -> bytes:
        """Read at most the requested number of bytes.

        Parameters
        ----------
        size : int
            Byte limit, or -1 to read the remaining content.

        Returns
        -------
        bytes
            Content read from the current position.
        """
        self._requireReadable()
        return self.raw.read(size)

    def read1(self, size: int = -1) -> bytes:
        """Read one logical block from the already buffered payload.

        Parameters
        ----------
        size : int
            Maximum bytes to return, or -1 for all remaining bytes.

        Returns
        -------
        bytes
            Content read from the current position.
        """
        return self.read(size)

    def readinto(self, buffer: bytearray | memoryview) -> int:
        """Read into a writable byte buffer when reading is permitted.

        Parameters
        ----------
        buffer : bytearray | memoryview
            Destination buffer receiving the content.

        Returns
        -------
        int
            Number of bytes copied into the destination.
        """
        self._requireReadable()
        return self.raw.readinto(buffer)

    def readline(self, size: int = -1) -> bytes:
        """Read one line within the selected mode's permissions.

        Parameters
        ----------
        size : int
            Maximum bytes to return, or -1 for an unrestricted line.

        Returns
        -------
        bytes
            The next line or an empty byte string at EOF.
        """
        self._requireReadable()
        return self.raw.readline(size)

    def write(self, data: bytes) -> int:
        """Write permitted bytes and force append-mode writes to EOF.

        Parameters
        ----------
        data : bytes
            Content to persist in the buffer.

        Returns
        -------
        int
            Number of bytes written.
        """
        self._requireWritable()
        if self._mode.startswith("a"):
            self.raw.seek(0, 2)
        return self.raw.write(data)

    def truncate(self, size: int | None = None) -> int:
        """Resize the buffer only when the selected mode permits writing.

        Parameters
        ----------
        size : int | None
            New length, or None to use the current position.

        Returns
        -------
        int
            New buffer length.
        """
        self._requireWritable()
        return self.raw.truncate(size)

    def seek(self, offset: int, whence: int = 0) -> int:
        """Move the position without changing append-mode write behavior.

        Parameters
        ----------
        offset : int
            Position relative to the selected anchor.
        whence : int
            Start, current position or end anchor.

        Returns
        -------
        int
            The resulting absolute position.
        """
        self._requireOpen()
        return self.raw.seek(offset, whence)

    def tell(self) -> int:
        """Return the current position of the owned buffer.

        Returns
        -------
        int
            Absolute byte position.
        """
        self._requireOpen()
        return self.raw.tell()

    def flush(self) -> None:
        """Flush the underlying buffer without exposing prohibited reads.

        Returns
        -------
        None
            No return value.
        """
        self._requireOpen()
        self.raw.flush()

    def close(self) -> None:
        """Close the wrapper and its owned buffer while preserving failures.

        Returns
        -------
        None
            No return value.
        """
        if self.closed:
            return
        try:
            super().close()
        except BaseException as error:
            _close_failed_buffer(self.raw, error)
            raise
        self.raw.close()


def _close_failed_buffer(buffer: BinaryIO, primary: BaseException) -> None:
    """Close an unpublished buffer without replacing its opening failure.

    Parameters
    ----------
    buffer : typing.BinaryIO
        Owned buffer that could not be returned to its caller.
    primary : BaseException
        Original failure raised while preparing the buffer.

    Returns
    -------
    None
        No return value.
    """
    try:
        buffer.close()
    except Exception as error:
        from orionis.failure.runtime import capture_nowait

        if not isinstance(
            primary,
            (
                asyncio.CancelledError,
                KeyboardInterrupt,
                SystemExit,
                GeneratorExit,
            ),
        ):
            capture_nowait(primary, flow="storage", phase="stream")
        capture_nowait(error, flow="storage", phase="cleanup", operation="stream.open")


def import_driver_dependency(module: str, package: str, extra: str) -> ModuleType:
    """
    Import an optional SDK module required by a storage driver.

    Cloud drivers rely on the official SDK of each platform, which is
    **not** installed with the framework. This helper performs the
    import lazily and converts an unavailable import into a descriptive
    storage exception with installation instructions.

    Parameters
    ----------
    module : str
        Dotted module path to import (e.g. ``'boto3'``).
    package : str
        PyPI package that provides the module (e.g. ``'boto3'``).
    extra : str
        Orionis extra that pulls the package (e.g. ``'s3'``), used to
        suggest ``uv add 'orionis[extra]'``.

    Returns
    -------
    types.ModuleType
        The imported module.

    Raises
    ------
    orionis.storage.exceptions.MissingStorageDependencyException
        If the module cannot be imported; retain the original import failure.
    """
    try:
        return importlib.import_module(module)
    except ImportError as exc:
        error_msg = (  # NOSONAR(S1110) - Preserve multiline grouping.
            f"The [{extra}] storage driver requires the optional package "
            f"[{package}]. Install it with: uv add 'orionis[{extra}]'."
        )
        raise MissingStorageDependencyException(error_msg) from exc


def assert_binary_mode(mode: str) -> None:
    """
    Validate a stream mode against the supported binary modes.

    Parameters
    ----------
    mode : str
        Mode requested by the caller.

    Returns
    -------
    None
        No return value.

    Raises
    ------
    orionis.storage.exceptions.UnsupportedStorageOperationException
        If *mode* is not one of ``'rb'``, ``'wb'``, ``'ab'``,
        ``'rb+'``, ``'wb+'``, or ``'ab+'``.
    """
    if mode not in _ALLOWED_MODES:
        error_msg = f"Unsupported stream mode [{mode}]."
        raise UnsupportedStorageOperationException(error_msg)


def resolve_download_target(normalized: str, destination: str | Path) -> Path:
    """
    Resolve the local target path for a download operation.

    When *destination* points to an existing directory, the file keeps
    its original name inside that directory. Missing parent
    directories are created.

    Parameters
    ----------
    normalized : str
        Canonical root-relative path of the remote file.
    destination : str | pathlib.Path
        Local target file or existing directory.

    Returns
    -------
    pathlib.Path
        Local path where the file must be written.
    """
    target = Path(destination)

    # Keep the original name when the destination is a directory.
    if target.is_dir():
        target = target / PurePosixPath(normalized).name
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def filter_files(
    keys: Iterable[str],
    base: str,
    *,
    recursive: bool,
) -> list[str]:
    """
    Select the object keys that represent files under *base*.

    Keys ending with ``/`` are treated as directory markers and are
    always excluded.

    Parameters
    ----------
    keys : collections.abc.Iterable[str]
        Object keys, relative to the disk root.
    base : str
        Canonical directory path acting as the listing root. The
        empty string denotes the disk root.
    recursive : bool
        When ``True``, include files from all nested prefixes.

    Returns
    -------
    list[str]
        Sorted file keys under *base*.
    """
    prefix = f"{base}/" if base else ""
    results: list[str] = []
    for key in keys:
        # Skip directory markers and keys outside the listing root.
        if key.endswith("/") or not key.startswith(prefix):
            continue
        remainder = key[len(prefix) :]
        if not remainder:
            continue
        if recursive or "/" not in remainder:
            results.append(key)
    results.sort()
    return results


def _directory_ancestors(key: str, base: str) -> Iterator[str]:
    """
    Yield every directory prefix implied by *key* down to *base*.

    Markers (keys ending with ``/``) name a directory directly, while
    file keys imply their parent chain.

    Parameters
    ----------
    key : str
        Object key, relative to the disk root.
    base : str
        Canonical directory path acting as the traversal floor.

    Yields
    ------
    str
        Directory paths between *key* and *base*, exclusive.
    """
    if key.endswith("/"):
        candidate = key.rstrip("/")
    else:
        candidate = key.rsplit("/", 1)[0] if "/" in key else ""

    # Walk the ancestor chain without ever crossing the listing root.
    while candidate and candidate != base:
        yield candidate
        candidate = candidate.rsplit("/", 1)[0] if "/" in candidate else ""


def derive_directories(
    keys: Iterable[str],
    base: str,
    *,
    recursive: bool,
) -> list[str]:
    """
    Derive the directory paths implied by object keys under *base*.

    Object stores have no physical directories: prefixes are inferred
    from the stored keys, and keys ending with ``/`` act as explicit
    directory markers.

    Parameters
    ----------
    keys : collections.abc.Iterable[str]
        Object keys, relative to the disk root.
    base : str
        Canonical directory path acting as the listing root. The
        empty string denotes the disk root.
    recursive : bool
        When ``True``, include all nested directories.

    Returns
    -------
    list[str]
        Sorted directory paths under *base*.
    """
    prefix = f"{base}/" if base else ""
    found: set[str] = set()
    for key in keys:
        if key.startswith(prefix):
            found.update(_directory_ancestors(key, base))

    results = [entry for entry in found if entry.startswith(prefix)]
    if not recursive:
        results = [entry for entry in results if "/" not in entry[len(prefix) :]]
    results.sort()
    return results


_LEGACY_EXPORTS = {
    "importDriverDependency": import_driver_dependency,
    "assertBinaryMode": assert_binary_mode,
    "resolveDownloadTarget": resolve_download_target,
    "filterFiles": filter_files,
    "deriveDirectories": derive_directories,
}
"""Legacy exports definitions used by ``functions``."""


def __getattr__(name: str) -> object:
    """
    Resolve and cache a legacy driver helper name.

    Parameters
    ----------
    name : str
        Attribute requested from this module.

    Returns
    -------
    object
        Existing helper function bound to the requested name.

    Raises
    ------
    AttributeError
        If the requested name is not a compatibility export.
    """
    try:
        value = _LEGACY_EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(name) from exc
    globals()[name] = value
    return value
