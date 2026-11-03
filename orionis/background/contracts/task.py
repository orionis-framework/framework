"""Define the interface for background task execution."""

from abc import ABC, abstractmethod

class IBackgroundTask(ABC):
    """
    Define the interface for background task execution.

    Any concrete implementation must provide a ``run`` coroutine
    that executes the task asynchronously.
    """

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    @abstractmethod
    async def run(self) -> None:
        """
        Run the background task.

        Returns
        -------
        None
            This method does not return a value.
        """
