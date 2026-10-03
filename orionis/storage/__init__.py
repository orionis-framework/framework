from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.storage.directory import Directory
    from orionis.storage.disk import Disk
    from orionis.storage.drivers.azure import AzureStorageDriver
    from orionis.storage.drivers.gcs import GoogleStorageDriver
    from orionis.storage.drivers.local import LocalStorageDriver
    from orionis.storage.drivers.memory import MemoryStorageDriver
    from orionis.storage.drivers.s3 import S3StorageDriver
    from orionis.storage.entities.file_info import FileInfo
    from orionis.storage.enums.visibility import Visibility
    from orionis.storage.file import File
    from orionis.storage.manager import StorageManager
    from orionis.storage.stream import AsyncStream
    from orionis.storage.uploaded_file import UploadedFile

__all__ = [
    "AsyncStream",
    "AzureStorageDriver",
    "Directory",
    "Disk",
    "File",
    "FileInfo",
    "GoogleStorageDriver",
    "LocalStorageDriver",
    "MemoryStorageDriver",
    "S3StorageDriver",
    "StorageManager",
    "UploadedFile",
    "Visibility",
]

_EXPORTS = {
    "AsyncStream": ("orionis.storage.stream", "AsyncStream"),
    "AzureStorageDriver": ("orionis.storage.drivers.azure", "AzureStorageDriver"),
    "Directory": ("orionis.storage.directory", "Directory"),
    "Disk": ("orionis.storage.disk", "Disk"),
    "File": ("orionis.storage.file", "File"),
    "FileInfo": ("orionis.storage.entities.file_info", "FileInfo"),
    "GoogleStorageDriver": ("orionis.storage.drivers.gcs", "GoogleStorageDriver"),
    "LocalStorageDriver": ("orionis.storage.drivers.local", "LocalStorageDriver"),
    "MemoryStorageDriver": ("orionis.storage.drivers.memory", "MemoryStorageDriver"),
    "S3StorageDriver": ("orionis.storage.drivers.s3", "S3StorageDriver"),
    "StorageManager": ("orionis.storage.manager", "StorageManager"),
    "UploadedFile": ("orionis.storage.uploaded_file", "UploadedFile"),
    "Visibility": ("orionis.storage.enums.visibility", "Visibility"),
}

def __getattr__(name: str) -> object:
    """
    Resolve and cache a public storage export.

    Parameters
    ----------
    name : str
        Name requested from this package.

    Returns
    -------
    object
        Exported object from its defining module.

    Raises
    ------
    AttributeError
        If the requested name is not exported.
    """
    return _resolve_export(globals(), _EXPORTS, name)

def __dir__() -> list[str]:
    """
    List loaded attributes and public storage exports.

    Returns
    -------
    list[str]
        Sorted names visible on this package.
    """
    return sorted(globals().keys() | _EXPORTS.keys())
