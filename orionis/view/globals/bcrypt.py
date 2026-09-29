from __future__ import annotations
from typing import TYPE_CHECKING, Any
from orionis.encrypter.contracts.encrypter import IEncrypter

if TYPE_CHECKING:
    from orionis.foundation.contracts.application import IApplication

# ruff: noqa: ANN401

def _global_encrypt(app: IApplication) -> Any:
    """
    Build the ``encrypt`` template global.

    Parameters
    ----------
    app : IApplication
        Application container to expose in templates.

    Returns
    -------
    Any
        Callable returning the application instance.
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

def _global_decrypt(app: IApplication) -> Any:
    """
    Build the ``decrypt`` template global.

    Parameters
    ----------
    app : IApplication
        Application container to expose in templates.

    Returns
    -------
    Any
        Callable returning the application instance.
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
