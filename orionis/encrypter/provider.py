from __future__ import annotations
from orionis.container.providers.service_provider import ServiceProvider
from orionis.encrypter.contracts.encrypter import IEncrypter
from orionis.encrypter.encrypter import Encrypter
from orionis.support.facades.encrypter import Crypt as CryptFacade

class EncrypterProvider(ServiceProvider):
    """
    Service provider for the Orionis encryption system.

    Binds :class:`IEncrypter` to :class:`Encrypter` as a singleton and pins
    the :class:`Crypt` facade so the synchronous ``Crypt.encrypt(...)`` and
    ``Crypt.decrypt(...)`` calls resolve without container overhead.
    """

    def register(self) -> None:
        """
        Register the encrypter service in the application container.

        This method binds the IEncrypter interface to its concrete implementation
        as a singleton, ensuring a single instance is shared across the application.

        Returns
        -------
        None
            This method does not return a value.
        """
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
            This method does not return a value. It performs initialization only.
        """
        await CryptFacade.pin()
