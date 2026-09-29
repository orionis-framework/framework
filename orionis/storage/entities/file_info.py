# ruff: noqa: N815
from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

@dataclass(frozen=True, kw_only=True, slots=True)
class FileInfo:
    """
    Immutable snapshot of a stored file's metadata.

    Instances are produced by storage drivers and returned by
    ``await file.info()``. All values reflect the state of the file at
    the moment the snapshot was taken.

    Attributes
    ----------
    path : str
        Canonical root-relative path of the file on its disk.
    size : int
        File size in bytes.
    lastModified : datetime
        Timezone-aware timestamp of the last modification.
    visibility : str
        Visibility level of the file (``'public'`` or ``'private'``).
    mimeType : str | None
        Guessed MIME type, or ``None`` when it cannot be determined.
    createdAt : datetime | None
        Timezone-aware creation timestamp, or ``None`` when the driver
        cannot provide it.
    etag : str | None
        Entity tag of the content (MD5 hex digest for built-in drivers),
        or ``None`` when unavailable.
    checksum : str | None
        SHA-256 hex digest of the content, or ``None`` when unavailable.
    url : str | None
        Public URL of the file, or ``None`` when the disk does not
        expose URLs.
    """

    # Field names are intentionally camelCase to match the public API
    # naming convention of the framework (see ruff N815 waiver above).
    path: str
    size: int
    lastModified: datetime  # NOSONAR
    visibility: str
    mimeType: str | None = None  # NOSONAR
    createdAt: datetime | None = None  # NOSONAR
    etag: str | None = None
    checksum: str | None = None
    url: str | None = None
