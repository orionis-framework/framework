"""Resolve the application service through the application facade."""

from orionis.container.facades.facade import Facade


class Application(Facade):
    """Resolve the application service through the application facade."""

    @classmethod
    def getFacadeAccessor(cls) -> str:
        """
        Return the container alias for the application.

        Returns
        -------
        str
            String identifier for the service in the application container.
        """
        return "x-orionis-IApplication"
