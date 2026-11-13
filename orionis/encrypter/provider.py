# ruff: noqa: PLC0415
# Resolve the implementation only when its service is registered.
"""Service provider for the Orionis encryption system."""

from __future__ import annotations
from orionis.container.providers.service_provider import ServiceProvider
from orionis.encrypter.contracts.encrypter import IEncrypter
from orionis.support.facades.encrypter import Crypt as CryptFacade


class EncrypterProvider(ServiceProvider):
    """
    Service provider for the Orionis encryption system.

    Binds :class:`orionis.encrypter.contracts.IEncrypter` to
    :class:`orionis.encrypter.Encrypter` as a singleton and pins
    the :class:`orionis.support.facades.Crypt` facade so the synchronous
    ``Crypt.encrypt(...)`` and
    ``Crypt.decrypt(...)`` calls resolve without container overhead.
    """

    def register(self) -> None:
        """
        Bind the encrypter contract to its singleton implementation.

        Returns
        -------
        None
            No return value.
        """
        from orionis.encrypter import Encrypter

        self.app.singleton(IEncrypter, Encrypter)

    async def boot(self) -> None:
        """
        Pin the Crypt facade after all services are registered.

        Pinning is mandatory here because the encrypter exposes a synchronous
        API: consumers such as ``Stringable.encrypt()`` call the facade without
        awaiting, and an unpinned facade would hand them a dispatcher object.

        Returns
        -------
        None
            No return value.
        """
        await CryptFacade.pin()
