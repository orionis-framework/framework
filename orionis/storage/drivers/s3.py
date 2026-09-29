from __future__ import annotations
import asyncio
import hashlib
import mimetypes
import tempfile
from datetime import UTC, datetime
from typing import TYPE_CHECKING
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
    from typing import Any, BinaryIO

# Default chunk size for streaming operations (64 KiB).
_CHUNK_SIZE: int = 64 * 1024

# In-memory bytes before spooled buffers spill to disk (8 MiB).
_SPOOL_THRESHOLD: int = 8 * 1024 * 1024

# Maximum number of keys per S3 batch-delete request.
_DELETE_BATCH: int = 1000

# Error codes reported by S3 for missing objects.
_MISSING_CODES: frozenset[str] = frozenset({"404", "NoSuchKey", "NotFound"})

# Canned ACLs applied per visibility level.
_ACL_MAP: dict[str, str] = {
    Visibility.PUBLIC.value: "public-read",
    Visibility.PRIVATE.value: "private",
}

# Grantee URI identifying anonymous users in S3 ACL grants. This is the
# canonical identifier defined by AWS, not a network endpoint, so the
# scheme must remain exactly as documented.
_ALL_USERS_URI: str = "http://acs.amazonaws.com/groups/global/AllUsers"  # NOSONAR

class S3StorageDriver(IStorageDriver):
    """
    Storage driver backed by Amazon S3 (or S3-compatible services).

    Uses the official AWS SDK for Python (``boto3``), which is an
    **optional dependency**: it is not installed with the framework.
    Install it before using this driver::

        pip install boto3
        # or
        pip install orionis[s3]

    The SDK is imported lazily on first operation, and every blocking
    call runs on a worker thread via :func:`asyncio.to_thread` so the
    event loop stays responsive. Directories are virtual: prefixes are
    inferred from object keys, and explicit directories are stored as
    zero-byte ``path/`` marker objects.
    """

    # ruff: noqa: ANN401

    __slots__ = (
        "_base_url",
        "_bucket",
        "_client",
        "_client_error",
        "_endpoint",
        "_key",
        "_region",
        "_secret",
        "_use_path_style",
    )

    def __init__(self, config: object) -> None:
        """
        Initialize the driver from an S3 disk configuration entity.

        No SDK import or network activity happens here; the client is
        bootstrapped lazily on first use.

        Parameters
        ----------
        config : object
            Disk configuration exposing ``bucket``, ``region``,
            ``key``, ``secret``, ``url``, ``endpoint``, and
            ``use_path_style_endpoint``.

        Returns
        -------
        None
        """
        self._bucket: str = str(getattr(config, "bucket", "") or "")
        self._region: str = str(getattr(config, "region", "") or "")
        self._key: str = str(getattr(config, "key", "") or "")
        self._secret: str = str(getattr(config, "secret", "") or "")
        self._endpoint: str | None = getattr(config, "endpoint", None) or None
        self._use_path_style: bool = bool(
            getattr(config, "use_path_style_endpoint", False),
        )

        base_url = getattr(config, "url", None)
        self._base_url: str | None = base_url.rstrip("/") if base_url else None

        self._client: Any = None
        self._client_error: type[Exception] = Exception

    # ── SDK bootstrap and low-level helpers ──────────────────────────────────

    def __client(self) -> Any:
        """
        Return the boto3 S3 client, bootstrapping it on first use.

        Returns
        -------
        Any
            Configured ``boto3`` S3 client.

        Raises
        ------
        MissingStorageDependencyException
            If ``boto3`` is not installed.
        """
        if self._client is not None:
            return self._client

        # Import the official SDK lazily; it is an optional dependency.
        boto3 = importDriverDependency("boto3", "boto3", "s3")
        botocore_config = importDriverDependency(
            "botocore.config", "boto3", "s3",
        )
        botocore_exceptions = importDriverDependency(
            "botocore.exceptions", "boto3", "s3",
        )

        params: dict[str, Any] = {
            "region_name": self._region or None,
            "endpoint_url": self._endpoint,
        }

        # Explicit credentials win; otherwise boto3 uses its own chain.
        if self._key and self._secret:
            params["aws_access_key_id"] = self._key
            params["aws_secret_access_key"] = self._secret
        if self._use_path_style:
            params["config"] = botocore_config.Config(
                s3={"addressing_style": "path"},
            )

        self._client = boto3.client("s3", **params)
        self._client_error = botocore_exceptions.ClientError
        return self._client

    def __isMissing(self, exc: Exception) -> bool:
        """
        Check whether an SDK error denotes a missing object.

        Parameters
        ----------
        exc : Exception
            Exception raised by the boto3 client.

        Returns
        -------
        bool
            ``True`` when the error code maps to a 404 condition.
        """
        response = getattr(exc, "response", None) or {}
        code = str(response.get("Error", {}).get("Code", ""))
        return code in _MISSING_CODES

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

    def __headSync(self, normalized: str) -> dict:
        """
        Fetch object metadata or raise when the object is absent.

        Parameters
        ----------
        normalized : str
            Canonical root-relative file path.

        Returns
        -------
        dict
            Raw ``head_object`` response.

        Raises
        ------
        StorageFileNotFoundException
            If the object does not exist.
        """
        client = self.__client()
        try:
            return client.head_object(Bucket=self._bucket, Key=normalized)
        except self._client_error as exc:
            if not self.__isMissing(exc):
                raise
            raise self.__missing(normalized) from exc

    def __listKeysSync(self, prefix: str) -> list[str]:
        """
        List every object key under *prefix*.

        Parameters
        ----------
        prefix : str
            Key prefix to filter by; empty string lists the bucket.

        Returns
        -------
        list[str]
            All matching object keys, including directory markers.
        """
        client = self.__client()
        keys: list[str] = []
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            keys.extend(
                entry["Key"] for entry in page.get("Contents", [])
            )
        return keys

    def __aclFor(self, visibility: str) -> str:
        """
        Map a visibility level onto an S3 canned ACL.

        Parameters
        ----------
        visibility : str
            Visibility level (``'public'`` or ``'private'``).

        Returns
        -------
        str
            Canned ACL name.

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

    def __putArgs(
        self,
        normalized: str,
        visibility: str | None,
    ) -> dict[str, str]:
        """
        Build the optional arguments for an object upload.

        Parameters
        ----------
        normalized : str
            Canonical root-relative file path.
        visibility : str | None
            Visibility to apply, or ``None`` to omit the ACL.

        Returns
        -------
        dict[str, str]
            Extra arguments with ``ContentType`` and optional ``ACL``.
        """
        args: dict[str, str] = {}
        mime = mimetypes.guess_type(normalized)[0]
        if mime:
            args["ContentType"] = mime
        if visibility is not None:
            args["ACL"] = self.__aclFor(visibility)
        return args

    def __visibilitySync(self, normalized: str) -> str:
        """
        Resolve the object visibility from its ACL grants.

        Parameters
        ----------
        normalized : str
            Canonical root-relative file path.

        Returns
        -------
        str
            ``'public'`` when anonymous users hold a read grant,
            otherwise ``'private'``.

        Raises
        ------
        StorageFileNotFoundException
            If the object does not exist.
        """
        client = self.__client()
        try:
            grants = client.get_object_acl(
                Bucket=self._bucket, Key=normalized,
            ).get("Grants", [])
        except self._client_error as exc:
            if not self.__isMissing(exc):
                raise
            raise self.__missing(normalized) from exc

        for grant in grants:
            grantee = grant.get("Grantee", {})
            readable = grant.get("Permission") in ("READ", "FULL_CONTROL")
            if grantee.get("URI") == _ALL_USERS_URI and readable:
                return Visibility.PUBLIC.value
        return Visibility.PRIVATE.value

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
            Public URL derived from the configured base URL, custom
            endpoint, or the canonical virtual-host address.
        """
        encoded = quote(normalized, safe="/")
        if self._base_url:
            return f"{self._base_url}/{encoded}"
        if self._endpoint:
            return f"{self._endpoint.rstrip('/')}/{self._bucket}/{encoded}"
        host = f"{self._bucket}.s3.{self._region}.amazonaws.com"
        return f"https://{host}/{encoded}"

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
            client = self.__client()
            try:
                body = client.get_object(
                    Bucket=self._bucket, Key=normalized,
                )["Body"]
            except self._client_error as exc:
                if not self.__isMissing(exc):
                    raise
                raise self.__missing(normalized) from exc
            with body:
                return body.read()

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
            client = self.__client()
            try:
                return client.get_object(
                    Bucket=self._bucket, Key=normalized,
                )["Body"]
            except self._client_error as exc:
                if not self.__isMissing(exc):
                    raise
                raise self.__missing(normalized) from exc

        body = await asyncio.to_thread(_open)
        try:
            while True:
                chunk = await asyncio.to_thread(body.read, chunk_size)
                if not chunk:
                    break
                yield chunk
        finally:
            await asyncio.to_thread(body.close)

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
            ``True`` if an object exists at the given key.
        """
        normalized = normalizeFilePath(path)

        def _exists() -> bool:
            try:
                self.__headSync(normalized)
            except StorageFileNotFoundException:
                return False
            return True

        return await asyncio.to_thread(_exists)

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
            Visibility to apply, or ``None`` for the bucket default.

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

        def _write() -> None:
            client = self.__client()
            client.put_object(
                Bucket=self._bucket,
                Key=normalized,
                Body=data,
                **self.__putArgs(normalized, visibility),
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

        The payload is buffered into a spooled temporary file (spilling
        to disk past 8 MiB) and uploaded with the SDK's managed
        transfer, which switches to multipart uploads for large
        objects.

        Parameters
        ----------
        path : str
            Root-relative file path.
        stream : AsyncIterable[bytes]
            Asynchronous byte-chunk producer.
        visibility : str | None
            Visibility to apply, or ``None`` for the bucket default.

        Returns
        -------
        None
        """
        normalized = normalizeFilePath(path)
        buffer = await self.__spool(stream)

        def _upload() -> None:
            client = self.__client()
            client.upload_fileobj(
                buffer,
                self._bucket,
                normalized,
                ExtraArgs=self.__putArgs(normalized, visibility),
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
            try:
                self.__headSync(normalized)
            except StorageFileNotFoundException:
                return False
            self.__client().delete_object(
                Bucket=self._bucket, Key=normalized,
            )
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
            client = self.__client()
            try:
                client.copy_object(
                    Bucket=self._bucket,
                    Key=destination,
                    CopySource={"Bucket": self._bucket, "Key": origin},
                )
            except self._client_error as exc:
                if not self.__isMissing(exc):
                    raise
                raise self.__missing(origin) from exc

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
        await asyncio.to_thread(
            lambda: self.__client().delete_object(
                Bucket=self._bucket, Key=normalized,
            ),
        )

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
        head = await asyncio.to_thread(self.__headSync, normalized)
        return int(head.get("ContentLength", 0))

    async def mimeType(self, path: str) -> str | None:
        """
        Return the MIME type of the object at *path*.

        Prefers the ``Content-Type`` stored in S3 and falls back to a
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
        head = await asyncio.to_thread(self.__headSync, normalized)
        return (
            head.get("ContentType")
            or mimetypes.guess_type(normalized)[0]
        )

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
        head = await asyncio.to_thread(self.__headSync, normalized)
        stamp = head.get("LastModified")
        return stamp if stamp is not None else datetime.now(tz=UTC)

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
            ``'public'`` or ``'private'`` based on the object ACL.

        Raises
        ------
        StorageFileNotFoundException
            If the object does not exist.
        """
        normalized = normalizeFilePath(path)
        return await asyncio.to_thread(self.__visibilitySync, normalized)

    async def setVisibility(self, path: str, visibility: str) -> None:
        """
        Change the visibility of the object at *path*.

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
        acl = self.__aclFor(visibility)

        def _apply() -> None:
            client = self.__client()
            try:
                client.put_object_acl(
                    Bucket=self._bucket, Key=normalized, ACL=acl,
                )
            except self._client_error as exc:
                if not self.__isMissing(exc):
                    raise
                raise self.__missing(normalized) from exc

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

            client = self.__client()
            try:
                body = client.get_object(
                    Bucket=self._bucket, Key=normalized,
                )["Body"]
            except self._client_error as exc:
                if not self.__isMissing(exc):
                    raise
                raise self.__missing(normalized) from exc
            with body:
                while chunk := body.read(_CHUNK_SIZE):
                    hasher.update(chunk)
            return hasher.hexdigest()

        return await asyncio.to_thread(_hash)

    async def info(self, path: str) -> FileInfo:
        """
        Collect a metadata snapshot for the object at *path*.

        The snapshot is built from object metadata only; the
        ``checksum`` field is ``None`` because computing it would
        require a full download (use :meth:`hash` instead).

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
            head = self.__headSync(normalized)
            try:
                visibility = self.__visibilitySync(normalized)
            except self._client_error:
                # ACL access may be disabled on the bucket.
                visibility = Visibility.PRIVATE.value

            stamp = head.get("LastModified") or datetime.now(tz=UTC)
            return FileInfo(
                path=normalized,
                size=int(head.get("ContentLength", 0)),
                lastModified=stamp,
                visibility=visibility,
                mimeType=(
                    head.get("ContentType")
                    or mimetypes.guess_type(normalized)[0]
                ),
                createdAt=None,
                etag=str(head.get("ETag", "")).strip('"') or None,
                checksum=None,
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
            lambda: self.__client().put_object(
                Bucket=self._bucket, Key=f"{normalized}/", Body=b"",
            ),
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
            keys = self.__listKeysSync(prefix)
            if not keys:
                return False
            client = self.__client()
            for start in range(0, len(keys), _DELETE_BATCH):
                batch = keys[start:start + _DELETE_BATCH]
                client.delete_objects(
                    Bucket=self._bucket,
                    Delete={"Objects": [{"Key": key} for key in batch]},
                )
            return True

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
            response = self.__client().list_objects_v2(
                Bucket=self._bucket,
                Prefix=f"{normalized}/",
                MaxKeys=1,
            )
            return int(response.get("KeyCount", 0)) > 0

        return await asyncio.to_thread(_exists)

    async def files(
        self,
        path: str = "",
        *,
        recursive: bool = False,
    ) -> list[str]:
        """
        List the object keys that represent files under *path*.

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
            URL derived from the configured base URL, custom endpoint,
            or the canonical virtual-host address.
        """
        return self.__urlFor(normalizeFilePath(path))

    async def temporaryUrl(self, path: str, expires_in: int) -> str:
        """
        Build a presigned URL for the object at *path*.

        Parameters
        ----------
        path : str
            Root-relative file path.
        expires_in : int
            Lifetime of the URL in seconds.

        Returns
        -------
        str
            Presigned GET URL valid for *expires_in* seconds.

        Raises
        ------
        MissingStorageDependencyException
            If ``boto3`` is not installed.
        """
        normalized = normalizeFilePath(path)

        def _sign() -> str:
            return self.__client().generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": normalized},
                ExpiresIn=expires_in,
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
            client = self.__client()
            try:
                client.download_file(self._bucket, normalized, str(target))
            except self._client_error as exc:
                if not self.__isMissing(exc):
                    raise
                raise self.__missing(normalized) from exc
            return target.resolve()

        return await asyncio.to_thread(_download)

    def open(self, path: str, mode: str = "rb") -> AsyncStream:
        """
        Open an asynchronous binary stream for the object at *path*.

        Read-oriented modes download the object into a spooled
        temporary buffer; writable modes upload the buffered content
        back to S3 when the stream is closed.

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
                self.__seedStream(buffer, normalized, mode)
            return buffer

        def flush(handle: BinaryIO) -> None:
            # Persist the buffered content back to S3 on close.
            handle.seek(0)
            self.__client().upload_fileobj(
                handle,
                self._bucket,
                normalized,
                ExtraArgs=self.__putArgs(normalized, None),
            )

        on_close = None if mode == "rb" else flush
        return AsyncStream(opener, on_close)

    def __seedStream(
        self,
        buffer: BinaryIO,
        normalized: str,
        mode: str,
    ) -> None:
        """
        Seed *buffer* with the current object content for a stream.

        Downloads the object into the buffer and positions the cursor
        according to *mode*. Missing objects are tolerated for append
        modes and rejected for read modes.

        Parameters
        ----------
        buffer : BinaryIO
            Spooled buffer backing the stream.
        normalized : str
            Canonical root-relative file path.
        mode : str
            Binary mode requested by the caller.

        Returns
        -------
        None

        Raises
        ------
        StorageFileNotFoundException
            If the object does not exist and *mode* requires it.
        """
        client = self.__client()
        try:
            client.download_fileobj(self._bucket, normalized, buffer)
        except self._client_error as exc:
            if not self.__isMissing(exc):
                buffer.close()
                raise
            if mode in ("rb", "rb+"):
                buffer.close()
                raise self.__missing(normalized) from exc
        if mode.startswith("a"):
            buffer.seek(0, 2)
        else:
            buffer.seek(0)
