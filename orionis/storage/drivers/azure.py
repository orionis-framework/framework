from __future__ import annotations
import asyncio
import hashlib
import mimetypes
import tempfile
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

class AzureStorageDriver(IStorageDriver):
    """
    Storage driver backed by Azure Blob Storage.

    Uses the official Azure SDK for Python (``azure-storage-blob``),
    which is an **optional dependency**: it is not installed with the
    framework. Install it before using this driver::

        pip install azure-storage-blob
        # or
        pip install orionis[azure]

    The SDK is imported lazily on first operation, and every blocking
    call runs on a worker thread via :func:`asyncio.to_thread`.
    Directories are virtual: prefixes are inferred from blob names and
    explicit directories are stored as zero-byte ``path/`` markers.
    Azure has no per-blob visibility: :meth:`visibility` reflects the
    container access level and :meth:`setVisibility` is unsupported.
    """

    # ruff: noqa: ANN401

    __slots__ = (
        "_account_key",
        "_account_name",
        "_base_url",
        "_connection_string",
        "_container",
        "_container_name",
        "_http_error",
        "_not_found",
        "_sdk",
    )

    def __init__(self, config: object) -> None:
        """
        Initialize the driver from an Azure disk configuration entity.

        No SDK import or network activity happens here; the client is
        bootstrapped lazily on first use. When a connection string is
        provided, the account name and key are parsed from it so URLs
        and SAS tokens can be produced.

        Parameters
        ----------
        config : object
            Disk configuration exposing ``connection_string``,
            ``account_name``, ``account_key``, ``container``, and
            ``url``.

        Returns
        -------
        None
        """
        self._connection_string: str = str(
            getattr(config, "connection_string", "") or "",
        )
        self._account_name: str = str(getattr(config, "account_name", "") or "")
        self._account_key: str = str(getattr(config, "account_key", "") or "")
        self._container_name: str = str(getattr(config, "container", "") or "")

        base_url = getattr(config, "url", None)
        self._base_url: str | None = base_url.rstrip("/") if base_url else None

        self._container: Any = None
        self._sdk: Any = None
        self._not_found: type[Exception] = Exception
        self._http_error: type[Exception] = Exception

        # Derive account credentials from the connection string when
        # they were not provided explicitly.
        if self._connection_string:
            parts = {
                key: value
                for key, separator, value in (
                    segment.partition("=")
                    for segment in self._connection_string.split(";")
                )
                if separator
            }
            self._account_name = self._account_name or parts.get(
                "AccountName", "",
            )
            self._account_key = self._account_key or parts.get(
                "AccountKey", "",
            )

    # ── SDK bootstrap and low-level helpers ──────────────────────────────────

    def __containerClient(self) -> Any:
        """
        Return the container client, bootstrapping it on first use.

        Returns
        -------
        Any
            Configured ``ContainerClient`` instance.

        Raises
        ------
        MissingStorageDependencyException
            If ``azure-storage-blob`` is not installed.
        """
        if self._container is not None:
            return self._container

        # Import the official SDK lazily; it is an optional dependency.
        sdk = importDriverDependency(
            "azure.storage.blob", "azure-storage-blob", "azure",
        )
        errors = importDriverDependency(
            "azure.core.exceptions", "azure-storage-blob", "azure",
        )

        if self._connection_string:
            service = sdk.BlobServiceClient.from_connection_string(
                self._connection_string,
            )
        else:
            account_url = (
                f"https://{self._account_name}.blob.core.windows.net"
            )
            service = sdk.BlobServiceClient(
                account_url=account_url,
                credential=self._account_key or None,
            )

        self._sdk = sdk
        self._not_found = errors.ResourceNotFoundError
        self._http_error = errors.HttpResponseError
        self._container = service.get_container_client(self._container_name)
        return self._container

    def __blob(self, normalized: str) -> Any:
        """
        Return the blob client for *normalized*.

        Parameters
        ----------
        normalized : str
            Canonical root-relative file path.

        Returns
        -------
        Any
            ``BlobClient`` bound to the blob.
        """
        return self.__containerClient().get_blob_client(normalized)

    def __missing(self, normalized: str) -> StorageFileNotFoundException:
        """
        Build the framework exception for a missing blob.

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

    def __propsSync(self, normalized: str) -> Any:
        """
        Fetch blob properties or raise when the blob is absent.

        Parameters
        ----------
        normalized : str
            Canonical root-relative file path.

        Returns
        -------
        Any
            ``BlobProperties`` for the blob.

        Raises
        ------
        StorageFileNotFoundException
            If the blob does not exist.
        """
        blob = self.__blob(normalized)
        try:
            return blob.get_blob_properties()
        except self._not_found as exc:
            raise self.__missing(normalized) from exc

    def __listKeysSync(self, prefix: str) -> list[str]:
        """
        List every blob name under *prefix*.

        Parameters
        ----------
        prefix : str
            Name prefix to filter by; empty string lists everything.

        Returns
        -------
        list[str]
            All matching blob names, including directory markers.
        """
        container = self.__containerClient()
        return [
            blob.name
            for blob in container.list_blobs(name_starts_with=prefix or None)
        ]

    def __contentSettings(self, normalized: str) -> Any:
        """
        Build the content settings for an upload, when derivable.

        Parameters
        ----------
        normalized : str
            Canonical root-relative file path.

        Returns
        -------
        Any
            ``ContentSettings`` with the guessed MIME type, or ``None``
            when no type could be guessed.
        """
        mime = mimetypes.guess_type(normalized)[0]
        if not mime:
            return None
        return self._sdk.ContentSettings(content_type=mime)

    def __urlFor(self, normalized: str) -> str:
        """
        Compose the public URL of a blob without SDK involvement.

        Parameters
        ----------
        normalized : str
            Canonical root-relative file path.

        Returns
        -------
        str
            URL derived from the configured base URL or the canonical
            Azure Blob endpoint.
        """
        encoded = quote(normalized, safe="/")
        if self._base_url:
            return f"{self._base_url}/{encoded}"
        host = f"{self._account_name}.blob.core.windows.net"
        return f"https://{host}/{self._container_name}/{encoded}"

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
        Read the full contents of the blob at *path*.

        Parameters
        ----------
        path : str
            Root-relative file path.

        Returns
        -------
        bytes
            Complete blob contents.

        Raises
        ------
        StorageFileNotFoundException
            If the blob does not exist.
        """
        normalized = normalizeFilePath(path)

        def _read() -> bytes:
            blob = self.__blob(normalized)
            try:
                return blob.download_blob().readall()
            except self._not_found as exc:
                raise self.__missing(normalized) from exc

        return await asyncio.to_thread(_read)

    async def readStream(
        self,
        path: str,
        chunk_size: int = _CHUNK_SIZE,
    ) -> AsyncIterator[bytes]:
        """
        Stream the contents of the blob at *path* in chunks.

        Chunk sizing follows the SDK transfer configuration; the
        *chunk_size* parameter is advisory for this driver.

        Parameters
        ----------
        path : str
            Root-relative file path.
        chunk_size : int
            Advisory chunk size in bytes.

        Yields
        ------
        bytes
            Consecutive chunks of the blob contents.

        Raises
        ------
        StorageFileNotFoundException
            If the blob does not exist.
        """
        normalized = normalizeFilePath(path)
        del chunk_size

        def _open() -> Any:
            blob = self.__blob(normalized)
            try:
                return blob.download_blob().chunks()
            except self._not_found as exc:
                raise self.__missing(normalized) from exc

        iterator = await asyncio.to_thread(_open)
        sentinel: bytes = b""
        while True:
            chunk = await asyncio.to_thread(next, iterator, sentinel)
            if not chunk:
                break
            yield chunk

    async def exists(self, path: str) -> bool:
        """
        Check whether a blob exists at *path*.

        Parameters
        ----------
        path : str
            Root-relative file path.

        Returns
        -------
        bool
            ``True`` if a blob exists at the given name.
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
        Write *contents* to *path*, replacing any existing blob.

        Azure Blob Storage has no per-blob visibility; access is
        governed by the container access level, so *visibility* is
        accepted for interface compatibility but ignored.

        Parameters
        ----------
        path : str
            Root-relative file path.
        contents : bytes | str
            Data to persist. Strings are encoded as UTF-8.
        visibility : str | None
            Ignored by this driver.

        Returns
        -------
        None
        """
        normalized = normalizeFilePath(path)
        del visibility
        data = (
            contents.encode("utf-8")
            if isinstance(contents, str)
            else bytes(contents)
        )

        def _write() -> None:
            container = self.__containerClient()
            container.upload_blob(
                name=normalized,
                data=data,
                overwrite=True,
                content_settings=self.__contentSettings(normalized),
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
        (spilling to disk past 8 MiB) and uploaded in blocks by the
        SDK.

        Parameters
        ----------
        path : str
            Root-relative file path.
        stream : AsyncIterable[bytes]
            Asynchronous byte-chunk producer.
        visibility : str | None
            Ignored by this driver.

        Returns
        -------
        None
        """
        normalized = normalizeFilePath(path)
        del visibility
        buffer = await self.__spool(stream)

        def _upload() -> None:
            container = self.__containerClient()
            container.upload_blob(
                name=normalized,
                data=buffer,
                overwrite=True,
                content_settings=self.__contentSettings(normalized),
            )

        try:
            await asyncio.to_thread(_upload)
        finally:
            await asyncio.to_thread(buffer.close)

    async def delete(self, path: str) -> bool:
        """
        Delete the blob at *path*.

        Parameters
        ----------
        path : str
            Root-relative file path.

        Returns
        -------
        bool
            ``True`` if the blob existed and was removed.
        """
        normalized = normalizeFilePath(path)

        def _delete() -> bool:
            blob = self.__blob(normalized)
            try:
                blob.delete_blob()
            except self._not_found:
                return False
            return True

        return await asyncio.to_thread(_delete)

    async def copy(self, source: str, target: str) -> None:
        """
        Copy the blob at *source* to *target*.

        The content is streamed through a spooled local buffer, which
        works with any authentication mode and never loads large blobs
        fully into memory.

        Parameters
        ----------
        source : str
            Root-relative path of the existing blob.
        target : str
            Root-relative destination path.

        Returns
        -------
        None

        Raises
        ------
        StorageFileNotFoundException
            If the source blob does not exist.
        """
        origin = normalizeFilePath(source)
        destination = normalizeFilePath(target)

        def _copy() -> None:
            container = self.__containerClient()
            buffer = tempfile.SpooledTemporaryFile(  # noqa: SIM115
                max_size=_SPOOL_THRESHOLD,
            )
            try:
                try:
                    container.get_blob_client(
                        origin,
                    ).download_blob().readinto(buffer)
                except self._not_found as exc:
                    raise self.__missing(origin) from exc
                buffer.seek(0)
                container.upload_blob(
                    name=destination,
                    data=buffer,
                    overwrite=True,
                    content_settings=self.__contentSettings(destination),
                )
            finally:
                buffer.close()

        await asyncio.to_thread(_copy)

    async def move(self, source: str, target: str) -> None:
        """
        Move the blob at *source* to *target*.

        Implemented as a copy followed by a delete of the source blob.

        Parameters
        ----------
        source : str
            Root-relative path of the existing blob.
        target : str
            Root-relative destination path.

        Returns
        -------
        None

        Raises
        ------
        StorageFileNotFoundException
            If the source blob does not exist.
        """
        await self.copy(source, target)
        normalized = normalizeFilePath(source)
        await asyncio.to_thread(
            lambda: self.__blob(normalized).delete_blob(),
        )

    # ── Metadata operations ──────────────────────────────────────────────────

    async def size(self, path: str) -> int:
        """
        Return the size in bytes of the blob at *path*.

        Parameters
        ----------
        path : str
            Root-relative file path.

        Returns
        -------
        int
            Blob size in bytes.

        Raises
        ------
        StorageFileNotFoundException
            If the blob does not exist.
        """
        normalized = normalizeFilePath(path)
        props = await asyncio.to_thread(self.__propsSync, normalized)
        return int(props.size or 0)

    async def mimeType(self, path: str) -> str | None:
        """
        Return the MIME type of the blob at *path*.

        Prefers the content type stored in Azure and falls back to a
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
            If the blob does not exist.
        """
        normalized = normalizeFilePath(path)
        props = await asyncio.to_thread(self.__propsSync, normalized)
        stored = getattr(props.content_settings, "content_type", None)
        return stored or mimetypes.guess_type(normalized)[0]

    async def lastModified(self, path: str) -> datetime:
        """
        Return the last-modification timestamp of the blob at *path*.

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
            If the blob does not exist.
        """
        normalized = normalizeFilePath(path)
        props = await asyncio.to_thread(self.__propsSync, normalized)
        return props.last_modified or datetime.now(tz=UTC)

    async def visibility(self, path: str) -> str:
        """
        Return the effective visibility of the blob at *path*.

        Azure controls access at container level, so the result
        reflects the container access policy rather than a per-blob
        ACL.

        Parameters
        ----------
        path : str
            Root-relative file path.

        Returns
        -------
        str
            ``'public'`` when the container allows anonymous access,
            otherwise ``'private'``.

        Raises
        ------
        StorageFileNotFoundException
            If the blob does not exist.
        """
        normalized = normalizeFilePath(path)

        def _visibility() -> str:
            # Assert existence first to honor the driver contract.
            self.__propsSync(normalized)
            container = self.__containerClient()
            try:
                policy = container.get_container_access_policy()
            except self._http_error:
                return Visibility.PRIVATE.value
            return (
                Visibility.PUBLIC.value
                if policy.get("public_access")
                else Visibility.PRIVATE.value
            )

        return await asyncio.to_thread(_visibility)

    async def setVisibility(self, path: str, visibility: str) -> None:
        """
        Change the visibility of the blob at *path*.

        Azure Blob Storage does not support per-blob visibility, so
        this operation always fails. Adjust the container access level
        from the Azure portal or management SDK instead.

        Parameters
        ----------
        path : str
            Root-relative file path.
        visibility : str
            Requested visibility level.

        Returns
        -------
        None
            Never returned by this driver.

        Raises
        ------
        UnsupportedStorageOperationException
            Always, since Azure has no per-blob visibility.
        """
        del visibility
        error_msg = (
            "Azure Blob Storage does not support per-blob visibility "
            f"for [{normalizeFilePath(path)}]; configure the container "
            "access level instead."
        )
        raise UnsupportedStorageOperationException(error_msg)

    async def hash(self, path: str, algorithm: str = "sha256") -> str:
        """
        Compute the content hash of the blob at *path*.

        The blob is streamed in chunks, so large files never load
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
            Hexadecimal digest of the blob contents.

        Raises
        ------
        StorageFileNotFoundException
            If the blob does not exist.
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

            blob = self.__blob(normalized)
            try:
                downloader = blob.download_blob()
            except self._not_found as exc:
                raise self.__missing(normalized) from exc
            for chunk in downloader.chunks():
                hasher.update(chunk)
            return hasher.hexdigest()

        return await asyncio.to_thread(_hash)

    async def info(self, path: str) -> FileInfo:
        """
        Collect a metadata snapshot for the blob at *path*.

        The snapshot is built from blob properties only; ``checksum``
        holds the Content-MD5 stored by Azure when available.

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
            If the blob does not exist.
        """
        normalized = normalizeFilePath(path)

        def _info() -> FileInfo:
            props = self.__propsSync(normalized)
            container = self.__containerClient()
            try:
                policy = container.get_container_access_policy()
                is_public = bool(policy.get("public_access"))
            except self._http_error:
                is_public = False

            stored_md5 = getattr(props.content_settings, "content_md5", None)
            stored_type = getattr(
                props.content_settings, "content_type", None,
            )
            return FileInfo(
                path=normalized,
                size=int(props.size or 0),
                lastModified=props.last_modified or datetime.now(tz=UTC),
                visibility=(
                    Visibility.PUBLIC.value
                    if is_public
                    else Visibility.PRIVATE.value
                ),
                mimeType=stored_type or mimetypes.guess_type(normalized)[0],
                createdAt=props.creation_time,
                etag=str(props.etag or "").strip('"') or None,
                checksum=bytes(stored_md5).hex() if stored_md5 else None,
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

        def _create() -> None:
            container = self.__containerClient()
            container.upload_blob(
                name=f"{normalized}/", data=b"", overwrite=True,
            )

        await asyncio.to_thread(_create)

    async def deleteDirectory(self, path: str) -> bool:
        """
        Recursively delete every blob under *path*.

        Parameters
        ----------
        path : str
            Root-relative directory path. The empty string clears the
            whole container prefix space.

        Returns
        -------
        bool
            ``True`` if at least one blob was removed.
        """
        normalized = normalizePath(path)
        prefix = f"{normalized}/" if normalized else ""

        def _purge() -> bool:
            container = self.__containerClient()
            names = self.__listKeysSync(prefix)
            for name in names:
                container.delete_blob(name)
            return bool(names)

        return await asyncio.to_thread(_purge)

    async def directoryExists(self, path: str) -> bool:
        """
        Check whether any blob exists under *path*.

        Parameters
        ----------
        path : str
            Root-relative directory path. The empty string denotes
            the disk root.

        Returns
        -------
        bool
            ``True`` if the prefix contains at least one blob.
        """
        normalized = normalizePath(path)
        if not normalized:
            return True

        def _exists() -> bool:
            container = self.__containerClient()
            iterator = container.list_blobs(
                name_starts_with=f"{normalized}/",
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
        List the blob names that represent files under *path*.

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
        Build the public URL for the blob at *path*.

        Parameters
        ----------
        path : str
            Root-relative file path.

        Returns
        -------
        str
            URL derived from the configured base URL or the canonical
            Azure Blob endpoint.
        """
        return self.__urlFor(normalizeFilePath(path))

    async def temporaryUrl(self, path: str, expires_in: int) -> str:
        """
        Build a SAS URL for the blob at *path*.

        Requires the storage account key, either configured explicitly
        or embedded in the connection string.

        Parameters
        ----------
        path : str
            Root-relative file path.
        expires_in : int
            Lifetime of the URL in seconds.

        Returns
        -------
        str
            Read-only SAS URL valid for *expires_in* seconds.

        Raises
        ------
        UnsupportedStorageOperationException
            If no account key is available for signing.
        MissingStorageDependencyException
            If ``azure-storage-blob`` is not installed.
        """
        normalized = normalizeFilePath(path)
        if not self._account_key:
            error_msg = (
                "Generating a SAS URL requires the Azure storage account "
                f"key for [{normalized}]."
            )
            raise UnsupportedStorageOperationException(error_msg)

        def _sign() -> str:
            # Bootstrap ensures the SDK module reference is available.
            self.__containerClient()
            sas = self._sdk.generate_blob_sas(
                account_name=self._account_name,
                container_name=self._container_name,
                blob_name=normalized,
                account_key=self._account_key,
                permission=self._sdk.BlobSasPermissions(read=True),
                expiry=datetime.now(tz=UTC) + timedelta(seconds=expires_in),
            )
            return f"{self.__urlFor(normalized)}?{sas}"

        return await asyncio.to_thread(_sign)

    async def download(self, path: str, destination: str | Path) -> Path:
        """
        Download the blob at *path* to the local filesystem.

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
            If the blob does not exist.
        """
        normalized = normalizeFilePath(path)

        def _download() -> Path:
            target = resolveDownloadTarget(normalized, destination)
            blob = self.__blob(normalized)
            try:
                downloader = blob.download_blob()
            except self._not_found as exc:
                raise self.__missing(normalized) from exc
            with target.open("wb") as handle:
                downloader.readinto(handle)
            return target.resolve()

        return await asyncio.to_thread(_download)

    def open(self, path: str, mode: str = "rb") -> AsyncStream:
        """
        Open an asynchronous binary stream for the blob at *path*.

        Read-oriented modes download the blob into a spooled temporary
        buffer; writable modes upload the buffered content back to
        Azure when the stream is closed.

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
                    blob.download_blob().readinto(buffer)
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
            # Persist the buffered content back to Azure on close.
            handle.seek(0)
            self.__containerClient().upload_blob(
                name=normalized,
                data=handle,
                overwrite=True,
                content_settings=self.__contentSettings(normalized),
            )

        on_close = None if mode == "rb" else flush
        return AsyncStream(opener, on_close)
