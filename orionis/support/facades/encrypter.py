"""Resolve the crypt service through the application facade."""

from orionis.container.facades.facade import Facade
from orionis.encrypter.contracts.encrypter import IEncrypter

class Crypt(Facade):
    """Resolve the crypt service through the application facade."""

    @classmethod
    def getFacadeAccessor(cls) -> type:
        """
        Return the facade accessor string for the unit test contract.

        Returns
        -------
        str
            String identifier for the service in the application container.
        """
        return IEncrypter
