"""Base class for asynchronous application database seeders."""

from abc import ABC, abstractmethod

class Seeder(ABC):
    """Base class for asynchronous application database seeders."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    @abstractmethod
    async def run(self) -> None:
        """
        Insert the application data described by this seeder.

        Returns
        -------
        None
            The operation is complete when all data has been written.
        """
