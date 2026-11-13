"""Define the contract for kernel cli implementations."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.foundation.contracts.application import IApplication


class IKernelCLI(ABC):
    """Define the contract for kernel cli implementations."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    @abstractmethod
    async def boot(
        self,
        application: IApplication,
    ) -> None:
        """
        Initialize the kernel CLI and register commands with the reactor.

        Parameters
        ----------
        application : orionis.IApplication
            The application instance used to create the reactor.

        Returns
        -------
        None
            This method does not return a value.
        """

    @abstractmethod
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
