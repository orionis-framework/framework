from orionis.container.facades.facade import Facade
from orionis.hashing.contracts.hash_manager import IHashManager

class Hash(Facade):

    @classmethod
    def getFacadeAccessor(cls) -> type:
        """
        Return the container accessor for the hashing manager.

        Returns
        -------
        type
            Contract used to resolve the service in the application
            container.
        """
        return IHashManager
