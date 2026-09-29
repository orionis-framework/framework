from __future__ import annotations
from abc import ABC, abstractmethod

class IServiceProvider(ABC):

    @abstractmethod
    def register(self) -> None:
        """
        Register services and components into the application container.

        This synchronous method must be implemented by subclasses to bind services,
        configurations, or other components to the application container. It is called
        during the application's service registration phase.

        Note
        ----
        This method must be synchronous. Asynchronous operations are not supported
        in this method.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        NotImplementedError
            If the method is not overridden in a subclass.
        """

    @abstractmethod
    async def boot(self) -> None:
        """
        Perform post-registration initialization tasks.

        This asynchronous method is called after all services have been registered.
        Subclasses may override this method to initialize services or perform operations
        required at application boot time.

        Returns
        -------
        None
            This method does not return a value.
        """
