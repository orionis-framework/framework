"""Resolve the storage service through the application facade."""

from orionis.container.facades.facade import Facade
from orionis.storage.contracts.manager import IStorageManager


class Storage(Facade):
    """Resolve the storage service through the application facade."""

    @classmethod
    def getFacadeAccessor(cls) -> type:
        """
        Return the container accessor for the storage manager.

        Returns
        -------
        type
            :class:`orionis.storage.contracts.IStorageManager`.
        """
        return IStorageManager
