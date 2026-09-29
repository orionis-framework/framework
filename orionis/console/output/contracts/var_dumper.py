from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TypeVar

T = TypeVar("T")

class IVarDumper(ABC):

    @abstractmethod
    def showTypes(self, *, show: bool = True) -> IVarDumper:
        """
        Set whether to display the type of each argument in the panel title.

        Parameters
        ----------
        show : bool, optional
            If True, display the type of each argument in the panel title.
            Default is True.

        Returns
        -------
        IVarDumper
            The current instance with updated show types setting.
        """

    @abstractmethod
    def showIndex(self, *, show: bool = True) -> IVarDumper:
        """
        Set whether to display an index number for each argument.

        Parameters
        ----------
        show : bool, optional
            If True, show an index number for each argument. Default is True.

        Returns
        -------
        IVarDumper
            The current instance with updated show index setting.
        """

    @abstractmethod
    def expandAll(self, *, expand: bool = True) -> IVarDumper:
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

    @abstractmethod
    def maxDepth(self, depth: int | None) -> IVarDumper:
        """
        Set the maximum depth for nested structures.

        Parameters
        ----------
        depth : int or None
            Maximum depth for nested structures. None means unlimited.

        Returns
        -------
        IVarDumper
            Returns self with updated max depth.

        Raises
        ------
        TypeError
            If 'depth' is not int or None.

        """

    @abstractmethod
    def modulePath(self, path: str | None) -> IVarDumper:
        """
        Set the module path to display in the header.

        Parameters
        ----------
        path : str or None
            Module path to display in the header.

        Returns
        -------
        IVarDumper
            Returns the current instance with updated module path.

        Raises
        ------
        TypeError
            If 'path' is not of type str or None.
        """

    @abstractmethod
    def lineNumber(self, number: int | None) -> IVarDumper:
        """
        Set the line number for header display.

        Parameters
        ----------
        number : int or None
            Line number to display in the header.

        Returns
        -------
        IVarDumper
            Returns self with updated line number.

        Raises
        ------
        TypeError
            If 'number' is not of type int or None.
        """

    @abstractmethod
    def forceExit(self, *, force: bool = True) -> IVarDumper:
        """
        Set whether to terminate the program after dumping.

        Parameters
        ----------
        force : bool, optional
            If True, the program will terminate after dumping. Default is True.

        Returns
        -------
        IVarDumper
            Returns the current instance with the updated force exit setting.

        Raises
        ------
        TypeError
            If 'force' is not of type bool.
        """

    @abstractmethod
    def redirectOutput(self, *, redirect: bool = True) -> IVarDumper:
        """
        Set whether to temporarily restore stdout/stderr during output.

        Parameters
        ----------
        redirect : bool, optional
            If True, temporarily restores stdout and stderr to their original
            streams during output. Default is True.

        Returns
        -------
        IVarDumper
            The current instance with the updated redirect output setting.

        Raises
        ------
        TypeError
            If 'redirect' is not of type bool.
        """

    @abstractmethod
    def values(self, *args: tuple | list) -> IVarDumper:
        """
        Receive and store multiple values to be dumped.

        Parameters
        ----------
        *args : tuple
            Values to be dumped.

        Returns
        -------
        IVarDumper
            Returns the current instance for method chaining.

        Raises
        ------
        TypeError
            If 'args' is not of type tuple or list.
        """

    @abstractmethod
    def value(self, value: type[T]) -> IVarDumper:
        """
        Add a value to be dumped.

        Parameters
        ----------
        value : type[T]
            The value to be stored for dumping.

        Returns
        -------
        IVarDumper
            Returns the current instance for method chaining.

        Notes
        -----
        The value is deep-copied and stored internally for later output.
        """

    @abstractmethod
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

    @abstractmethod
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
            HTML string containing the formatted dumped output.

        Notes
        -----
        Calls the print method to prepare the output and then exports it as HTML.
        """
