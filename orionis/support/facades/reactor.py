"""Resolve the reactor service through the application facade."""

from orionis.container.facades.facade import Facade


class Reactor(Facade):
    """Resolve the reactor service through the application facade."""

    @classmethod
    def getFacadeAccessor(cls) -> str:
        """
        Return the container alias for the command reactor.

        Returns
        -------
        str
            String identifier for the service in the application container.
        """
        return "x-orionis-IReactor"
