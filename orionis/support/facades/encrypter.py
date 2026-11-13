"""Resolve the crypt service through the application facade."""

from orionis.container.facades.facade import Facade
from orionis.encrypter.contracts.encrypter import IEncrypter


class Crypt(Facade):
    """Resolve the crypt service through the application facade."""

    @classmethod
    def getFacadeAccessor(cls) -> type:
        """
        Return the contract used to resolve the encrypter.

        Returns
        -------
        type[IEncrypter]
            Contract registered in the application container.
        """
        return IEncrypter
