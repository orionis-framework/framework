# ruff: noqa: TC001, TC003
# Keep public callback and application annotations resolvable at runtime.
"""Provide view globals operations through ``_global_encrypt``, ``_global_decrypt``."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from orionis.encrypter.contracts.encrypter import IEncrypter
from orionis.foundation.contracts.application import IApplication


def _global_encrypt(app: IApplication) -> Callable[[str], Awaitable[str]]:
    """
    Build the ``encrypt`` template global.

    Parameters
    ----------
    app : orionis.IApplication
        Application container to expose in templates.

    Returns
    -------
    collections.abc.Callable
        Async callable encrypting plaintext through the configured encrypter.
    """

    async def encrypt(plaintext: str) -> str:
        """
        Encrypt the given value using the application's encrypter.

        Parameters
        ----------
        plaintext : str
            The value to encrypt.

        Returns
        -------
        str
            The encrypted value.
        """
        crypt: IEncrypter = await app.make(IEncrypter)
        return crypt.encrypt(plaintext)

    return encrypt


def _global_decrypt(app: IApplication) -> Callable[[str], Awaitable[str]]:
    """
    Build the ``decrypt`` template global.

    Parameters
    ----------
    app : orionis.IApplication
        Application container to expose in templates.

    Returns
    -------
    collections.abc.Callable
        Async callable decrypting payloads through the configured encrypter.
    """

    async def decrypt(payload: str) -> str:
        """
        Decrypt the given value using the application's encrypter.

        Parameters
        ----------
        payload : str
            The value to decrypt.

        Returns
        -------
        str
            The decrypted value.
        """
        crypt: IEncrypter = await app.make(IEncrypter)
        return crypt.decrypt(payload)

    return decrypt
