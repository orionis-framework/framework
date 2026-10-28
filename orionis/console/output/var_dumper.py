from __future__ import annotations
import copy
import inspect
import os
import sys
from html import escape
from io import StringIO
from typing import Any, TextIO, TypeVar
from rich.console import Console
from rich.panel import Panel
from rich.pretty import Pretty
from rich.terminal_theme import TerminalTheme
from rich.theme import Theme
from orionis.console.output.contracts.var_dumper import IVarDumper

T = TypeVar("T")

# Match the diagnostic pages without changing the terminal's palette.
_HTML_TERMINAL_THEME = TerminalTheme(
    (255, 255, 255),
    (24, 36, 51),
    [
        (24, 36, 51),
        (180, 35, 24),
        (20, 118, 109),
        (145, 103, 0),
        (23, 79, 134),
        (121, 83, 168),
        (8, 107, 134),
        (98, 110, 127),
    ],
    [
        (98, 110, 127),
        (180, 35, 24),
        (20, 118, 109),
        (145, 103, 0),
        (32, 107, 196),
        (121, 83, 168),
        (8, 107, 134),
        (24, 36, 51),
    ],
)

_HTML_DUMP_FORMAT = (
    '<pre class="dump-output" tabindex="0" role="region" aria-label="Dumped value" '
    'style="margin:0;padding:16px;overflow:auto;'
    "background-color:var(--orionis-surface,#fff);"
    "color:var(--orionis-text,#182433);"
    "font-family:var(--orionis-mono,'Fira Code','Cascadia Code',Consolas,monospace);"
    'font-size:13px;line-height:1.75;white-space:pre;overflow-wrap:normal;'
    'scrollbar-width:thin"><code style="font:inherit">{code}</code></pre>'
)
_HTML_DUMP_PANEL_FORMAT = (
    '<section class="code-container dump-panel" style="min-width:0;'
    "border:1px solid var(--orionis-border,#dce1e7);"
    "border-radius:var(--orionis-radius,6px);overflow:hidden;"
    "background-color:var(--orionis-surface,#fff);"
    'box-shadow:0 1px 3px rgb(24 36 51 / 4%)">'
    '<div class="code-header" style="display:flex;align-items:center;'
    "justify-content:space-between;flex-wrap:nowrap;gap:12px;padding:12px 16px;"
    "border-bottom:1px solid var(--orionis-border,#dce1e7);"
    "background-color:var(--orionis-soft,#edf3f9);"
    "font-family:var(--orionis-font,'Titillium Web',sans-serif);"
    'font-size:12px">'
    '<span class="code-filename" style="min-width:0;max-width:100%;'
    'overflow-wrap:anywhere;color:var(--orionis-primary-hover,#1a569d);'
    'font-weight:600">{source}</span>'
    '<span class="code-header-info" style="display:flex;align-items:center;'
    'min-width:min-content;'
    "gap:10px;color:var(--orionis-muted,#626e7f);"
    "font-family:var(--orionis-mono,'Fira Code','Cascadia Code',Consolas,monospace);"
    'overflow-wrap:anywhere">{title}</span></div>{code}</section>'
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
        self.__line_number: int | str | None = None

        # HTML capture must not replace the terminal's module header.
        self.__html_module_path: str | None = None
        self.__html_line_number: int | str | None = None

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

    def __resolveCallerInfo(self, *, html: bool = False) -> None: # NOSONAR
        """
        Resolve and set the caller's module path and line number.

        If the internal module path or line number is not set, this method uses
        the inspect module to retrieve the caller's frame and extract the
        relevant information. If the frame is unavailable, it sets default
        values.

        Parameters
        ----------
        html : bool, optional
            Capture the filename separately from the terminal's module name.

        Returns
        -------
        None
            This method does not return any value.
        """
        module_path = self.__html_module_path if html else self.__module_path
        line_number = self.__html_line_number if html else self.__line_number
        if module_path and line_number:
            return

        caller_frame = inspect.currentframe()
        try:
            if caller_frame is not None:
                caller_frame = caller_frame.f_back
                if caller_frame is not None:
                    caller_frame = caller_frame.f_back
            if caller_frame is not None:
                if not module_path:
                    module_path = (
                        caller_frame.f_code.co_filename if html
                        else caller_frame.f_globals.get("__name__", "unknown")
                    )
                if not line_number:
                    line_number = caller_frame.f_lineno
            else:
                module_path = module_path or "unknown"
                line_number = line_number or "?"
        finally:
            del caller_frame

        if html:
            self.__html_module_path = module_path
            self.__html_line_number = line_number
        else:
            self.__module_path = module_path
            self.__line_number = line_number

    def __makeConsole(self, *, file: TextIO | None = None) -> Console:
        """
        Create and return a configured Console instance for output formatting.

        Parameters
        ----------
        file : TextIO or None, optional
            Output stream; None uses the terminal's standard output.

        Returns
        -------
        Console
            A Console object with a custom theme for variable dumping and
            recording enabled.
        """
        # Configure the Console with a custom theme for variable dumping
        return Console(
            file=file,
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

    def __makePretty(self, value: object) -> Pretty:
        """
        Format a value consistently for terminal and HTML output.

        Parameters
        ----------
        value : object
            Stored value to format.

        Returns
        -------
        Pretty
            Value formatted with the configured expansion and depth.
        """
        return Pretty(
            value,
            indent_size=2,
            indent_guides=True,
            expand_all=self.__expand_all,
            max_depth=self.__max_depth,
            margin=1,
            insert_line=True,
        )

    def __makePanel(
        self, value: type[T], _type: str, *, console: Console,
    ) -> Panel:
        """
        Create a Rich Panel with a pretty-printed representation of the value.

        Parameters
        ----------
        value : type[T]
            Object to be pretty-printed inside the panel.
        _type : str
            Type name of the value for display in the panel title.
        console : Console
            Console whose width is used to size the panel.

        Returns
        -------
        Panel
            Rich Panel object displaying the formatted content.

        Notes
        -----
        Uses internal configuration for indentation, expansion, and panel width.
        """
        # Cache attrs as locals: LOAD_FAST vs LOAD_ATTR chain for each access
        show_index = self.__show_index
        show_types = self.__show_types

        # console.size is a property call; cache width once for the panel width calc
        console_width = console.size.width

        # Build the Pretty object with configured formatting options
        pretty_obj = self.__makePretty(value)

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

    def __render(self, console: Console, *, show_header: bool) -> None:
        """
        Render the stored values to the selected console without exiting.

        Parameters
        ----------
        console : Console
            Destination for the formatted output.
        show_header : bool
            Whether to include the caller's module and line.

        Returns
        -------
        None
            Write the formatted values to the selected console.
        """
        if show_header:
            header = (
                f"🐞 [white]Module([/white][bold blue]{self.__module_path}"
                f"[/bold blue][white]) [/white]"
                f"[bright_black]#{self.__line_number}[/bright_black]"
            )
            console.print(header)

        _console_print = console.print
        _make_panel = self.__makePanel
        for item in self.__args:
            _console_print(
                _make_panel(
                    value=item["value"], _type=item["type"], console=console,
                ),
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
        self.__html_module_path = path
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
        self.__html_line_number = number
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
        Print the stored values to the console in a formatted manner.

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

            self.__resolveCallerInfo()
            self.__render(self.__console, show_header=True)

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
        Renders to an isolated in-memory console and exports with a light
        diagnostic palette and native HTML panels with inline styles. Does not
        write to stdout or stderr, redirect streams, or terminate execution,
        regardless of console options. Panel headers show the source filename
        and line, using configured values or the first HTML export's caller.
        HTML source metadata and indices do not affect terminal output.
        """
        self.__resolveCallerInfo(html=True)
        source = escape(f"{self.__html_module_path}:{self.__html_line_number}")
        console = self.__makeConsole(file=StringIO())
        panels: list[str] = []
        for index, item in enumerate(self.__args, start=1):
            if insert_line and index == 1:
                console.print()
            console.print(self.__makePretty(item["value"]))
            if insert_line and index == len(self.__args):
                console.print()
            code = console.export_html(
                theme=_HTML_TERMINAL_THEME,
                code_format=_HTML_DUMP_FORMAT,
                inline_styles=True,
            )
            labels: list[str] = []
            if self.__show_index:
                labels.append(f"#{index}")
            if self.__show_types:
                labels.append(escape(item["type"]))
            panels.append(_HTML_DUMP_PANEL_FORMAT.format(
                source=source,
                title=" &middot; ".join(labels),
                code=code,
            ))
        return (
            '<div class="orionis-dump" style="display:grid;gap:16px;min-width:0">'
            f'{"".join(panels)}</div>'
        )
