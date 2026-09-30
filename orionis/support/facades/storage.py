from orionis.container.facades.facade import Facade
from orionis.storage.contracts.manager import IStorageManager

class Storage(Facade):

    @classmethod
    def getFacadeAccessor(cls) -> type:
        """
        Return the container accessor for the storage manager.

        Returns
        -------
        type
            :class:`IStorageManager`.
        """
        return IStorageManager
