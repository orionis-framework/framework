from __future__ import annotations
from typing import TYPE_CHECKING, ClassVar
from orionis.console.contracts.kernel import IKernelCLI
from orionis.console.core.contracts.reactor import IReactor

if TYPE_CHECKING:
    from orionis.foundation.contracts.application import IApplication

class KernelCLI(IKernelCLI):

    __slots__ = ("__reactor",)

    IGNORE_FLAGS: ClassVar[frozenset[str]] = frozenset({
        "reactor", "-c", "-m", "-", "-i", "-q", "-B", "-O", "-OO", "-v",
        "-vv", "-d", "-x", "-E", "-s", "-S", "-u", "-I", "-W",
    })

    _HELP_FLAGS: ClassVar[frozenset[str]] = frozenset({"help", "--help", "-h"})

    async def boot(
        self,
        application: IApplication,
    ) -> None:
        """
        Initialize the kernel CLI and register commands with the reactor.

        Parameters
        ----------
        application : IApplication
            The application instance used to create the reactor.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Create and assign the reactor instance using the application factory.
        self.__reactor: IReactor = await application.make(IReactor)

    async def handle(self, args: list[str] | None = None) -> int:
        """
        Process and dispatch command line arguments to the appropriate handler.

        Parameters
        ----------
        args : list of str, optional
            List of command line arguments.

        Returns
        -------
        int
            The exit code from the command execution.
        """
        # Validate that args is a list or None
        if args is not None and not isinstance(args, list):
            error_msg = "Arguments must be provided as a list."
            raise TypeError(error_msg)

        # Fallback depuration: drop leading "reactor" prefix
        if args and "reactor" in args[0]:
            del args[0]

        # If no arguments are provided, show help
        if not args:
            return await self.__reactor.call("list")

        # Strip interpreter flags from the front in O(n) — single C-level del
        ignore = self.IGNORE_FLAGS  # cache as local: LOAD_FAST vs LOAD_ATTR
        i = 0
        n = len(args)
        while i < n and args[i] in ignore:
            i += 1
        if i:
            del args[:i]

        # If no command remains after stripping flags, show help
        if not args or args[0] in self._HELP_FLAGS:
            return await self.__reactor.call("list")

        # Dispatch command with remaining arguments
        return await self.__reactor.call(args[0], args[1:])
