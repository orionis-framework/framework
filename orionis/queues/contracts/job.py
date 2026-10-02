from abc import ABC, abstractmethod

class IJob(ABC):
    """Declare the asynchronous entry point of a persistent job."""

    __slots__ = ()

    @abstractmethod
    async def handle(self) -> None:
        """
        Execute the job with services resolved by the application.

        Returns
        -------
        None
            Complete the job's side effects.
        """
