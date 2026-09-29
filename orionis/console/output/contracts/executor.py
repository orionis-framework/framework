from __future__ import annotations
from abc import ABC, abstractmethod

class IExecutor(ABC):

    @abstractmethod
    def running(self, program: str, time: str = "") -> None:
        """
        Log the execution of a program in the "RUNNING" state.

        Outputs a formatted console message indicating that a program or process
        is currently running. Uses ANSI color coding to highlight the running state
        with a warning color. The output includes timestamp, program name, optional
        execution time, and colored state indicator.

        Parameters
        ----------
        program : str
            Name of the program or process being executed.
        time : str, optional
            Current execution time duration with units. Default is ''.

        Returns
        -------
        None
            This method prints the formatted running state message to the console.
        """

    @abstractmethod
    def done(self, program: str, time: str = "") -> None:
        """
        Log the completion of a program in the "DONE" state.

        Outputs a formatted console message indicating successful completion of a
        program or process. Uses ANSI color coding to highlight the completion
        state with a success color. The output includes timestamp, program name,
        optional execution time, and colored state indicator.

        Parameters
        ----------
        program : str
            Name of the program or process that has completed execution.
        time : str, optional
            Total execution time duration with units. Default is ''.

        Returns
        -------
        None
            This method prints the formatted completion state message to the console.
        """

    @abstractmethod
    def fail(self, program: str, time: str = "") -> None:
        """
        Log program execution in the "FAIL" state.

        Outputs a formatted console message indicating that a program or process
        has failed. Uses ANSI color coding to highlight the failure state with
        an error color. The output includes timestamp, program name, optional
        execution time, and colored state indicator.

        Parameters
        ----------
        program : str
            Name of the program or process that failed.
        time : str, optional
            Execution time duration before failure. Default is ''.

        Returns
        -------
        None
            This method prints the formatted failure state message to the console.
        """
