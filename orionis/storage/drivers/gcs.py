from __future__ import annotations
import asyncio
import base64
import hashlib
import mimetypes
import tempfile
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from urllib.parse import quote
from orionis.storage.contracts.driver import IStorageDriver
from orionis.storage.entities.file_info import FileInfo
from orionis.storage.enums.visibility import Visibility
from orionis.storage.drivers.functions import (
    assertBinaryMode,
    deriveDirectories,
    filterFiles,
    importDriverDependency,
    resolveDownloadTarget,
)
from orionis.storage.exceptions import (
    StorageFileNotFoundException,
    UnsupportedStorageOperationException,
)
from orionis.storage.paths import normalizeFilePath, normalizePath
from orionis.storage.stream import AsyncStream

if TYPE_CHECKING:
    from collections.abc import AsyncIterable, AsyncIterator
    from pathlib import Path
    from typing import BinaryIO

# Default chunk size for streaming operations (64 KiB).
_CHUNK_SIZE: int = 64 * 1024

# In-memory bytes before spooled buffers spill to disk (8 MiB).
_SPOOL_THRESHOLD: int = 8 * 1024 * 1024

# Content type applied when the MIME type cannot be guessed.
_DEFAULT_CONTENT_TYPE: str = "application/octet-stream"

# Predefined ACLs applied per visibility level.
_ACL_MAP: dict[str, str] = {
    Visibility.PUBLIC.value: "publicRead",
    Visibility.PRIVATE.value: "private",
}

class GoogleStorageDriver(IStorageDriver):
    """
    Storage driver backed by Google Cloud Storage.

    Uses the official Google Cloud client library
    (``google-cloud-storage``), which is an **optional dependency**:
    it is not installed with the framework. Install it before using
    this driver::

        pip install google-cloud-storage
        # or
        pip install orionis[gcs]

    The SDK is imported lazily on first operation, and every blocking
    call runs on a worker thread via :func:`asyncio.to_thread`.
    Directories are virtual: prefixes are inferred from object names
    and explicit directories are stored as zero-byte ``path/``
    markers. Authentication uses the configured service-account key
    file or Application Default Credentials.
    """

    # ruff: noqa: ANN401

    __slots__ = (
        "_base_url",
        "_bucket",
        "_bucket_name",
        "_cloud_error",
        "_key_file",
        "_not_found",
        "_project",
    )

    def __init__(self, config: object) -> None:
        """
        Initialize the driver from a GCS disk configuration entity.

        No SDK import or network activity happens here; the client is
        bootstrapped lazily on first use.

        Parameters
        ----------
        config : object
            Disk configuration exposing ``project_id``, ``key_file``,
            ``bucket``, and ``url``.

        Returns
        -------
        None
        """
        self._project: str = str(getattr(config, "project_id", "") or "")
        self._key_file: str | None = getattr(config, "key_file", None) or None
        self._bucket_name: str = str(getattr(config, "bucket", "") or "")

        base_url = getattr(config, "url", None)
        self._base_url: str | None = base_url.rstrip("/") if base_url else None

        self._bucket: Any = None
        self._not_found: type[Exception] = Exception
        self._cloud_error: type[Exception] = Exception

    # ── SDK bootstrap and low-level helpers ──────────────────────────────────

    def __bucket(self) -> Any:
        """
        Return the bucket handle, bootstrapping the client on first use.

        Returns
        -------
        Any
            Configured ``Bucket`` instance.

        Raises
        ------
        MissingStorageDependencyException
            If ``google-cloud-storage`` is not installed.
        """
        if self._bucket is not None:
            return self._bucket

        # Import the official SDK lazily; it is an optional dependency.
        storage = importDriverDependency(
            "google.cloud.storage", "google-cloud-storage", "gcs",
        )
        errors = importDriverDependency(
            "google.cloud.exceptions", "google-cloud-storage", "gcs",
        )

        # Prefer the service-account key file; fall back to ADC.
        client = (
            storage.Client.from_service_account_json(self._key_file)
            if self._key_file
            else storage.Client(project=self._project or None)
        )

        self._not_found = errors.NotFound
        self._cloud_error = errors.GoogleCloudError
        self._bucket = client.bucket(self._bucket_name)
        return self._bucket

    def __blob(self, normalized: str) -> Any:
        """
        Return a lightweight blob handle for *normalized*.

        Parameters
        ----------
        normalized : str
            Canonical root-relative file path.

        Returns
        -------
        Any
            ``Blob`` handle bound to the bucket.
        """
        return self.__bucket().blob(normalized)

    def __missing(self, normalized: str) -> StorageFileNotFoundException:
        """
        Build the framework exception for a missing object.

        Parameters
        ----------
        normalized : str
            Canonical root-relative file path.

        Returns
        -------
        StorageFileNotFoundException
            Exception instance ready to be raised.
        """
        error_msg = f"File does not exist at path [{normalized}]."
        return StorageFileNotFoundException(error_msg)

    def __blobOrFail(self, normalized: str) -> Any:
        """
        Fetch a blob with loaded metadata or raise when absent.

        Parameters
        ----------
        normalized : str
            Canonical root-relative file path.

        Returns
        -------
        Any
            ``Blob`` with populated properties.

        Raises
        ------
        StorageFileNotFoundException
            If the object does not exist.
        """
        blob = self.__bucket().get_blob(normalized)
        if blob is None:
            raise self.__missing(normalized)
        return blob

    def __listKeysSync(self, prefix: str) -> list[str]:
        """
        List every object name under *prefix*.

        Parameters
        ----------
        prefix : str
            Name prefix to filter by; empty string lists the bucket.

        Returns
        -------
        list[str]
            All matching object names, including directory markers.
        """
        bucket = self.__bucket()
        return [
            blob.name
            for blob in bucket.list_blobs(prefix=prefix or None)
        ]

    def __aclFor(self, visibility: str) -> str:
        """
        Map a visibility level onto a GCS predefined ACL.

        Parameters
        ----------
        visibility : str
            Visibility level (``'public'`` or ``'private'``).

        Returns
        -------
        str
            Predefined ACL name.

        Raises
        ------
        UnsupportedStorageOperationException
            If *visibility* is not a supported level.
        """
        acl = _ACL_MAP.get(str(visibility))
        if acl is None:
            error_msg = f"Unsupported visibility level [{visibility}]."
            raise UnsupportedStorageOperationException(error_msg)
        return acl

    def __urlFor(self, normalized: str) -> str:
        """
        Compose the public URL of an object without SDK involvement.

        Parameters
        ----------
        normalized : str
            Canonical root-relative file path.

        Returns
        -------
        str
            URL derived from the configured base URL or the canonical
            ``storage.googleapis.com`` address.
        """
        encoded = quote(normalized, safe="/")
        if self._base_url:
            return f"{self._base_url}/{encoded}"
        return (
            f"https://storage.googleapis.com/{self._bucket_name}/{encoded}"
        )

    def __isPublicSync(self, blob: Any) -> bool:
        """
        Check whether a blob grants read access to anonymous users.

        Parameters
        ----------
        blob : Any
            ``Blob`` with loaded metadata.

        Returns
        -------
        bool
            ``True`` when ``allUsers`` holds a reader or owner role.
            ``False`` when ACLs cannot be inspected (e.g. uniform
            bucket-level access).
        """
        try:
            entries = list(blob.acl)
        except self._cloud_error:
            return False
        return any(
            entry.get("entity") == "allUsers"
            and entry.get("role") in ("READER", "OWNER")
            for entry in entries
        )

    async def __spool(self, stream: AsyncIterable[bytes]) -> BinaryIO:
        """
        Buffer an async byte stream into a spooled temporary file.

        Parameters
        ----------
        stream : AsyncIterable[bytes]
            Asynchronous byte-chunk producer.

        Returns
        -------
        BinaryIO
            Rewound buffer holding the full payload.
        """
        buffer = await asyncio.to_thread(
            tempfile.SpooledTemporaryFile, max_size=_SPOOL_THRESHOLD,
        )
        try:
            async for chunk in stream:
                await asyncio.to_thread(buffer.write, chunk)
        except BaseException:
            await asyncio.to_thread(buffer.close)
            raise
        await asyncio.to_thread(buffer.seek, 0)
        return buffer

    # ── Read operations ──────────────────────────────────────────────────────

    async def read(self, path: str) -> bytes:
        """
        Read the full contents of the object at *path*.

        Parameters
        ----------
        path : str
            Root-relative file path.

        Returns
        -------
        bytes
            Complete object contents.

        Raises
        ------
        StorageFileNotFoundException
            If the object does not exist.
        """
        normalized = normalizeFilePath(path)

        def _read() -> bytes:
            blob = self.__blob(normalized)
            try:
                return blob.download_as_bytes()
            except self._not_found as exc:
                raise self.__missing(normalized) from exc

        return await asyncio.to_thread(_read)

    async def readStream(
        self,
        path: str,
        chunk_size: int = _CHUNK_SIZE,
    ) -> AsyncIterator[bytes]:
        """
        Stream the contents of the object at *path* in chunks.

        Parameters
        ----------
        path : str
            Root-relative file path.
        chunk_size : int
            Maximum number of bytes per yielded chunk.

        Yields
        ------
        bytes
            Consecutive chunks of the object contents.

        Raises
        ------
        StorageFileNotFoundException
            If the object does not exist.
        """
        normalized = normalizeFilePath(path)

        def _open() -> Any:
            blob = self.__blobOrFail(normalized)
            return blob.open("rb")

        handle = await asyncio.to_thread(_open)
        try:
            while True:
                chunk = await asyncio.to_thread(handle.read, chunk_size)
                if not chunk:
                    break
                yield chunk
        finally:
            await asyncio.to_thread(handle.close)

    async def exists(self, path: str) -> bool:
        """
        Check whether an object exists at *path*.

        Parameters
        ----------
        path : str
            Root-relative file path.

        Returns
        -------
        bool
            ``True`` if an object exists at the given name.
        """
        normalized = normalizeFilePath(path)
        return await asyncio.to_thread(
            lambda: bool(self.__blob(normalized).exists()),
        )

    # ── Write operations ─────────────────────────────────────────────────────

    async def write(
        self,
        path: str,
        contents: bytes | str,
        visibility: str | None = None,
    ) -> None:
        """
        Write *contents* to *path*, replacing any existing object.

        Parameters
        ----------
        path : str
            Root-relative file path.
        contents : bytes | str
            Data to persist. Strings are encoded as UTF-8.
        visibility : str | None
            Visibility applied through a predefined ACL, or ``None``
            for the bucket default. Ignored by GCS when the bucket
            enforces uniform bucket-level access.

        Returns
        -------
        None
        """
        normalized = normalizeFilePath(path)
        data = (
            contents.encode("utf-8")
            if isinstance(contents, str)
            else bytes(contents)
        )
        acl = self.__aclFor(visibility) if visibility is not None else None

        def _write() -> None:
            blob = self.__blob(normalized)
            blob.upload_from_string(
                data,
                content_type=(
                    mimetypes.guess_type(normalized)[0]
                    or _DEFAULT_CONTENT_TYPE
                ),
                predefined_acl=acl,
            )

        await asyncio.to_thread(_write)

    async def writeStream(
        self,
        path: str,
        stream: AsyncIterable[bytes],
        visibility: str | None = None,
    ) -> None:
        """
        Write the chunks produced by *stream* to *path*.

        The payload is buffered into a spooled temporary file
        (spilling to disk past 8 MiB) and uploaded with the SDK's
        resumable transfer.

        Parameters
        ----------
        path : str
            Root-relative file path.
        stream : AsyncIterable[bytes]
            Asynchronous byte-chunk producer.
        visibility : str | None
            Visibility applied through a predefined ACL, or ``None``
            for the bucket default.

        Returns
        -------
        None
        """
        normalized = normalizeFilePath(path)
        acl = self.__aclFor(visibility) if visibility is not None else None
        buffer = await self.__spool(stream)

        def _upload() -> None:
            blob = self.__blob(normalized)
            blob.upload_from_file(
                buffer,
                content_type=(
                    mimetypes.guess_type(normalized)[0]
                    or _DEFAULT_CONTENT_TYPE
                ),
                predefined_acl=acl,
            )

        try:
            await asyncio.to_thread(_upload)
        finally:
            await asyncio.to_thread(buffer.close)

    async def delete(self, path: str) -> bool:
        """
        Delete the object at *path*.

        Parameters
        ----------
        path : str
            Root-relative file path.

        Returns
        -------
        bool
            ``True`` if the object existed and was removed.
        """
        normalized = normalizeFilePath(path)

        def _delete() -> bool:
            blob = self.__blob(normalized)
            try:
                blob.delete()
            except self._not_found:
                return False
            return True

        return await asyncio.to_thread(_delete)

    async def copy(self, source: str, target: str) -> None:
        """
        Copy the object at *source* to *target* server-side.

        Parameters
        ----------
        source : str
            Root-relative path of the existing object.
        target : str
            Root-relative destination path.

        Returns
        -------
        None

        Raises
        ------
        StorageFileNotFoundException
            If the source object does not exist.
        """
        origin = normalizeFilePath(source)
        destination = normalizeFilePath(target)

        def _copy() -> None:
            bucket = self.__bucket()
            blob = self.__blobOrFail(origin)
            bucket.copy_blob(blob, bucket, destination)

        await asyncio.to_thread(_copy)

    async def move(self, source: str, target: str) -> None:
        """
        Move the object at *source* to *target*.

        Implemented as a server-side copy followed by a delete of the
        source object.

        Parameters
        ----------
        source : str
            Root-relative path of the existing object.
        target : str
            Root-relative destination path.

        Returns
        -------
        None

        Raises
        ------
        StorageFileNotFoundException
            If the source object does not exist.
        """
        await self.copy(source, target)
        normalized = normalizeFilePath(source)

        def _cleanup() -> None:
            blob = self.__blob(normalized)
            with suppress(self._not_found):
                blob.delete()

        await asyncio.to_thread(_cleanup)

    # ── Metadata operations ──────────────────────────────────────────────────

    async def size(self, path: str) -> int:
        """
        Return the size in bytes of the object at *path*.

        Parameters
        ----------
        path : str
            Root-relative file path.

        Returns
        -------
        int
            Object size in bytes.

        Raises
        ------
        StorageFileNotFoundException
            If the object does not exist.
        """
        normalized = normalizeFilePath(path)
        blob = await asyncio.to_thread(self.__blobOrFail, normalized)
        return int(blob.size or 0)

    async def mimeType(self, path: str) -> str | None:
        """
        Return the MIME type of the object at *path*.

        Prefers the content type stored in GCS and falls back to a
        guess based on the file extension.

        Parameters
        ----------
        path : str
            Root-relative file path.

        Returns
        -------
        str | None
            MIME type, or ``None`` when it cannot be determined.

        Raises
        ------
        StorageFileNotFoundException
            If the object does not exist.
        """
        normalized = normalizeFilePath(path)
        blob = await asyncio.to_thread(self.__blobOrFail, normalized)
        return blob.content_type or mimetypes.guess_type(normalized)[0]

    async def lastModified(self, path: str) -> datetime:
        """
        Return the last-modification timestamp of the object at *path*.

        Parameters
        ----------
        path : str
            Root-relative file path.

        Returns
        -------
        datetime
            Timezone-aware modification timestamp.

        Raises
        ------
        StorageFileNotFoundException
            If the object does not exist.
        """
        normalized = normalizeFilePath(path)
        blob = await asyncio.to_thread(self.__blobOrFail, normalized)
        return blob.updated or datetime.now(tz=UTC)

    async def visibility(self, path: str) -> str:
        """
        Return the visibility of the object at *path*.

        Parameters
        ----------
        path : str
            Root-relative file path.

        Returns
        -------
        str
            ``'public'`` when anonymous users can read the object,
            otherwise ``'private'``.

        Raises
        ------
        StorageFileNotFoundException
            If the object does not exist.
        """
        normalized = normalizeFilePath(path)

        def _visibility() -> str:
            blob = self.__blobOrFail(normalized)
            return (
                Visibility.PUBLIC.value
                if self.__isPublicSync(blob)
                else Visibility.PRIVATE.value
            )

        return await asyncio.to_thread(_visibility)

    async def setVisibility(self, path: str, visibility: str) -> None:
        """
        Change the visibility of the object at *path*.

        Not available on buckets with uniform bucket-level access,
        where the SDK raises the corresponding API error.

        Parameters
        ----------
        path : str
            Root-relative file path.
        visibility : str
            Target visibility (``'public'`` or ``'private'``).

        Returns
        -------
        None

        Raises
        ------
        StorageFileNotFoundException
            If the object does not exist.
        UnsupportedStorageOperationException
            If *visibility* is not a supported level.
        """
        normalized = normalizeFilePath(path)

        # Validate the level before any network activity.
        self.__aclFor(visibility)
        make_public = str(visibility) == Visibility.PUBLIC.value

        def _apply() -> None:
            blob = self.__blobOrFail(normalized)
            if make_public:
                blob.make_public()
            else:
                blob.make_private()

        await asyncio.to_thread(_apply)

    async def hash(self, path: str, algorithm: str = "sha256") -> str:
        """
        Compute the content hash of the object at *path*.

        The object is streamed in chunks, so large files never load
        fully into memory.

        Parameters
        ----------
        path : str
            Root-relative file path.
        algorithm : str
            Any algorithm name accepted by :func:`hashlib.new`.

        Returns
        -------
        str
            Hexadecimal digest of the object contents.

        Raises
        ------
        StorageFileNotFoundException
            If the object does not exist.
        UnsupportedStorageOperationException
            If *algorithm* is not available.
        """
        normalized = normalizeFilePath(path)

        def _hash() -> str:
            try:
                hasher = hashlib.new(algorithm, usedforsecurity=False)
            except ValueError as exc:
                error_msg = f"Unsupported hash algorithm [{algorithm}]."
                raise UnsupportedStorageOperationException(error_msg) from exc

            blob = self.__blobOrFail(normalized)
            with blob.open("rb") as handle:
                while chunk := handle.read(_CHUNK_SIZE):
                    hasher.update(chunk)
            return hasher.hexdigest()

        return await asyncio.to_thread(_hash)

    async def info(self, path: str) -> FileInfo:
        """
        Collect a metadata snapshot for the object at *path*.

        The snapshot is built from object metadata only; ``checksum``
        holds the MD5 hash stored by GCS when available.

        Parameters
        ----------
        path : str
            Root-relative file path.

        Returns
        -------
        FileInfo
            Immutable entity with size, MIME type, timestamps, ETag,
            visibility, and URL.

        Raises
        ------
        StorageFileNotFoundException
            If the object does not exist.
        """
        normalized = normalizeFilePath(path)

        def _info() -> FileInfo:
            blob = self.__blobOrFail(normalized)
            checksum = (
                base64.b64decode(blob.md5_hash).hex()
                if blob.md5_hash
                else None
            )
            return FileInfo(
                path=normalized,
                size=int(blob.size or 0),
                lastModified=blob.updated or datetime.now(tz=UTC),
                visibility=(
                    Visibility.PUBLIC.value
                    if self.__isPublicSync(blob)
                    else Visibility.PRIVATE.value
                ),
                mimeType=(
                    blob.content_type
                    or mimetypes.guess_type(normalized)[0]
                ),
                createdAt=blob.time_created,
                etag=blob.etag or None,
                checksum=checksum,
                url=self.__urlFor(normalized),
            )

        return await asyncio.to_thread(_info)

    # ── Directory operations ─────────────────────────────────────────────────

    async def createDirectory(self, path: str) -> None:
        """
        Create a zero-byte directory marker at *path*.

        Parameters
        ----------
        path : str
            Root-relative directory path.

        Returns
        -------
        None
        """
        normalized = normalizePath(path)
        if not normalized:
            return

        await asyncio.to_thread(
            lambda: self.__blob(f"{normalized}/").upload_from_string(b""),
        )

    async def deleteDirectory(self, path: str) -> bool:
        """
        Recursively delete every object under *path*.

        Parameters
        ----------
        path : str
            Root-relative directory path. The empty string clears the
            whole bucket prefix space.

        Returns
        -------
        bool
            ``True`` if at least one object was removed.
        """
        normalized = normalizePath(path)
        prefix = f"{normalized}/" if normalized else ""

        def _purge() -> bool:
            bucket = self.__bucket()
            blobs = list(bucket.list_blobs(prefix=prefix or None))
            for blob in blobs:
                blob.delete()
            return bool(blobs)

        return await asyncio.to_thread(_purge)

    async def directoryExists(self, path: str) -> bool:
        """
        Check whether any object exists under *path*.

        Parameters
        ----------
        path : str
            Root-relative directory path. The empty string denotes
            the disk root.

        Returns
        -------
        bool
            ``True`` if the prefix contains at least one object.
        """
        normalized = normalizePath(path)
        if not normalized:
            return True

        def _exists() -> bool:
            bucket = self.__bucket()
            iterator = bucket.list_blobs(
                prefix=f"{normalized}/", max_results=1,
            )
            return next(iter(iterator), None) is not None

        return await asyncio.to_thread(_exists)

    async def files(
        self,
        path: str = "",
        *,
        recursive: bool = False,
    ) -> list[str]:
        """
        List the object names that represent files under *path*.

        Parameters
        ----------
        path : str
            Root-relative directory path. Empty string for the root.
        recursive : bool
            When ``True``, include files from all nested prefixes.

        Returns
        -------
        list[str]
            Sorted root-relative file paths.
        """
        normalized = normalizePath(path)
        prefix = f"{normalized}/" if normalized else ""
        keys = await asyncio.to_thread(self.__listKeysSync, prefix)
        return filterFiles(keys, normalized, recursive=recursive)

    async def directories(
        self,
        path: str = "",
        *,
        recursive: bool = False,
    ) -> list[str]:
        """
        List the directory prefixes contained under *path*.

        Parameters
        ----------
        path : str
            Root-relative directory path. Empty string for the root.
        recursive : bool
            When ``True``, include all nested prefixes.

        Returns
        -------
        list[str]
            Sorted root-relative directory paths.
        """
        normalized = normalizePath(path)
        prefix = f"{normalized}/" if normalized else ""
        keys = await asyncio.to_thread(self.__listKeysSync, prefix)
        return deriveDirectories(keys, normalized, recursive=recursive)

    # ── URLs and transfers ───────────────────────────────────────────────────

    async def url(self, path: str) -> str:
        """
        Build the public URL for the object at *path*.

        Parameters
        ----------
        path : str
            Root-relative file path.

        Returns
        -------
        str
            URL derived from the configured base URL or the canonical
            ``storage.googleapis.com`` address.
        """
        return self.__urlFor(normalizeFilePath(path))

    async def temporaryUrl(self, path: str, expires_in: int) -> str:
        """
        Build a V4 signed URL for the object at *path*.

        Requires credentials with a private key (a service-account
        key file); plain Application Default Credentials without a
        key cannot sign URLs.

        Parameters
        ----------
        path : str
            Root-relative file path.
        expires_in : int
            Lifetime of the URL in seconds.

        Returns
        -------
        str
            Signed GET URL valid for *expires_in* seconds.

        Raises
        ------
        MissingStorageDependencyException
            If ``google-cloud-storage`` is not installed.
        """
        normalized = normalizeFilePath(path)

        def _sign() -> str:
            blob = self.__blob(normalized)
            return blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=expires_in),
                method="GET",
            )

        return await asyncio.to_thread(_sign)

    async def download(self, path: str, destination: str | Path) -> Path:
        """
        Download the object at *path* to the local filesystem.

        Parameters
        ----------
        path : str
            Root-relative file path on the disk.
        destination : str | Path
            Local target. When it points to an existing directory the
            file keeps its original name inside that directory.

        Returns
        -------
        Path
            Absolute local path of the downloaded file.

        Raises
        ------
        StorageFileNotFoundException
            If the object does not exist.
        """
        normalized = normalizeFilePath(path)

        def _download() -> Path:
            target = resolveDownloadTarget(normalized, destination)
            blob = self.__blob(normalized)
            try:
                blob.download_to_filename(str(target))
            except self._not_found as exc:
                raise self.__missing(normalized) from exc
            return target.resolve()

        return await asyncio.to_thread(_download)

    def open(self, path: str, mode: str = "rb") -> AsyncStream:
        """
        Open an asynchronous binary stream for the object at *path*.

        Read-oriented modes download the object into a spooled
        temporary buffer; writable modes upload the buffered content
        back to GCS when the stream is closed.

        Parameters
        ----------
        path : str
            Root-relative file path.
        mode : str
            Binary mode: ``'rb'``, ``'wb'``, ``'ab'``, ``'rb+'``,
            ``'wb+'``, or ``'ab+'``.

        Returns
        -------
        AsyncStream
            Lazily opened stream; use it as an async context manager.

        Raises
        ------
        UnsupportedStorageOperationException
            If *mode* is not a supported binary mode.
        """
        normalized = normalizeFilePath(path)
        assertBinaryMode(mode)

        def opener() -> BinaryIO:
            buffer = tempfile.SpooledTemporaryFile(  # noqa: SIM115
                max_size=_SPOOL_THRESHOLD,
            )

            # Seed the buffer for modes that read existing content.
            if mode in ("rb", "rb+", "ab", "ab+"):
                blob = self.__blob(normalized)
                try:
                    blob.download_to_file(buffer)
                except self._not_found as exc:
                    if mode in ("rb", "rb+"):
                        buffer.close()
                        raise self.__missing(normalized) from exc
                if mode.startswith("a"):
                    buffer.seek(0, 2)
                else:
                    buffer.seek(0)
            return buffer

        def flush(handle: BinaryIO) -> None:
            # Persist the buffered content back to GCS on close.
            handle.seek(0)
            self.__blob(normalized).upload_from_file(
                handle,
                content_type=(
                    mimetypes.guess_type(normalized)[0]
                    or _DEFAULT_CONTENT_TYPE
                ),
            )

        on_close = None if mode == "rb" else flush
        return AsyncStream(opener, on_close)
