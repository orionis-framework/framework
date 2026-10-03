"""Expose storage drivers on first access."""

from typing import TYPE_CHECKING as _TYPE_CHECKING

from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.storage.drivers.azure import AzureStorageDriver
    from orionis.storage.drivers.gcs import GoogleStorageDriver
    from orionis.storage.drivers.local import LocalStorageDriver
    from orionis.storage.drivers.memory import MemoryStorageDriver
    from orionis.storage.drivers.s3 import S3StorageDriver

__all__ = [
    "AzureStorageDriver",
    "GoogleStorageDriver",
    "LocalStorageDriver",
    "MemoryStorageDriver",
    "S3StorageDriver",
]

_EXPORTS = {
    "AzureStorageDriver": ("orionis.storage.drivers.azure", "AzureStorageDriver"),
    "GoogleStorageDriver": ("orionis.storage.drivers.gcs", "GoogleStorageDriver"),
    "LocalStorageDriver": ("orionis.storage.drivers.local", "LocalStorageDriver"),
    "MemoryStorageDriver": ("orionis.storage.drivers.memory", "MemoryStorageDriver"),
    "S3StorageDriver": ("orionis.storage.drivers.s3", "S3StorageDriver"),
}


def __getattr__(name: str) -> object:
    """Resolve and cache a public storage driver.

    Parameters
    ----------
    name : str
        Name requested from this package.

    Returns
    -------
    object
        Driver class from its defining module.

    Raises
    ------
    AttributeError
        If the requested name is not exported.
    """
    return _resolve_export(globals(), _EXPORTS, name)


def __dir__() -> list[str]:
    """List loaded attributes and public storage drivers.

    Returns
    -------
    list[str]
        Sorted names visible on this package.
    """
    return sorted(globals().keys() | _EXPORTS.keys())
