from typing import Any
from orionis.console.debug.contracts.dumper import IDumper
from orionis.console.output.var_dumper import VarDumper

class Dumper(IDumper):

    # ruff: noqa: PLR0913

    @staticmethod
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
        Dump variables to the console and terminate execution.

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
        return VarDumper().showTypes(show=show_types)\
            .showIndex(show=show_index)\
            .expandAll(expand=expand_all)\
            .maxDepth(max_depth)\
            .modulePath(module_path)\
            .lineNumber(line_number)\
            .redirectOutput(redirect=redirect_output)\
            .forceExit(force=True)\
            .values(*args)\
            .print(insert_line=insert_line)

    @staticmethod
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
        return VarDumper().showTypes(show=show_types)\
            .showIndex(show=show_index)\
            .expandAll(expand=expand_all)\
            .maxDepth(max_depth)\
            .modulePath(module_path)\
            .lineNumber(line_number)\
            .redirectOutput(redirect=redirect_output)\
            .forceExit(force=False)\
            .values(*args)\
            .print(insert_line=insert_line)
