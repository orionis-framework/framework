from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.foundation.config.filesystems.entitites.aws import S3
    from orionis.foundation.config.filesystems.entitites.azure import Azure
    from orionis.foundation.config.filesystems.entitites.disks import Disks
    from orionis.foundation.config.filesystems.entitites.filesystems import Filesystems
    from orionis.foundation.config.filesystems.entitites.gcs import GCS
    from orionis.foundation.config.filesystems.entitites.local import Local
    from orionis.foundation.config.filesystems.entitites.public import Public
    from orionis.foundation.config.filesystems.enums.disk_name import DiskName

__all__ = [
    "GCS",
    "S3",
    "Azure",
    "DiskName",
    "Disks",
    "Filesystems",
    "Local",
    "Public",
]

_EXPORTS = {
    "GCS": ("orionis.foundation.config.filesystems.entitites.gcs", "GCS"),
    "S3": ("orionis.foundation.config.filesystems.entitites.aws", "S3"),
    "Azure": ("orionis.foundation.config.filesystems.entitites.azure", "Azure"),
    "DiskName": ("orionis.foundation.config.filesystems.enums.disk_name", "DiskName"),
    "Disks": ("orionis.foundation.config.filesystems.entitites.disks", "Disks"),
    "Filesystems": ("orionis.foundation.config.filesystems.entitites.filesystems", "Filesystems"),
    "Local": ("orionis.foundation.config.filesystems.entitites.local", "Local"),
    "Public": ("orionis.foundation.config.filesystems.entitites.public", "Public"),
}

def __getattr__(name: str) -> object:
    """
    Resolve and cache a public package export.

    Parameters
    ----------
    name : str
        Public attribute requested from this package.

    Returns
    -------
    object
        Exported object from its defining module.

    Raises
    ------
    AttributeError
        If the requested attribute is not exported.
    """
    return _resolve_export(globals(), _EXPORTS, name)

def __dir__() -> list[str]:
    """
    List loaded attributes and declared public exports.

    Returns
    -------
    list[str]
        Sorted attribute names available on this package.
    """
    return sorted(globals().keys() | _EXPORTS.keys())
