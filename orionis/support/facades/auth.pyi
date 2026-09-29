from orionis.auth.contracts.manager import IAuthManager
from orionis.container.contracts.facade import IFacade

class Auth(IAuthManager, IFacade):
    @classmethod
    def getFacadeAccessor(cls) -> type[IAuthManager]: ...
