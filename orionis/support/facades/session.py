from orionis.container.facades.facade import Facade
from orionis.session.contracts.session import ISession

class Session(Facade):

    @classmethod
    def getFacadeAccessor(cls) -> type[ISession]:
        """
        Return the facade accessor string for the unit test contract.

        Returns
        -------
        type
            The facade contract type.
        """
        return ISession
