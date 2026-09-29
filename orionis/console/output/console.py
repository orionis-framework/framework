from __future__ import annotations
import asyncio
import getpass
import os
import sys
from typing import TYPE_CHECKING, Any
from rich.console import Console as RichConsole
from rich.traceback import Traceback
from orionis.console.dynamic.progress_bar import ProgressBar
from orionis.console.enums.styles import ANSIColors
from orionis.console.output.contracts.console import IConsole
from orionis.console.output.var_dumper import VarDumper
from orionis.support.facades.datetime import DateTime

if TYPE_CHECKING:
    from orionis.console.dynamic.contracts.progress_bar import IProgressBar
    from _typeshed import SupportsWrite
    from datetime import datetime

class Console(IConsole):

    # ruff: noqa: T201, B905, PLR0913

    @property
    def progressBar(self) -> IProgressBar:
        """
        Get a new instance of the ProgressBar class.

        Returns
        -------
        IProgressBar
            A new instance of the ProgressBar class.
        """
        return ProgressBar()

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

    def __getTimestamp(self) -> str:
        """
        Return current date and time formatted with muted color.

        Returns
        -------
        str
            Formatted timestamp string in muted color.
        """
        # Format timestamp and wrap with muted ANSI color codes
        return (
            f"{ANSIColors.TEXT_MUTED.value}"
            f"{self.__getNow().strftime('%Y-%m-%d %H:%M:%S')}"
            f"{ANSIColors.DEFAULT.value}"
        )

    def __printWithBackground(
        self, label: str, bg_color: ANSIColors, message: str, *, timestamp: bool,
    ) -> None:
        """
        Print a formatted message with a background color.

        Parameters
        ----------
        label : str
            Label to display (e.g., 'SUCCESS', 'INFO').
        bg_color : ANSIColors
            Background color to use.
        message : str
            Message to print.
        timestamp : bool
            Whether to include a timestamp.

        Returns
        -------
        None
            This method does not return any value.
        """
        # Get the timestamp string if required
        str_time = self.__getTimestamp() if timestamp else ""

        # Print the message with background color, label, and optional timestamp
        print(
            f"{bg_color.value}{ANSIColors.TEXT_WHITE.value} {label} "
            f"{ANSIColors.DEFAULT.value} {str_time} {message}"
            f"{ANSIColors.DEFAULT.value}",
        )

    def __printColored(self, message: str, text_color: ANSIColors) -> None:
        """
        Print a message with the specified text color.

        Parameters
        ----------
        message : str
            Message to print.
        text_color : ANSIColors
            Text color to use.

        Returns
        -------
        None
            This method does not return any value.
        """
        # Print the message with the given ANSI color and reset formatting
        print(f"{text_color.value}{message}{ANSIColors.DEFAULT.value}")

    def success(self, message: str, *, timestamp: bool = True) -> None:
        """
        Print a success message with a green background.

        Parameters
        ----------
        message : str
            Success message to print.
        timestamp : bool, optional
            If True, include a timestamp (default is True).

        Returns
        -------
        None
            This method does not return any value.
        """
        # Print the success message with green background and optional timestamp
        self.__printWithBackground(
            "SUCCESS",
            ANSIColors.BG_SUCCESS,
            message,
            timestamp=timestamp,
        )

    def textSuccess(self, message: str) -> None:
        """
        Print a success message in green.

        Parameters
        ----------
        message : str
            Success message to print.

        Returns
        -------
        None
            This method does not return any value.
        """
        # Print the message with success color and reset formatting
        self.__printColored(message, ANSIColors.TEXT_SUCCESS)

    def textSuccessBold(self, message: str) -> None:
        """
        Print a bold success message in green.

        Parameters
        ----------
        message : str
            Success message to print.

        Returns
        -------
        None
            This method does not return any value.
        """
        # Print the message with bold success color and reset formatting
        self.__printColored(message, ANSIColors.TEXT_BOLD_SUCCESS)

    def info(self, message: str, *, timestamp: bool = True) -> None:
        """
        Print an informational message with a blue background.

        Parameters
        ----------
        message : str
            Informational message to print.
        timestamp : bool, optional
            If True, include a timestamp (default is True).

        Returns
        -------
        None
            This method does not return any value.
        """
        # Print the info message with blue background and optional timestamp
        self.__printWithBackground(
            "INFO",
            ANSIColors.BG_INFO,
            message,
            timestamp=timestamp,
        )

    def textInfo(self, message: str) -> None:
        """
        Print an informational message in blue.

        Parameters
        ----------
        message : str
            Informational message to print.

        Returns
        -------
        None
            This method does not return any value.
        """
        # Print the message with informational color and reset formatting
        self.__printColored(message, ANSIColors.TEXT_INFO)

    def textInfoBold(self, message: str) -> None:
        """
        Print a bold informational message in blue.

        Parameters
        ----------
        message : str
            Informational message to print.

        Returns
        -------
        None
            This method does not return any value.
        """
        # Print the message with bold informational color and reset formatting
        self.__printColored(message, ANSIColors.TEXT_BOLD_INFO)

    def warning(self, message: str, *, timestamp: bool = True) -> None:
        """
        Print a warning message with a yellow background.

        Parameters
        ----------
        message : str
            Warning message to print.
        timestamp : bool, optional
            If True, include a timestamp (default is True).

        Returns
        -------
        None
            This method does not return any value.

        Notes
        -----
        Uses ANSI escape codes for warning style.
        """
        # Print the warning message with yellow background and optional timestamp
        self.__printWithBackground(
            "WARNING",
            ANSIColors.BG_WARNING,
            message,
            timestamp=timestamp,
        )

    def textWarning(self, message: str) -> None:
        """
        Print a warning message in yellow.

        Parameters
        ----------
        message : str
            Warning message to print.

        Returns
        -------
        None
            This method does not return any value.

        Notes
        -----
        Uses ANSI escape codes for warning style.
        """
        # Print the message with warning color and reset formatting
        self.__printColored(message, ANSIColors.TEXT_WARNING)

    def textWarningBold(self, message: str) -> None:
        """
        Print a bold warning message in yellow.

        Parameters
        ----------
        message : str
            Warning message to print.

        Returns
        -------
        None
            This method does not return any value.

        Notes
        -----
        Uses ANSI escape codes for bold warning style.
        """
        # Print the message with bold warning color and reset formatting
        self.__printColored(message, ANSIColors.TEXT_BOLD_WARNING)

    def fail(self, message: str, *, timestamp: bool = True) -> None:
        """
        Print a failure message with a red background.

        Parameters
        ----------
        message : str
            Failure message to print.
        timestamp : bool, optional
            If True, include a timestamp (default is True).

        Returns
        -------
        None
            This method does not return any value.

        Notes
        -----
        Uses ANSI escape codes for fail style.
        """
        # Print the failure message with red background and optional timestamp
        self.__printWithBackground(
            "FAIL",
            ANSIColors.BG_FAIL,
            message,
            timestamp=timestamp,
        )

    def error(self, message: str, *, timestamp: bool = True) -> None:
        """
        Print an error message with a red background.

        Parameters
        ----------
        message : str
            Error message to print.
        timestamp : bool, optional
            If True, include a timestamp (default is True).

        Returns
        -------
        None
            This method does not return any value.

        Notes
        -----
        Uses ANSI escape codes for error style.
        """
        # Print the error message with red background and optional timestamp
        self.__printWithBackground(
            "ERROR",
            ANSIColors.BG_ERROR,
            message,
            timestamp=timestamp,
        )

    def textError(self, message: str) -> None:
        """
        Print an error message in red.

        Parameters
        ----------
        message : str
            Error message to print.

        Returns
        -------
        None
            This method does not return any value.

        Notes
        -----
        Uses ANSI escape codes for error style.
        """
        # Print the message with error color and reset formatting
        self.__printColored(message, ANSIColors.TEXT_ERROR)

    def textErrorBold(self, message: str) -> None:
        """
        Print a bold error message in red.

        Parameters
        ----------
        message : str
            Error message to print.

        Returns
        -------
        None
            This method does not return any value.

        Notes
        -----
        Uses ANSI escape codes for bold error style.
        """
        # Print the message with bold error color and reset formatting
        self.__printColored(message, ANSIColors.TEXT_BOLD_ERROR)

    def textMuted(self, message: str) -> None:
        """
        Print a muted (gray) message.

        Parameters
        ----------
        message : str
            Message to print.

        Returns
        -------
        None
            This method does not return any value.

        Notes
        -----
        Uses ANSI escape codes for muted style.
        """
        # Print the message with muted color and reset formatting
        self.__printColored(message, ANSIColors.TEXT_MUTED)

    def textMutedBold(self, message: str) -> None:
        """
        Print a bold muted (gray) message.

        Parameters
        ----------
        message : str
            Message to print.

        Returns
        -------
        None
            This method does not return any value.

        Notes
        -----
        Uses ANSI escape codes for bold muted style.
        """
        # Print the message with bold muted color and reset formatting
        self.__printColored(message, ANSIColors.TEXT_BOLD_MUTED)

    def textUnderline(self, message: str) -> None:
        """
        Print an underlined message.

        Parameters
        ----------
        message : str
            Message to print.

        Returns
        -------
        None
            This method does not return any value.

        Notes
        -----
        Uses ANSI escape codes for underline style.
        """
        # Print the message with underline style and reset formatting
        print(
            f"{ANSIColors.TEXT_STYLE_UNDERLINE.value}{message}"
            f"{ANSIColors.DEFAULT.value}",
        )

    def clear(self) -> None:
        """
        Clear the console screen.

        Notes
        -----
        Emite códigos de escape ANSI para limpiar la pantalla y mover el
        cursor al origen, evitando el overhead de lanzar un subproceso.

        Returns
        -------
        None
            This method does not return any value.
        """
        if sys.stdout.isatty():
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()

    def clearLine(self) -> None:
        """
        Clear the current line in the console.

        Notes
        -----
        Move the cursor to the start of the line and overwrite it with a space.
        Return the cursor to the beginning.

        Returns
        -------
        None
            This method does not return any value.
        """
        # Move cursor to start, overwrite with space, and return to start
        sys.stdout.write("\r \r")
        sys.stdout.flush()

    def line(self) -> None:
        """
        Print a horizontal line in the console.

        Notes
        -----
        Outputs a newline character as a visual separator.

        Returns
        -------
        None
            This method does not return any value.
        """
        # Print a single newline character without advancing to a new line
        print("\n", end="")

    def newLine(self, count: int = 1) -> None:
        """
        Print multiple new lines.

        Parameters
        ----------
        count : int, optional
            Number of new lines to print (default is 1).

        Raises
        ------
        ValueError
            If count is less than or equal to 0.

        Returns
        -------
        None
            This method does not return any value.
        """
        # Validate that count is greater than 0
        if count <= 0:
            error_msg = f"Unsupported Value '{count}'"
            raise ValueError(error_msg)

        # Print the requested number of new lines
        print("\n" * count, end="")

    def write(
        self,
        *values: object,
        sep: str | None = " ",
        end: str | None = "\n",
        file: SupportsWrite[str] | None = None,
        flush: bool = False,
    ) -> None:
        """
        Write values to the output stream and move to the next line.

        Parameters
        ----------
        values : object
            Values to print.
        sep : str | None, optional
            Separator between values. Defaults to " ".
        end : str | None, optional
            String appended after the last value..
        file : SupportsWrite[str] | None, optional
            Output stream. Defaults to sys.stdout.
        flush : bool, optional
            Whether to forcibly flush the stream. Defaults to False.

        Returns
        -------
        None
            This method prints values and returns None.
        """
        # Print values with specified separator, end, file, and flush options
        print(*values, sep=sep, end=end, file=file, flush=flush)

    def writeLine(self, message: str) -> None:
        """
        Print a message and move to the next line.

        Parameters
        ----------
        message : str
            Message to print.

        Returns
        -------
        None
            This method does not return any value.
        """
        # Print the message and move to the next line
        print(message)

    def ask(self, question: str) -> str:
        """
        Prompt user for input and return the response.

        Parameters
        ----------
        question : str
            Message to display to the user.

        Returns
        -------
        str
            User's input as a string.
        """
        # Display the question in info color and get user input
        return input(
            f"{ANSIColors.TEXT_INFO.value}{question.strip()}"
            f"{ANSIColors.DEFAULT.value} ",
        )

    def confirm(self, question: str, *, default: bool = False) -> bool:
        """
        Ask for confirmation and return True or False.

        Parameters
        ----------
        question : str
            Confirmation prompt for the user.
        default : bool, optional
            Default response if user presses Enter. False means 'No'.

        Returns
        -------
        bool
            True if user enters 'Y' or 'YES', False otherwise.
        """
        # Prompt the user for confirmation with info color
        response = input(
            f"{ANSIColors.TEXT_INFO.value}{question.strip()} (Y/n): "
            f"{ANSIColors.DEFAULT.value} ",
        ).upper()

        # Return True for 'Y' or 'YES'; frozenset gives O(1) lookup vs O(n) list
        return default if not response else response in {"Y", "YES"}

    def secret(self, question: str) -> str:
        """
        Prompt for hidden input using the provided question.

        Parameters
        ----------
        question : str
            Prompt message for the user.

        Returns
        -------
        str
            User's hidden input as a string.

        Notes
        -----
        Uses getpass to hide input, suitable for passwords.
        """
        # Prompt the user for hidden input with info color
        prompt = (
            f"{ANSIColors.TEXT_INFO.value}{question.strip()}"
            f"{ANSIColors.DEFAULT.value} "
        )
        return getpass.getpass(prompt)

    def table(self, headers: list, rows: list) -> None:
        """
        Print a formatted table with bold headers and box-drawing borders.

        Parameters
        ----------
        headers : list of str
            Column headers for the table.
        rows : list of list of str
            Table rows, each as a list of column values.

        Raises
        ------
        ValueError
            If headers or rows are empty.

        Returns
        -------
        None
            This method does not return any value.

        Notes
        -----
        Adjust column widths dynamically and use bold for headers.
        """
        # Validate that headers are provided
        if not headers:
            error_msg = "Headers cannot be empty."
            raise ValueError(error_msg)

        # Validate that rows are provided
        if not rows:
            error_msg = "Rows cannot be empty."
            raise ValueError(error_msg)

        # Calculate maximum width for each column
        col_widths = [
            max(len(str(item)) for item in col)
            for col in zip(headers, *rows)
        ]

        # Define table border characters
        top_border = (
            "┌" + "┬".join("─" * (col_width + 2) for col_width in col_widths) + "┐"
        )
        separator = (
            "├" + "┼".join("─" * (col_width + 2) for col_width in col_widths) + "┤"
        )
        bottom_border = (
            "└" + "┴".join("─" * (col_width + 2) for col_width in col_widths) + "┘"
        )

        # Format header row with bold style
        header_row = (
            "│ "
            + " │ ".join(
                f"{ANSIColors.TEXT_BOLD.value}{header:<{col_width}}"
                f"{ANSIColors.DEFAULT.value}"
                for header, col_width in zip(headers, col_widths)
            )
            + " │"
        )

        # Print table borders and header
        print(top_border)
        print(header_row)
        print(separator)

        # Print each row of the table
        for row in rows:
            row_text = (
                "│ "
                + " │ ".join(
                    f"{item!s:<{col_width}}"
                    for item, col_width in zip(row, col_widths)
                )
                + " │"
            )
            print(row_text)

        # Print bottom border
        print(bottom_border)

    def anticipate(self, question: str, options: list, default: None = None) -> str:
        """
        Provide autocomplete suggestions based on user input.

        Parameters
        ----------
        question : str
            Prompt for the user.
        options : list of str
            List of possible autocomplete options.
        default : str, optional
            Default value if no match is found. Defaults to None.

        Returns
        -------
        str
            Chosen option if matched, otherwise default or user input.

        Notes
        -----
        Match the beginning of user input with available options.
        Return the first match, or default/user input if no match.
        """
        # Prompt the user for input with info color
        prompt = (
            f"{ANSIColors.TEXT_INFO.value}{question.strip()}"
            f"{ANSIColors.DEFAULT.value} "
        )
        input_value = input(prompt)

        # Find first option that starts with input_value, or use default/user input
        return next((option for option in options if option.startswith(input_value)),
                    default or input_value)

    def choice(self, question: str, choices: list, default_index: int = 0) -> str:
        """
        Prompt user to select an option from a list.

        Parameters
        ----------
        question : str
            Prompt message for the user.
        choices : list of str
            List of available choices.
        default_index : int, optional
            Index of the default choice (zero-based). Default is 0.

        Returns
        -------
        str
            Selected choice from the list.

        Raises
        ------
        ValueError
            If `choices` is empty or `default_index` is out of range.

        Notes
        -----
        Display a numbered list of choices and prompt the user to select one.
        Re-prompt until a valid selection is made.
        """
        # Validate that choices is not empty
        if not choices:
            error_msg = "The choices list cannot be empty."
            raise ValueError(error_msg)

        # Validate that default_index is within range
        if not (0 <= default_index < len(choices)):
            error_msg = (
                f"Invalid default_index {default_index}. Must be between 0 and "
                f"{len(choices) - 1}."
            )
            raise ValueError(error_msg)

        # Display the question and the choices
        print(
            f"{ANSIColors.TEXT_INFO.value}{question.strip()} "
            f"(default: {choices[default_index]}):{ANSIColors.DEFAULT.value}",
        )

        # Print each choice with its corresponding number
        for idx, choice in enumerate(choices, 1):
            print(
                f"{ANSIColors.TEXT_MUTED.value}{idx}: "
                f"{choice}{ANSIColors.DEFAULT.value}",
            )

        # Prompt the user for input
        answer = input("Answer: ").strip()

        # If the user provides no input, select the default choice
        if not answer:
            return choices[default_index]

        # Validate input: ensure it's a number within range
        while not answer.isdigit() or not (1 <= int(answer) <= len(choices)):
            answer = input("Please select a valid number: ").strip()

        # Cache int conversion: avoids calling int() twice (in loop and in return)
        selected = int(answer)
        return choices[selected - 1]

    def exception(self, exception: Exception) -> None:
        """
        Print exception details and stack trace.

        Parameters
        ----------
        exception : Exception
            Exception to display.

        Notes
        -----
        Shows exception type, message, and stack trace using rich formatting.

        Returns
        -------
        None
            This method does not return any value.
        """
        # Validate that the argument is an Exception instance
        if not isinstance(exception, Exception):
            error_msg = "The provided argument is not an Exception instance."
            raise TypeError(error_msg)

        # Create a rich console for formatted output
        rich_console = RichConsole()

        # Generate a formatted traceback object
        traceback_obj = Traceback.from_exception(
            type(exception),
            exception,
            exception.__traceback__,
            max_frames=1,
            suppress=[],
            extra_lines=1,
            show_locals=False,
        )

        # Print the traceback to the console
        rich_console.print(traceback_obj)

    def exitSuccess(self, message: str | None = None) -> None:
        """
        Exit the program with a success message.

        Parameters
        ----------
        message : str or None, optional
            Success message to print before exiting.

        Returns
        -------
        None
            This method does not return any value.
        """
        # Print success message if provided
        if message:
            self.success(message)

        # Attempt to exit gracefully
        try:
            sys.exit(0)

        # Force exit if SystemExit is caught
        except SystemExit:
            os._exit(0)
            raise

    def exitError(self, message: str| None = None) -> None:
        """
        Exit the program with an error message.

        Parameters
        ----------
        message : str, optional
            Error message to print before exiting.

        Returns
        -------
        None
            This method does not return any value.
        """
        # Print error message if provided
        if message:
            self.error(message)

        # Attempt to exit gracefully
        try:
            sys.exit(1)

        # Force exit if SystemExit is caught
        except SystemExit:
            os._exit(1)
            raise

    def dump(
        self,
        *args: type[Any],
        show_types: bool = True,
        show_index: bool = False,
        expand_all: bool = True,
        max_depth: int | None = None,
        module_path: str | None = None,
        line_number: int | None = None,
        force_exit: bool = False,
        redirect_output: bool = False,
        insert_line: bool = False,
    ) -> None:
        """
        Dump variable information to the console with formatting options.

        Parameters
        ----------
        *args : Any
            Variables to be dumped.
        show_types : bool, optional
            Show variable types (default is True).
        show_index : bool, optional
            Show index for collections (default is False).
        expand_all : bool, optional
            Expand all nested structures (default is True).
        max_depth : int or None, optional
            Maximum depth to expand (default is None).
        module_path : str or None, optional
            Path of the module (default is None).
        line_number : int or None, optional
            Line number for context (default is None).
        force_exit : bool, optional
            Force program exit after dump (default is False).
        redirect_output : bool, optional
            Redirect output to file or stream (default is False).
        insert_line : bool, optional
            Insert a line after output (default is False).

        Returns
        -------
        None
            This method does not return any value.
        """
        # Configure VarDumper with provided options and dump variables
        return VarDumper().showTypes(show=show_types)\
            .showIndex(show=show_index)\
            .expandAll(expand=expand_all)\
            .maxDepth(max_depth)\
            .modulePath(module_path)\
            .lineNumber(line_number)\
            .redirectOutput(redirect=redirect_output)\
            .forceExit(force=force_exit)\
            .values(*args)\
            .print(insert_line=insert_line)

    async def sleep(self, seconds: float) -> None:
        """
        Asynchronously sleep for a specified number of seconds.

        Parameters
        ----------
        seconds : float
            Number of seconds to sleep.

        Returns
        -------
        None
            This method does not return any value.
        """
        # Use asyncio to sleep asynchronously for the given duration
        await asyncio.sleep(seconds)
