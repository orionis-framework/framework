from __future__ import annotations
from abc import abstractmethod
from orionis.hashing.contracts.hasher import IHasher

class IHashManager(IHasher):
    """
    Define the contract for the hashing manager.

    The manager resolves the configured driver and exposes the same API as
    a single hasher, so application code never depends on a concrete
    algorithm.
    """

    __slots__ = ()

    @abstractmethod
    def driver(self, name: str | None = None) -> IHasher:
        """
        Return the hasher bound to the named (or default) driver.

        Parameters
        ----------
        name : str | None
            Driver name (``'argon2'`` or ``'bcrypt'``). ``None`` selects
            the configured default driver.

        Returns
        -------
        IHasher
            Hasher instance for the requested driver.

        Raises
        ------
        HashDriverNotSupportedException
            If the requested driver is not supported.
        """

    @abstractmethod
    def getDefaultDriver(self) -> str:
        """
        Return the name of the configured default driver.

        Returns
        -------
        str
            Driver name, such as ``'argon2'`` or ``'bcrypt'``.
        """
