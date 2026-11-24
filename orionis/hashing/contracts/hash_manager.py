# ruff: noqa: TC001
# Driver return types use lazy package exports for runtime reflection.
"""Define the contract for the hashing manager."""

from __future__ import annotations
from abc import abstractmethod
from typing import Literal, overload
from orionis import hashing
from orionis.hashing.contracts.hasher import IHasher


class IHashManager(IHasher):
    """
    Define the contract for the hashing manager.

    The manager resolves the configured driver and exposes the same API as
    a single hasher, so application code never depends on a concrete
    algorithm.
    """

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    @overload
    def driver(self, name: Literal["argon2"]) -> hashing.Argon2Hasher: ...

    @overload
    def driver(self, name: Literal["bcrypt"]) -> hashing.BcryptHasher: ...

    @overload
    def driver(self, name: str | None = None) -> IHasher: ...

    @abstractmethod
    def driver(self, name: str | None = None) -> IHasher:
        """
        Return the hasher bound to the named (or default) driver.

        Parameters
        ----------
        name : str | None
            Driver name (``'argon2'`` or ``'bcrypt'``). ``None`` selects
            the configured default driver. An empty string also selects it.

        Returns
        -------
        orionis.hashing.contracts.IHasher
            Hasher instance for the requested driver.

        Raises
        ------
        orionis.hashing.exceptions.HashDriverNotSupportedException
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
