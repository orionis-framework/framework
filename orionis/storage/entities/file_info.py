# ruff: noqa: N815, TC003
"""Immutable snapshot of a stored file's metadata."""

from __future__ import annotations
from dataclasses import dataclass
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
    lastModified : datetime.datetime
        Timezone-aware timestamp of the last modification.
    visibility : str
        Visibility level of the file (``'public'`` or ``'private'``).
    mimeType : str | None
        Guessed MIME type, or ``None`` when it cannot be determined.
    createdAt : datetime.datetime | None
        Timezone-aware creation timestamp, or ``None`` when the driver
        cannot provide it.
    etag : str | None
        Backend entity tag, which need not be a complete-content MD5 digest,
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
    lastModified: datetime
    visibility: str
    mimeType: str | None = None
    createdAt: datetime | None = None
    etag: str | None = None
    checksum: str | None = None
    url: str | None = None
