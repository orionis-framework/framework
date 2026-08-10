from __future__ import annotations
import copy
import inspect
import os
import sys
from typing import Any, TypeVar
from rich.console import Console
from rich.panel import Panel
from rich.pretty import Pretty
from rich.terminal_theme import TerminalTheme
from rich.theme import Theme
from orionis.console.output.contracts.var_dumper import IVarDumper

T = TypeVar("T")

# Light palette applied only on HTML export; terminal output is untouched.
# Pale ANSI slots (white, bright white) are mapped to dark ink so the dump
# stays legible on a light page background.
_HTML_TERMINAL_THEME = TerminalTheme(
    (247, 248, 250),
    (31, 41, 51),
    [
        (31, 41, 51),
        (176, 32, 48),
        (16, 112, 72),
        (146, 96, 0),
        (28, 84, 176),
        (146, 48, 160),
        (0, 108, 120),
        (85, 96, 110),
    ],
    [
        (108, 118, 132),
        (200, 48, 64),
        (24, 136, 88),
        (168, 112, 0),
        (40, 100, 200),
        (168, 64, 184),
        (0, 128, 140),
        (55, 65, 81),
    ],
)

# Embeddable fragment: light surface so dumps stay legible inside a page.
_HTML_DUMP_FORMAT = (
    '<pre style="margin:0;padding:12px;overflow:auto;'
    "background-color:#f7f8fa;color:#1f2933;"
    "border:1px solid #d9dee5;border-radius:6px;"
    'font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;'
    'font-size:13px;line-height:1.4"><code style="font-family:inherit">'
    "{code}</code></pre>"
)

class VarDumper(IVarDumper):

    # ruff: noqa: T201

    def __init__(self) -> None:
        """
        Initialize the VarDumper instance with default configuration.

        Sets up internal state for variable dumping, including display options,
        output formatting, and argument storage.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Set whether to show types in output
        self.__show_types: bool = True

        # Set whether to show index numbers in output
        self.__show_index: bool = True

        # Set whether to expand all nested structures
        self.__expand_all: bool = True

        # Set the maximum depth for nested structures; None means unlimited
        self.__max_depth: int | None = None

        # Store the module path for display in the header
        self.__module_path: str | None = None

        # Store the line number for display in the header
        self.__line_number: int | None = None

        # Set whether to print the module/line header before the panels
        self.__show_header: bool = True

        # Set whether to force program exit after dumping
        self.__force_exit: bool = False

        # Set whether to redirect output streams during dumping
        self.__redirect_output: bool = False
        self.__redirected_output: bool = False
        self.__original_stdout: Any = None
        self.__original_stderr: Any = None

        # Store the arguments to be dumped
        self.__args: list = []

        # Create a Console instance for output formatting
        self.__console: Console = self.__makeConsole()

        # Initialize the last index for tracking
        self.__last_index: int = 0

    def __forceExit(self) -> None:
        """
        Terminate the program if the force exit flag is set.

        If the internal force exit flag is True, terminate the program using
        os._exit(1) or sys.exit(1) depending on the redirect output flag.

        Returns
        -------
        None
            This method does not return any value.
        """
        # Check if force exit is enabled
        if self.__force_exit:

            # Use os._exit for immediate termination if output is redirected
            if self.__redirect_output:
                os._exit(1)

            # Otherwise, use sys.exit for normal termination
            else:
                sys.exit(1)

    def __resolveCallerInfo(self) -> None:
        """
        Resolve and set the caller's module path and line number.

        If the internal module path or line number is not set, this method uses
        the inspect module to retrieve the caller's frame and extract the
        relevant information. If the frame is unavailable, it sets default
        values.

        Returns
        -------
        None
            This method does not return any value.
        """
        # Only proceed if either module path or line number is missing
        if self.__module_path and self.__line_number:
            return

        # Get the current frame using inspect
        caller_frame = inspect.currentframe()

        # Move back two frames to the caller if possible
        if caller_frame is not None:
            caller_frame = caller_frame.f_back
            if caller_frame is not None:
                caller_frame = caller_frame.f_back

        # If the caller frame exists, extract module and line number
        if caller_frame is not None:
            if not self.__module_path:
                self.__module_path = caller_frame.f_globals.get("__name__", "unknown")
            if not self.__line_number:
                self.__line_number = caller_frame.f_lineno
        else:
            if not self.__module_path:
                self.__module_path = "unknown"
            if not self.__line_number:
                self.__line_number = "?"

    def __makeConsole(self) -> Console:
        """
        Create and return a configured Console instance for output formatting.

        Returns
        -------
        Console
            A Console object with a custom theme for variable dumping and
            recording enabled.
        """
        # Configure the Console with a custom theme for variable dumping
        return Console(
            theme=Theme({
                "dump.index": "bold bright_blue",
                "dump.type": "bold green",
                "dump.rule": "bright_black",
            }),
            record=True,
        )

    def __storeClonedValue(self, value: type[T]) -> None:
        """
        Clone the given value using deep copy and store its type information.

        Parameters
        ----------
        value : type[T]
            Value to be cloned.

        Returns
        -------
        None
            This method does not return a value.

        Notes
        -----
        The type information is obtained from the __name__ attribute of the
        value's type.
        """
        # Append a dictionary containing the deep-copied value
        # and its type name to the args list
        self.__args.append({
            "value": copy.deepcopy(value),
            "type": value.__class__.__name__,
        })

    def __redirectOutput(self) -> None:
        """
        Redirect standard output and error streams temporarily.

        If output redirection is enabled and not already redirected, this method saves
        the current stdout and stderr, then redirects them to the original system
        streams. If already redirected, it restores stdout and stderr to their
        previously saved values.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Redirect output if enabled and not already redirected
        if self.__redirect_output and self.__redirected_output is False:
            self.__original_stdout, self.__original_stderr = sys.stdout, sys.stderr
            sys.stdout, sys.stderr = sys.__stdout__, sys.__stderr__
            self.__redirected_output = True

        # Restore output if it was redirected
        if self.__redirected_output:
            sys.stdout, sys.stderr = self.__original_stdout, self.__original_stderr

    def __printLine(self, *, insert_line: bool = False) -> None:
        """
        Print a blank line to the console if requested.

        Parameters
        ----------
        insert_line : bool, optional
            If True, print a blank line. Default is False.

        Returns
        -------
        None
            This method does not return a value.

        Notes
        -----
        Prints a blank line to the standard output if `insert_line` is True.
        """
        # Print a blank line if requested
        if insert_line:
            print()

    def __makePanel(self, value: type[T], _type: str) -> Panel:
        """
        Create a Rich Panel with a pretty-printed representation of the value.

        Parameters
        ----------
        value : type[T]
            Object to be pretty-printed inside the panel.
        _type : str
            Type name of the value for display in the panel title.

        Returns
        -------
        Panel
            Rich Panel object displaying the formatted content.

        Notes
        -----
        Uses internal configuration for indentation, expansion, and panel width.
        """
        # Cache attrs as locals: LOAD_FAST vs LOAD_ATTR chain for each access
        expand_all = self.__expand_all
        max_depth = self.__max_depth
        show_index = self.__show_index
        show_types = self.__show_types

        # console.size is a property call; cache width once for the panel width calc
        console_width = self.__console.size.width

        # Build the Pretty object with configured formatting options
        pretty_obj = Pretty(
            value,
            indent_size=2,
            indent_guides=True,
            expand_all=expand_all,
            max_depth=max_depth,
            margin=1,
            insert_line=True,
        )

        # Construct the panel title based on settings
        title = None
        if show_index:
            # Increment index for display
            self.__last_index += 1
            title = f"[dump.index]#{self.__last_index}[/dump.index] "
        if show_types:
            if title is None:
                title = ""
            # Add type information to the title
            title += f"[dump.type]{_type}[/dump.type]"

        # Create and return the Panel with the Pretty object and styling
        return Panel(
            pretty_obj,
            title=title,
            title_align="left" if title else None,
            border_style="dump.rule",
            width=min(int(console_width * 0.85), 120),
            padding=(0, 1),
        )

    def showTypes(self, *, show: bool = True) -> VarDumper:
        """
        Set whether to display the type of each argument in the panel title.

        Parameters
        ----------
        show : bool, optional
            If True, display the type of each argument in the panel title.
            Default is True.

        Returns
        -------
        VarDumper
            The current instance with updated show types setting.
        """
        # Validate that the 'show' parameter is a boolean
        if not isinstance(show, bool):
            error_msg = "The 'show' parameter must be of type bool."
            raise TypeError(error_msg)

        # Update the internal flag for showing types
        self.__show_types = show

        # Return the current instance for method chaining
        return self

    def showIndex(self, *, show: bool = True) -> VarDumper:
        """
        Set whether to display an index number for each argument.

        Parameters
        ----------
        show : bool, optional
            If True, show an index number for each argument. Default is True.

        Returns
        -------
        VarDumper
            The current instance with updated show index setting.
        """
        # Validate that the 'show' parameter is a boolean
        if not isinstance(show, bool):
            error_msg = "The 'show' parameter must be of type bool."
            raise TypeError(error_msg)

        # Update the internal flag for showing index
        self.__show_index = show

        # Return the current instance for method chaining
        return self

    def expandAll(self, *, expand: bool = True) -> VarDumper:
        """
        Set whether to expand all nested data structures.

        Parameters
        ----------
        expand : bool, optional
            If True, expands all nested data structures. Default is True.

        Returns
        -------
        VarDumper
            The current instance with updated expand all setting.
        """
        # Validate that the 'expand' parameter is a boolean
        if not isinstance(expand, bool):
            error_msg = "The 'expand' parameter must be of type bool."
            raise TypeError(error_msg)

        # Update the internal flag for expanding all nested structures
        self.__expand_all = expand
        return self

    def maxDepth(self, depth: int | None) -> VarDumper:
        """
        Set the maximum depth for nested structures.

        Parameters
        ----------
        depth : int or None
            Maximum depth for nested structures. None means unlimited.

        Returns
        -------
        VarDumper
            Returns self with updated max depth.

        Raises
        ------
        TypeError
            If 'depth' is not int or None.

        """
        # Check if depth is int or None
        if depth is not None and not isinstance(depth, int):
            error_msg = "The 'depth' parameter must be of type int or None."
            raise TypeError(error_msg)

        # Set the internal max depth value
        self.__max_depth = depth
        return self

    def modulePath(self, path: str | None) -> VarDumper:
        """
        Set the module path to display in the header.

        Parameters
        ----------
        path : str or None
            Module path to display in the header.

        Returns
        -------
        VarDumper
            Returns the current instance with updated module path.

        Raises
        ------
        TypeError
            If 'path' is not of type str or None.
        """
        # Validate that 'path' is a string or None
        if path is not None and not isinstance(path, str):
            error_msg = "The 'path' parameter must be of type str or None."
            raise TypeError(error_msg)

        # Set the internal module path for header display
        self.__module_path = path
        return self

    def lineNumber(self, number: int | None) -> VarDumper:
        """
        Set the line number for header display.

        Parameters
        ----------
        number : int or None
            Line number to display in the header.

        Returns
        -------
        VarDumper
            Returns self with updated line number.

        Raises
        ------
        TypeError
            If 'number' is not of type int or None.
        """
        # Ensure the input is an integer or None
        if number is not None and not isinstance(number, int):
            error_msg = "The 'number' parameter must be of type int or None."
            raise TypeError(error_msg)

        # Update the internal line number for header display
        self.__line_number = number
        return self

    def forceExit(self, *, force: bool = True) -> VarDumper:
        """
        Set whether to terminate the program after dumping.

        Parameters
        ----------
        force : bool, optional
            If True, the program will terminate after dumping. Default is True.

        Returns
        -------
        VarDumper
            Returns the current instance with the updated force exit setting.

        Raises
        ------
        TypeError
            If 'force' is not of type bool.
        """
        # Validate that the 'force' parameter is a boolean
        if not isinstance(force, bool):
            error_msg = "The 'force' parameter must be of type bool."
            raise TypeError(error_msg)

        # Update the internal flag for force exit
        self.__force_exit = force

        # Return the current instance for method chaining
        return self

    def redirectOutput(self, *, redirect: bool = True) -> VarDumper:
        """
        Set whether to temporarily restore stdout/stderr during output.

        Parameters
        ----------
        redirect : bool, optional
            If True, temporarily restores stdout and stderr to their original
            streams during output. Default is True.

        Returns
        -------
        VarDumper
            The current instance with the updated redirect output setting.

        Raises
        ------
        TypeError
            If 'redirect' is not of type bool.
        """
        # Validate that the 'redirect' parameter is a boolean
        if not isinstance(redirect, bool):
            error_msg = "The 'redirect' parameter must be of type bool."
            raise TypeError(error_msg)

        # Update the internal flag for redirecting output
        self.__redirect_output = redirect

        # Return the current instance for method chaining
        return self

    def values(self, *args: tuple | list) -> VarDumper:
        """
        Receive and store multiple values to be dumped.

        Parameters
        ----------
        *args : tuple
            Values to be dumped.

        Returns
        -------
        VarDumper
            Returns the current instance for method chaining.

        Raises
        ------
        TypeError
            If 'args' is not of type tuple or list.
        """
        # Ensure the input is a tuple or list
        if not isinstance(args, (tuple, list)):
            error_msg = "The 'args' parameter must be of type tuple or list."
            raise TypeError(error_msg)

        # Clone and store each value
        for value in args:
            self.__storeClonedValue(value)

        # Return the current instance for method chaining
        return self

    def value(self, value: type[T]) -> VarDumper:
        """
        Add a value to be dumped.

        Parameters
        ----------
        value : type[T]
            The value to be stored for dumping.

        Returns
        -------
        VarDumper
            Returns the current instance for method chaining.

        Notes
        -----
        The value is deep-copied and stored internally for later output.
        """
        # Store a deep-copied version of the value along with its type
        self.__storeClonedValue(value)
        return self

    def print(self, *, insert_line: bool = False) -> None:
        """
        Print the stored values in a formatted manner and return HTML output.

        Optionally inserts a blank line before and after the output, resolves
        caller information, prints a header with module and line details, and
        displays each stored value in a styled panel. Handles optional output
        redirection and program termination.

        Parameters
        ----------
        insert_line : bool, optional
            If True, insert a blank line before and after the output.
            Default is False.

        Returns
        -------
        None
            This method does not return any value.
        """
        # Optionally redirect output to original stdout/stderr
        self.__redirectOutput()

        try:
            # Optionally insert a blank line before the dump output
            self.__printLine(insert_line=insert_line)

            if self.__show_header:

                # Resolve caller information if not already set
                self.__resolveCallerInfo()

                # Print header with module and line information
                header = (
                    f"🐞 [white]Module([/white][bold blue]{self.__module_path}"
                    f"[/bold blue][white]) [/white]"
                    f"[bright_black]#{self.__line_number}[/bright_black]"
                )
                self.__console.print(header)

            # Cache console.print and args list as locals: LOAD_FAST in the loop
            _console_print = self.__console.print
            _make_panel = self.__makePanel

            # Iterate over each argument and display it in a styled panel
            for item in self.__args:
                # Unpack dict values to locals: 2x LOAD_FAST vs 2x dict hash lookup
                _console_print(_make_panel(value=item["value"], _type=item["type"]))

            # Optionally insert a blank line after the dump output
            self.__printLine(insert_line=insert_line)

            # Optionally terminate the program after dumping
            self.__forceExit()

        finally:

            # Restore stdout/stderr if they were redirected
            self.__redirectOutput()

    def toHtml(self, *, insert_line: bool = False) -> str:
        """
        Generate the HTML representation of the dumped output.

        Parameters
        ----------
        insert_line : bool, optional
            If True, insert a blank line before and after the output.
            Default is False.

        Returns
        -------
        str
            HTML fragment containing the formatted dumped output.

        Notes
        -----
        Calls the print method to prepare the output and then exports it
        with a light terminal palette and inline styles, so the dump is
        readable and self-contained when embedded in a page. The module
        and line header is omitted from the HTML output.
        """
        # Print the output to prepare for HTML conversion
        self.__show_header = False
        try:
            self.print(insert_line=insert_line)
        finally:
            self.__show_header = True

        # Export and return the recorded output as HTML
        return self.__console.export_html(
            theme=_HTML_TERMINAL_THEME,
            code_format=_HTML_DUMP_FORMAT,
            inline_styles=True,
        )
