# ruff: noqa: PYI021
# Keep public facade methods documented alongside their static signatures.
from orionis.container.contracts.facade import IFacade
from orionis.realtime.clients import HubClients
from orionis.realtime.contracts.manager import IConnectionManager
from orionis.realtime.hub import Hub

class Realtime(IFacade):
    @classmethod
    def getFacadeAccessor(cls) -> type[IConnectionManager]:
        """Return the contract registered for this facade in the container."""

    @staticmethod
    def hub(hub: type[Hub]) -> HubClients:
        """Create application-service client selectors for one Hub class."""
