from orionis.container.facades.facade import Facade
from orionis.mail.contracts.manager import IMailManager


class Mail(Facade):
    """Proxy the eager mail manager after normal HTTP or CLI startup."""

    __slots__ = ()

    @classmethod
    def getFacadeAccessor(cls) -> type[IMailManager]:
        """Return the contract shared by the facade and dependency injection.

        Returns
        -------
        type[IMailManager]
            The mail manager's container binding.
        """
        return IMailManager
