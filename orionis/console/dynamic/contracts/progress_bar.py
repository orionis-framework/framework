from __future__ import annotations
from abc import ABC, abstractmethod

class IProgressBar(ABC):

    @abstractmethod
    def start(self) -> None:
        """
        Reset and display the progress bar at the starting state.

        Sets the progress to zero and renders the initial progress bar.

        Returns
        -------
        None
            This method does not return a value.
        """

    @abstractmethod
    def advance(
        self,
        increment: int = 1,
    ) -> None:
        """
        Advance the progress bar by a specified increment.

        Parameters
        ----------
        increment : int, optional
            Value by which to increase the progress. Default is 1.

        Notes
        -----
        Progress will not exceed the total value.

        Returns
        -------
        None
            This method does not return a value.
        """

    @abstractmethod
    def finish(self) -> None:
        """
        Complete the progress bar and move to a new line.

        Sets progress to the maximum value, updates the bar, and moves the
        cursor to a new line for cleaner output.

        Returns
        -------
        None
            This method does not return a value.
        """
