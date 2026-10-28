import inspect
from typing import Any
from orionis.console.debug.contracts.dumper import IDumper
from orionis.console.output.var_dumper import VarDumper
from orionis.container.context.manager import ScopeManager
from orionis.container.context.scope import ScopedContext
from orionis.failure.enums.kernel_type import KernelContext

class HttpDump(RuntimeError):
    """Carry a snapshot that only the debug HTTP error boundary may render."""

    __slots__ = ("dumper", "insert_line")

    def __init__(self, dumper: VarDumper, *, insert_line: bool = False) -> None:
        """
        Prepare a lazy dump that fails safely outside HTTP error handling.

        Parameters
        ----------
        dumper : VarDumper
            Configured dumper containing the cloned values.
        insert_line : bool, optional
            Whether the rendered fragment includes separating lines.

        Returns
        -------
        None
            Initialize the request interruption.
        """
        super().__init__(
            "HTTP variable dumping is only available during debug "
            "request dispatch.",
        )
        self.dumper = dumper
        self.insert_line = insert_line

class Dumper(IDumper):
    """Implement synchronous dumping independently of application boot.

    Use ``orionis.support.facades.Debug`` after boot to access the registered
    service through the container. Direct calls remain available for standalone
    scripts and debugging during application initialization.
    """

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
        During debug HTTP dispatch, the kernel sends the HTML dump and stops
        only the current request. The source filename and line are captured
        before unwinding to the renderer. Outside HTTP, print to the console
        and terminate the process as configured.
        """
        scope = ScopedContext.getCurrentScope()
        http_context = (
            isinstance(scope, ScopeManager)
            and scope.isActive
            and scope["kernel"] is KernelContext.HTTP
        )

        if http_context and (module_path is None or line_number is None):
            caller_frame = inspect.currentframe()
            try:
                if caller_frame is not None:
                    caller_frame = caller_frame.f_back
                if caller_frame is not None:
                    if module_path is None:
                        module_path = caller_frame.f_code.co_filename
                    if line_number is None:
                        line_number = caller_frame.f_lineno
            finally:
                del caller_frame

        dumper = VarDumper().showTypes(show=show_types)\
            .showIndex(show=show_index)\
            .expandAll(expand=expand_all)\
            .maxDepth(max_depth)\
            .modulePath(module_path)\
            .lineNumber(line_number)\
            .redirectOutput(redirect=redirect_output)\
            .values(*args)

        if http_context:
            raise HttpDump(dumper, insert_line=insert_line)

        return dumper.forceExit(force=True)\
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
