from orionis.container.contracts.facade import IFacade
from orionis.realtime.clients import HubClients
from orionis.realtime.contracts.manager import IConnectionManager
from orionis.realtime.hub import Hub

class Realtime(IFacade):

    @classmethod
    def getFacadeAccessor(cls) -> type[IConnectionManager]:
        ...

    @staticmethod
    def hub(hub: type[Hub]) -> HubClients:
        ...
