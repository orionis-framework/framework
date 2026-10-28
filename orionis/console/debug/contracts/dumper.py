from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any

class IDumper(ABC):

    # ruff: noqa: PLR0913

    @staticmethod
    @abstractmethod
    def dd(
        *args: tuple[Any],
        show_types: bool = False,
        show_index: bool = False,
        expand_all: bool = True,
        max_depth: int | None = None,
        module_path: str | None = None,
        line_number: int | None = None,
        redirect_output: bool = False,
        insert_line: bool = False,
    ) -> None:
        """
        Dump variables and stop the current execution context.

        Parameters
        ----------
        *args : Any
            Variables to dump.
        show_types : bool, optional
            Whether to show variable types. Default is False.
        show_index : bool, optional
            Whether to show index for each variable. Default is False.
        expand_all : bool, optional
            Whether to expand all nested structures. Default is True.
        max_depth : int or None, optional
            Maximum depth for expansion. Default is None.
        module_path : str or None, optional
            Source path for the header. HTTP defaults to the caller's filename.
        line_number : int or None, optional
            Line number of the call. Default is None.
        redirect_output : bool, optional
            Whether to redirect output. Default is False.
        insert_line : bool, optional
            Whether to insert a separating line before output. Default is False.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        RuntimeError
            If HTTP dumping is attempted outside debug request dispatch.

        Notes
        -----
        Debug HTTP requests receive an HTML response without terminating the
        server. Source filename and line are captured at the dump call, before
        HTTP exception handling. Console calls retain their termination behavior.
        """

    @staticmethod
    @abstractmethod
    def dump(
        *args: tuple[Any],
        show_types: bool = False,
        show_index: bool = False,
        expand_all: bool = True,
        max_depth: int | None = None,
        module_path: str | None = None,
        line_number: int | None = None,
        redirect_output: bool = False,
        insert_line: bool = False,
    ) -> None:
        """
        Dump variables to the console for debugging.

        Parameters
        ----------
        *args : Any
            Variables to dump.
        show_types : bool, optional
            Whether to show variable types. Default is False.
        show_index : bool, optional
            Whether to show index for each variable. Default is False.
        expand_all : bool, optional
            Whether to expand all nested structures. Default is True.
        max_depth : int or None, optional
            Maximum depth for expansion. Default is None.
        module_path : str or None, optional
            Path of the calling module. Default is None.
        line_number : int or None, optional
            Line number of the call. Default is None.
        redirect_output : bool, optional
            Whether to redirect output. Default is False.
        insert_line : bool, optional
            Whether to insert a separating line before output. Default is False.

        Returns
        -------
        None
            This method does not return a value.
        """
