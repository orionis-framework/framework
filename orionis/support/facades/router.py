from orionis.container.facades.facade import Facade

class Route(Facade):
    """Forward route registration, including ``auth()``, to the pinned router."""

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
