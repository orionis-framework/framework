from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from _typeshed import SupportsWrite
    from orionis.console.dynamic.contracts.progress_bar import IProgressBar

class IConsole(ABC):

    # ruff: noqa: PLR0913

    @property
    @abstractmethod
    def progressBar(self) -> IProgressBar:
        """
        Get a new instance of the ProgressBar class.

        Returns
        -------
        IProgressBar
            A new instance of the ProgressBar class.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def write(
        self,
        *values: object,
        sep: str | None = " ",
        end: str | None = "\n",
        file: SupportsWrite[str] | None = None,
        flush: bool = False,
    ) -> None:
        r"""
        Write values to the output stream and move to the next line.

        Parameters
        ----------
        values : object
            Values to print.
        sep : str | None, optional
            Separator between values. Defaults to " ".
        end : str | None, optional
            String appended after the last value. Defaults to "\n".
        file : SupportsWrite[str] | None, optional
            Output stream. Defaults to sys.stdout.
        flush : bool, optional
            Whether to forcibly flush the stream. Defaults to False.

        Returns
        -------
        None
            This method prints values and returns None.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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
