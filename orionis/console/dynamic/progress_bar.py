from __future__ import annotations
import sys
from orionis.console.dynamic.contracts.progress_bar import IProgressBar

class ProgressBar(IProgressBar):

    def __init__(self, total: int = 100, width: int = 50) -> None:
        """
        Initialize a new progress bar instance.

        Parameters
        ----------
        total : int, optional
            Maximum value representing 100% progress. Default is 100.
        width : int, optional
            Width of the progress bar in characters. Default is 50.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Set the total value for 100% progress
        self.total = total

        # Set the width of the progress bar
        self.bar_width = width

        # Initialize progress to zero
        self.progress = 0

        # Cache references to sys.stdout methods for faster access in the hot path
        _stdout = sys.stdout
        self._write = _stdout.write
        self._flush = _stdout.flush

    def __updateBar(self) -> None:
        """
        Update the visual representation of the progress bar in the console.

        Calculates the percentage of completion and redraws the progress bar
        in place, overwriting the previous output.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Cache local variables for faster access in the hot path
        progress = self.progress
        total = self.total
        width = self.bar_width

        # Calculate the number of filled characters and the percentage complete
        filled = width * progress // total
        pct = progress * 100 // total

        # Write the progress bar to the console, using carriage return to overwrite
        self._write(f"\r[{'█' * filled}{'░' * (width - filled)}] {pct}%")
        self._flush()

    def start(self) -> None:
        """
        Reset and display the progress bar at the starting state.

        Sets the progress to zero and renders the initial progress bar.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Reset progress to zero
        self.progress = 0

        # Render the initial progress bar
        self.__updateBar()

    def advance(self, increment: int = 1) -> None:
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
        # Inline clamp: avoids min() function-call overhead in the hot path
        progress = self.progress + increment
        self.progress = min(self.total, progress)

        # Update the progress bar display
        self.__updateBar()

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
        # Set progress to the maximum value
        self.progress = self.total

        # Update the progress bar to show completion
        self.__updateBar()

        # Move the cursor to a new line for cleaner output
        self._write("\n")
        self._flush()
