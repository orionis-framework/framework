from abc import ABC, abstractmethod

class IFacade(ABC):

    @classmethod
    @abstractmethod
    def getFacadeAccessor(cls) -> str | type:
        """
        Return the container accessor key for this facade.

        Returns
        -------
        str | type
            The alias or contract class used to resolve the container binding.

        Raises
        ------
        NotImplementedError
            Raised when the subclass does not implement this method.
        """

    @classmethod
    @abstractmethod
    async def resolve(cls, *args: object, **kwargs: object) -> object:
        """
        Resolve the service instance bound to this facade.

        Parameters
        ----------
        *args : object
            Positional arguments forwarded to the container make call.
        **kwargs : object
            Keyword arguments forwarded to the container make call.

        Returns
        -------
        object
            The resolved service instance from the application container.

        Raises
        ------
        RuntimeError
            Raised when the application has not been booted.
        """

    @classmethod
    @abstractmethod
    async def pin(cls) -> None:
        """
        Pin the resolved instance on this facade class.

        Returns
        -------
        None
            Returns ``None`` after storing the currently resolved instance.
        """

    @classmethod
    @abstractmethod
    def unpin(cls) -> None:
        """
        Clear the pinned instance from this facade class.

        Returns
        -------
        None
            Returns ``None`` after clearing the cached pinned instance.
        """
