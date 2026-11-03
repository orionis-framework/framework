"""Resolve the mail service through the application facade."""

from orionis.container.facades.facade import Facade
from orionis.mail.contracts.manager import IMailManager

class Mail(Facade):
    """Resolve the mail service through the application facade."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    @classmethod
    def getFacadeAccessor(cls) -> type[IMailManager]:
        """
        Return the contract shared by the facade and dependency injection.

        Returns
        -------
        type[orionis.mail.contracts.IMailManager]
            The mail manager's container binding.
        """
        return IMailManager
