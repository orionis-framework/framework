from orionis.container.facades.facade import Facade
from orionis.storage.contracts.manager import IStorageManager


class Storage(Facade):
    """
    Facade for the storage system.

    Proxies all calls to the bound :class:`IStorageManager` singleton.
    The facade is only an entry point: every behavior lives in the
    domain objects resolved through it.

    Usage (facade pinned at boot)::

        avatar = Storage.disk("public").file("avatars/user.png")
        data   = await avatar.read()

        disk   = Storage.default()
        photos = await disk.directory("photos").files()
    """

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
