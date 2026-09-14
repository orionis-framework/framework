from orionis.auth.contracts.manager import IAuthManager
from orionis.container.facades.facade import Facade

class Auth(Facade):

    @classmethod
    def getFacadeAccessor(cls) -> type:
        """
        Return the container accessor for the authentication manager.

        Returns
        -------
        type
            Contract used to resolve the service in the application
            container.
        """
        return IAuthManager
