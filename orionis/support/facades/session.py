"""Resolve the session service through the application facade."""

from orionis.container.facades.facade import ScopedFacade
from orionis.session.contracts.session import ISession


class Session(ScopedFacade):
    """Resolve the session service through the application facade."""

    @classmethod
    def getFacadeAccessor(cls) -> type[ISession]:
        """
        Return the contract of the request-local session.

        Returns
        -------
        type
            The facade contract type.
        """
        return ISession
