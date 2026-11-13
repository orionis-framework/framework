# ruff: noqa: TC001, TC003
# Keep public callback and application annotations resolvable at runtime.
"""Provide view globals operations.

Includes ``_disk_file_url``, ``_global_asset``, ``_global_secure_asset``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from orionis.foundation.config.filesystems import DiskName
from orionis.foundation.contracts.application import IApplication
from orionis.storage.contracts.manager import IStorageManager
from orionis.view.globals.url import _to_secure_url

_PUBLIC_DISK: str = DiskName.PUBLIC.value


async def _disk_file_url(
    app: IApplication,
    path: str,
    disk: str | None,
) -> str:
    """
    Resolve the public URL of a file stored on a disk.

    Parameters
    ----------
    app : orionis.IApplication
        Application container used to resolve the storage manager.
    path : str
        Disk-relative file path (e.g. ``'css/app.css'``).
    disk : str | None
        Disk name to read from, or ``None`` for the ``public`` disk.

    Returns
    -------
    str
        Publicly accessible URL for the file.

    Raises
    ------
    orionis.storage.exceptions.UnsupportedStorageOperationException
        If the resolved disk does not expose public URLs.
    """
    storage: IStorageManager = await app.make(IStorageManager)
    return await storage.disk(disk or _PUBLIC_DISK).file(path).url()


def _global_asset(app: IApplication) -> Callable[..., Awaitable[str]]:
    """
    Build the async ``asset`` template global bound to the application.

    Parameters
    ----------
    app : orionis.IApplication
        Application container used to resolve the storage manager.

    Returns
    -------
    collections.abc.Callable
        Async callable that builds the public URL of a stored file.
    """

    async def asset(path: str, disk: str | None = None) -> str:
        """
        Build the public URL of a file stored on a disk.

        Parameters
        ----------
        path : str
            Disk-relative file path (e.g. ``'css/app.css'``).
        disk : str | None, optional
            Disk name to read from, or ``None`` for the ``public`` disk.

        Returns
        -------
        str
            Publicly accessible URL for the file.

        Raises
        ------
        orionis.storage.exceptions.UnsupportedStorageOperationException
            If the resolved disk does not expose public URLs.
        """
        return await _disk_file_url(app, path, disk)

    return asset


def _global_secure_asset(app: IApplication) -> Callable[..., Awaitable[str]]:
    """
    Build the async ``secure_asset`` template global bound to the app.

    Parameters
    ----------
    app : orionis.IApplication
        Application container used to resolve the storage manager.

    Returns
    -------
    collections.abc.Callable
        Async callable that builds the HTTPS URL of a stored file.
    """

    async def secure_asset(path: str, disk: str | None = None) -> str:
        """
        Build the HTTPS URL of a file stored on a disk.

        Parameters
        ----------
        path : str
            Disk-relative file path (e.g. ``'css/app.css'``).
        disk : str | None, optional
            Disk name to read from, or ``None`` for the ``public`` disk.

        Returns
        -------
        str
            File URL served over HTTPS when a host is known, otherwise
            the URL as produced by the disk.

        Raises
        ------
        orionis.storage.exceptions.UnsupportedStorageOperationException
            If the resolved disk does not expose public URLs.
        """
        return _to_secure_url(await _disk_file_url(app, path, disk))

    return secure_asset
