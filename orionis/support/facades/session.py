from orionis.container.facades.facade import ScopedFacade
from orionis.session.contracts.session import ISession

class Session(ScopedFacade):

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
