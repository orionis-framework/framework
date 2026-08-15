from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Self

class IHasher(ABC):
    """
    Define the contract implemented by every password hashing driver.

    Implementations must rely on algorithms designed for password storage
    (Argon2id, bcrypt) and never on general purpose digests such as MD5
    or the SHA family.
    """

    __slots__ = ()

    @abstractmethod
    def make(
        self,
        value: str,
        *,
        rounds: int | None = None,
        memory: int | None = None,
        threads: int | None = None,
    ) -> str:
        """
        Hash a plain text value.

        Parameters
        ----------
        value : str
            Plain text value to hash.
        rounds : int | None
            Per-call cost override. Maps to the bcrypt cost factor and to
            the Argon2id time cost. ``None`` keeps the configured value.
        memory : int | None
            Per-call memory cost override, in kibibytes. Only meaningful
            for drivers that support it.
        threads : int | None
            Per-call parallelism override. Only meaningful for drivers
            that support it.

        Returns
        -------
        str
            Encoded hash, including algorithm identifier, parameters and
            salt.
        """

    @abstractmethod
    def check(self, value: str, hashed: str) -> bool:
        """
        Verify a plain text value against an encoded hash.

        Parameters
        ----------
        value : str
            Plain text value to verify.
        hashed : str
            Previously generated hash.

        Returns
        -------
        bool
            ``True`` when the value matches the hash, ``False`` otherwise.
        """

    @abstractmethod
    def needsRehash(self, hashed: str) -> bool:
        """
        Determine whether a hash was produced with outdated parameters.

        Parameters
        ----------
        hashed : str
            Previously generated hash.

        Returns
        -------
        bool
            ``True`` when the hash should be regenerated with the current
            configuration.
        """

    @abstractmethod
    def getAlgorithm(self) -> str:
        """
        Return the identifier of the algorithm used by the driver.

        Returns
        -------
        str
            Algorithm identifier, such as ``'argon2id'`` or ``'bcrypt'``.
        """

    @abstractmethod
    def setRounds(self, rounds: int) -> Self:
        """
        Set the default cost factor used by the driver.

        Parameters
        ----------
        rounds : int
            New cost factor. Maps to the bcrypt cost factor and to the
            Argon2id time cost.

        Returns
        -------
        Self
            The same instance, allowing fluent configuration.

        Raises
        ------
        HashConfigurationException
            If the value is not a valid cost factor for the driver.
        """
