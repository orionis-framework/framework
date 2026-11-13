"""Resolve the route service through the application facade."""

from orionis.container.facades.facade import Facade


class Route(Facade):
    """Resolve the route service through the application facade."""

    @classmethod
    def getFacadeAccessor(cls) -> str:
        """
        Return the facade accessor string for the router contract.

        Returns
        -------
        str
            String identifier for the service in the application container.
        """
        return "x-orionis-IRouter"
