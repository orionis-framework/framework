from __future__ import annotations
from typing import TYPE_CHECKING
from orionis.console.enums.styles import ANSIColors
from orionis.console.output.contracts.executor import IExecutor
from orionis.support.facades.datetime import DateTime

if TYPE_CHECKING:
    from datetime import datetime

class Executor(IExecutor):

    # ruff: noqa: T201

    def __getNow(self) -> datetime:
        """
        Return the current date and time.

        Returns
        -------
        datetime
            Current date and time as a datetime object.
        """
        # Use DateTime facade to get current datetime
        return DateTime.now()

    def __ansiOutput(
        self,
        program: str,
        state: str,
        state_color: str,
        time: str = "",
    ) -> None:
        """
        Output a formatted console message with timestamp, program name, and state.

        Parameters
        ----------
        program : str
            Program or process name.
        state : str
            Execution state (e.g., 'RUNNING', 'DONE', 'FAIL').
        state_color : str
            ANSI color code for state text.
        time : str, optional
            Execution duration with units. Default is ''.

        Returns
        -------
        None
            Prints the formatted message to the console.
        """
        # Define the total width for the output line
        width = 60

        # Cache ANSI color codes to avoid repeated lookups
        muted = ANSIColors.TEXT_MUTED.value
        default = ANSIColors.DEFAULT.value

        # Calculate lengths for spacing
        len_program = len(program)
        len_state = len(state)
        len_time = len(time)

        # Create dotted line separator
        line = "." * (width - (len_program + len_state + len_time))

        # Format timestamp with muted color;
        # cache the current time to avoid multiple calls
        timestamp = (
            f"{muted}{self.__getNow().strftime('%Y-%m-%d %H:%M:%S')}{default}"
        )

        # Single f-string: 1 str object vs 2 separate allocations + 1 concat op
        time_formatted = f"{muted}{time}{default}" if time else ""

        # Format state with color
        state_formatted = f"{state_color}{state}{default}"

        # Add line breaks for visual separation
        start = "\n\r" if state == "RUNNING" else ""
        end = "\n\r" if state != "RUNNING" else ""

        # Print the formatted message; program used directly (was f"{program}" before)
        print(
            f"{start}{timestamp} | {program} {line} "
            f"{time_formatted} {state_formatted}{end}",
            flush=True,
        )

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
        # Call the private ANSI output method with
        # RUNNING state and warning color formatting
        self.__ansiOutput(program, "RUNNING", ANSIColors.TEXT_BOLD_WARNING.value, time)

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
        # Call the private ANSI output method with DONE
        # state and success color formatting
        self.__ansiOutput(
            program,
            "DONE",
            ANSIColors.TEXT_BOLD_SUCCESS.value,
            f" ~ {time}",
        )

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
        # Call the private ANSI output method with FAIL state and error color formatting
        self.__ansiOutput(
            program,
            "FAIL",
            ANSIColors.TEXT_BOLD_ERROR.value,
            f" ~ {time}",
        )
