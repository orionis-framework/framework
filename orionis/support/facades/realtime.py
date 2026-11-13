"""Expose worker-local Hub targeting from ordinary application services."""

from orionis.container.facades.facade import Facade
from orionis.realtime.contracts.manager import IConnectionManager


class Realtime(Facade):
    """Expose worker-local Hub targeting from ordinary application services."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    @classmethod
    def getFacadeAccessor(cls) -> type[IConnectionManager]:
        """
        Return the registry contract owned by the application container.

        Returns
        -------
        type[orionis.realtime.contracts.IConnectionManager]
            Replaceable realtime targeting and connection registry contract.
        """
        return IConnectionManager
