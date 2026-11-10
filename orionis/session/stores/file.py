"""Session store that persists each session as a JSON file on disk."""

import asyncio
import os
import re
import secrets
import threading
import time
import msgspec
import msgspec.json as _msgspec_json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from zlib import crc32
from filelock import FileLock
from orionis.session.contracts.store import ISessionStore
from orionis.session.entities.record import SessionRecord
from orionis.session.exceptions import SessionStorageException

if TYPE_CHECKING:
    from pathlib import Path
    from filelock import BaseFileLock

class _SessionPayload(msgspec.Struct, frozen=True, gc=False):
    """
    Represent the serialized payload stored for a session.

    Attributes
    ----------
    id : str
        Unique session identifier.
    expires_at : datetime.datetime
        Expiration timestamp in UTC.
    data : dict[str, typing.Any]
        Session key-value data.
    """

    id: str
    expires_at: datetime
    data: dict[str, Any]

# Codecs built once: msgspec resolves the struct layout at construction time
# instead of on every encode/decode call.
_ENCODER = _msgspec_json.Encoder()
"""
Codecs built once: msgspec resolves the struct layout at construction time instead
of on every encode/decode call.
"""
_DECODER = _msgspec_json.Decoder(_SessionPayload)
"""Decoder used by ``file``."""

# A staging file younger than this may still belong to an in-flight write.
_STALE_TEMP_SECONDS: float = 3600.0
"""A staging file younger than this may still belong to an in-flight write."""

# Windows refuses a rename while another process swaps the same destination.
_REPLACE_ATTEMPTS: int = 3
"""Windows refuses a rename while another process swaps the same destination."""
_REPLACE_BACKOFF_SECONDS: float = 0.005
"""Replace backoff seconds value used by ``file``."""
_LOCK_STRIPES: int = 64
"""Lock stripes value used by ``file``."""
_VALID_ID = re.compile(r"[A-Za-z0-9_-]{1,255}\Z")
"""Compiled pattern used to recognize valid id."""

class FileSessionStore(ISessionStore):
    """
    Session store that persists each session as a JSON file on disk.

    One JSON file per session, named ``{session_id}.json``, stored
    inside *directory*.  The directory is created on instantiation when
    it does not already exist.

    Expired sessions are evicted lazily during
    :meth:`orionis.session.stores.file.FileSessionStore.read`, keeping
    hot-path operations at *O(1)* complexity.  Bulk removal of stale
    files can be triggered explicitly via
    :meth:`orionis.session.stores.file.FileSessionStore.gc`.

    File layout
    -----------
    .. code-block:: json

        {
            "id": "...",
            "expires_at": "2026-07-10T12:00:00+00:00",
            "data": { ... }
        }

    Parameters
    ----------
    directory : pathlib.Path
        Path to the directory where session files are stored.
    """

    __slots__ = ("_directory", "_locks", "_rename_lock")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(self, directory: Path) -> None:
        """
        Initialise the store and ensure the storage directory exists.

        Parameters
        ----------
        directory : pathlib.Path
            Filesystem path to the session storage directory.

        Returns
        -------
        None
            Initialise the store and ensure the storage directory exists.
        """
        self._directory = directory
        """Filesystem path to the session storage directory."""
        self._directory.mkdir(parents=True, exist_ok=True)

        # Writes run on worker threads, so publishing two payloads for the
        # same session must not overlap inside this process.
        self._rename_lock = threading.Lock()
        """
        Writes run on worker threads, so publishing two payloads for the same
        session must not overlap inside this process.
        """
        self._locks = tuple(
            FileLock(directory / f".session-lock-{index}", timeout=10)
            for index in range(_LOCK_STRIPES)
        )
        """Locks produced by ``tuple``."""

    def _lock(self, path: Path) -> BaseFileLock:
        """
        Select a bounded, stable cross-process lock for a session file.

        Parameters
        ----------
        path : pathlib.Path
            Session file protected by the lock.

        Returns
        -------
        ``filelock.BaseFileLock``
            Platform lock serializing validation, replacement and deletion.
        """
        return self._locks[crc32(path.name.encode()) % _LOCK_STRIPES]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _path(self, session_id: str) -> Path:
        """
        Return the absolute path to the JSON file for *session_id*.

        Parameters
        ----------
        session_id : str
            Unique session identifier.

        Returns
        -------
        pathlib.Path
            Full path to ``{session_id}.json`` inside the store directory.

        Raises
        ------
        orionis.session.exceptions.SessionStorageException
            If an identifier contains path syntax or exceeds its limit.
        """
        if not isinstance(session_id, str) or _VALID_ID.fullmatch(session_id) is None:
            error_msg = "Invalid session identifier."
            raise SessionStorageException(error_msg)
        return self._directory / f"{session_id}.json"

    def _serialize(self, record: SessionRecord) -> bytes:
        """
        Encode *record* to compact JSON bytes via ``msgspec``.

        Parameters
        ----------
        record : orionis.session.entities.record.SessionRecord
            Record to serialise.

        Returns
        -------
        bytes
            UTF-8 encoded JSON payload.
        """
        payload = _SessionPayload(
            id=record.id,
            expires_at=record.expires_at,
            data=record.data,
        )
        return _ENCODER.encode(payload)

    def _deserialize(self, raw: bytes) -> SessionRecord | None:
        """
        Decode JSON bytes into a session record.

        Return a :class:`orionis.session.entities.record.SessionRecord` instance.
        Type validation is delegated entirely to ``msgspec``; any structural
        mismatch or missing field is treated as corruption.

        Parameters
        ----------
        raw : bytes
            Raw JSON bytes previously written by
            :meth:`orionis.session.stores.file.FileSessionStore._serialize`.

        Returns
        -------
        orionis.session.entities.record.SessionRecord | None
            Deserialised record, or ``None`` on any decode error.
        """
        try:
            payload = _DECODER.decode(raw)
            return SessionRecord(
                id=payload.id,
                data=payload.data,
                expires_at=payload.expires_at,
            )
        except (ValueError, msgspec.DecodeError) as error:
            from orionis.failure.runtime import capture_nowait  # noqa: PLC0415
            capture_nowait(
                error,
                flow="session",
                phase="decode",
                operation="file.read",
            )
            return None

    def _readFile(self, path: Path) -> bytes | None:
        """
        Read *path* as raw bytes, returning ``None`` if absent.

        Parameters
        ----------
        path : pathlib.Path
            File to read.

        Returns
        -------
        bytes | None
            File contents, or ``None`` when the file does not exist.
        """
        try:
            return path.read_bytes()
        except FileNotFoundError:
            return None

    @staticmethod
    def _tempPath(path: Path) -> Path:
        """
        Build a unique staging path for an atomic write.

        Parameters
        ----------
        path : pathlib.Path
            Final destination file.

        Returns
        -------
        pathlib.Path
            Sibling path carrying a random infix, so concurrent writers of the
            same session never share a staging file, and still ending in
            ``.tmp`` so the sweep keeps telling both apart.
        """
        return path.with_name(f"{path.name}.{secrets.token_hex(8)}.tmp")

    def _writeFile(self, path: Path, content: bytes) -> None:
        """
        Atomically write *content* to *path*.

        Writes to a unique ``.tmp`` sibling first, then renames over the
        destination to prevent partial reads from concurrent processes.
        A failed write removes its own staging file before propagating.

        Parameters
        ----------
        path : pathlib.Path
            Destination file path.
        content : bytes
            Serialised session payload.

        Returns
        -------
        None
            Atomically write *content* to *path*.

        Raises
        ------
        OSError
            If the payload cannot be staged or renamed into place.
        """
        tmp = self._tempPath(path)
        try:
            tmp.write_bytes(content)
            self._replace(tmp, path)
        except OSError:
            try:
                tmp.unlink(missing_ok=True)
            except OSError as cleanup_error:
                from orionis.failure.runtime import capture_nowait  # noqa: PLC0415
                capture_nowait(
                    cleanup_error,
                    flow="session",
                    phase="cleanup",
                    operation="file.write",
                )
            raise

    def _replace(self, tmp: Path, path: Path) -> None:
        """
        Publish *tmp* as *path*, retrying a transient sharing violation.

        The rename is serialised per store instance, and retried when the
        operating system refuses it because another process is swapping the
        same destination.  POSIX never reaches the retry branch.

        Parameters
        ----------
        tmp : pathlib.Path
            Staging file holding the serialised payload.
        path : pathlib.Path
            Destination session file.

        Returns
        -------
        None
            Publish *tmp* as *path*, retrying a transient sharing violation.

        Raises
        ------
        OSError
            If the rename keeps failing after the last attempt.
        """
        last = _REPLACE_ATTEMPTS - 1
        for attempt in range(_REPLACE_ATTEMPTS):
            try:
                with self._rename_lock:
                    tmp.replace(path)
            except PermissionError as error:
                if attempt == last:
                    raise
                from orionis.failure.runtime import capture_nowait  # noqa: PLC0415
                capture_nowait(
                    error,
                    flow="session",
                    phase="retry",
                    operation="file.replace",
                    expected=True,
                    metadata={"attempt": attempt + 1},
                )
                time.sleep(_REPLACE_BACKOFF_SECONDS)
            else:
                return

    def _deleteFile(self, path: Path) -> bool:
        """
        Unlink *path*, silently ignoring a missing-file error.

        Parameters
        ----------
        path : pathlib.Path
            Session file to remove.

        Returns
        -------
        bool
            True when this call removed the session file.
        """
        with self._lock(path):
            try:
                path.unlink()
            except FileNotFoundError:
                return False
            return True

    def _readRecord(self, path: Path) -> SessionRecord | None:
        """
        Load, decode and validate the record stored at *path*.

        Runs entirely on a worker thread: file I/O, JSON decoding and the
        eviction of an expired or corrupt file happen in a single hop.

        Parameters
        ----------
        path : pathlib.Path
            Session file to load.

        Returns
        -------
        orionis.session.entities.record.SessionRecord | None
            The live record, or ``None`` when absent, expired or corrupt.
        """
        with self._lock(path):
            raw = self._readFile(path)
            if raw is None:
                return None

            record = self._deserialize(raw)
            if (
                record is None
                or record.id != path.stem
                or record.expires_at.tzinfo is None
                or record.expires_at <= datetime.now(UTC)
            ):
                self._deleteFile(path)
                return None
            return record

    def _writeRecord(self, path: Path, record: SessionRecord) -> None:
        """
        Serialise *record* and store it atomically at *path*.

        Parameters
        ----------
        path : pathlib.Path
            Destination session file.
        record : orionis.session.entities.record.SessionRecord
            The record to persist.

        Returns
        -------
        None
            Serialise *record* and store it atomically at *path*.
        """
        with self._lock(path):
            self._writeFile(path, self._serialize(record))

    def _updateRecord(self, path: Path, record: SessionRecord) -> bool:
        """
        Replace an existing live session under its cross-process lock.

        Parameters
        ----------
        path : pathlib.Path
            Existing session file.
        record : orionis.session.entities.record.SessionRecord
            Replacement record.

        Returns
        -------
        bool
            False when another worker deleted or expired the record.
        """
        with self._lock(path):
            if self._readRecord(path) is None:
                return False
            self._writeRecord(path, record)
            return True

    def _gcSweep(self) -> None:
        """
        Scan the store directory and remove stale or corrupt files.

        Uses ``os.scandir`` for reduced object allocation and
        filesystem cache reuse.  A session file is removed when it is
        expired, contains invalid JSON, is structurally incomplete, or
        cannot be read due to an I/O error.  Staging files left behind by
        an interrupted write are reclaimed once they are old enough that
        no writer can still be filling them.

        Returns
        -------
        None
            Scan the store directory and remove stale or corrupt files.
        """
        stale_before = time.time() - _STALE_TEMP_SECONDS
        with os.scandir(self._directory) as it:
            for entry in it:
                if not entry.is_file():
                    continue

                try:
                    if entry.name.endswith(".tmp"):
                        if entry.stat().st_mtime <= stale_before:
                            os.unlink(entry.path)  # noqa: PTH108
                    elif entry.name.endswith(".json"):
                        self._readRecord(self._directory / entry.name)
                except FileNotFoundError:
                    pass
                except OSError as error:
                    from orionis.failure.runtime import capture_nowait  # noqa: PLC0415
                    capture_nowait(
                        error,
                        flow="session",
                        phase="cleanup",
                        operation="file.gc",
                    )

    # ------------------------------------------------------------------
    # ISessionStore interface
    # ------------------------------------------------------------------

    async def read(self, session_id: str) -> SessionRecord | None:
        """
        Load and return the live record for *session_id*, or ``None``.

        Expired or corrupt records are evicted lazily: the file is
        deleted and ``None`` is returned without triggering a GC cycle.

        Parameters
        ----------
        session_id : str
            Unique session identifier to look up.

        Returns
        -------
        orionis.session.entities.record.SessionRecord | None
            The live record, or ``None`` when absent, expired, or corrupt.
        """
        return await asyncio.to_thread(self._readRecord, self._path(session_id))

    async def write(self, record: SessionRecord) -> None:
        """
        Serialise and persist *record* to disk atomically.

        Parameters
        ----------
        record : orionis.session.entities.record.SessionRecord
            The record to store.

        Returns
        -------
        None
            Serialise and persist *record* to disk atomically.
        """
        await asyncio.to_thread(self._writeRecord, self._path(record.id), record)

    async def update(self, record: SessionRecord) -> bool:
        """
        Update only a live session without recreating a deleted file.

        Parameters
        ----------
        record : orionis.session.entities.record.SessionRecord
            Replacement record.

        Returns
        -------
        bool
            Whether the session still existed and was updated.
        """
        return await asyncio.to_thread(
            self._updateRecord, self._path(record.id), record,
        )

    async def delete(self, session_id: str) -> bool:
        """
        Remove the session file for *session_id* (no-op when absent).

        Parameters
        ----------
        session_id : str
            Unique session identifier to remove.

        Returns
        -------
        bool
            True only when a session file was deleted.
        """
        path = self._path(session_id)
        return await asyncio.to_thread(self._deleteFile, path)

    async def gc(self) -> None:
        """
        Remove all expired, corrupt, or incomplete session files.

        The directory scan runs on a thread-pool worker so it never
        blocks the event loop.  This method must be called explicitly;
        it is never triggered automatically by
        :meth:`orionis.session.stores.file.FileSessionStore.read`,
        :meth:`orionis.session.stores.file.FileSessionStore.write`, or
        :meth:`orionis.session.stores.file.FileSessionStore.delete`.

        Returns
        -------
        None
            Remove all expired, corrupt, or incomplete session files.
        """
        await asyncio.to_thread(self._gcSweep)
