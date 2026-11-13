"""Define the contract for encrypter implementations."""

from __future__ import annotations
from abc import ABC, abstractmethod


class IEncrypter(ABC):
    """Define the contract for encrypter implementations."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    @abstractmethod
    def encrypt(
        self,
        plaintext: str,
    ) -> str:
        """
        Encrypt plaintext using the configured cipher algorithm.

        Parameters
        ----------
        plaintext : str
            The text to encrypt.

        Returns
        -------
        str
            Base64-encoded encrypted payload containing IV, value, tag, and cipher.

        Raises
        ------
        TypeError
            If plaintext is not a string.
        ValueError
            If plaintext is empty or has encoding issues.
        RuntimeError
            If encryption fails.
        """

    @abstractmethod
    def decrypt(
        self,
        payload: str,
    ) -> str:
        """
        Decrypt an encrypted payload using the configured cipher algorithm.

        Parameters
        ----------
        payload : str
            Base64-encoded encrypted payload containing IV, value, tag, and cipher.

        Returns
        -------
        str
            The decrypted plaintext as a UTF-8 string.

        Raises
        ------
        TypeError
            If payload is not a string.
        ValueError
            If payload is empty or invalid.
        RuntimeError
            If decryption fails.
        """
