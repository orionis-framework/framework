"""Resolve the debug service through the application facade."""

from orionis.container.facades.facade import Facade

class Debug(Facade):
    """Resolve the debug service through the application facade."""

    @classmethod
    def getFacadeAccessor(cls) -> str:
        """Return the container alias for the dumper contract.

        Returns
        -------
        str
            Alias used to resolve the registered dumper service.
        """
        return "x-orionis-IDumper"
