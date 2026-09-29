from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from orionis.console.fluent.contracts.command import ICommand

class IReactor(ABC):

    @abstractmethod
    def command(
        self,
        signature: str,
        handler: list[type[Any] | str | None] | str,
    ) -> ICommand:
        """
        Register a fluent command with the given signature and handler.

        Parameters
        ----------
        signature : str
            Command signature to register.
        handler : list[type[Any] | str | None] | str
            Handler class and optional method name.

        Returns
        -------
        ICommand
            The registered command instance.
        """

    @abstractmethod
    async def info(self) -> list[dict]:
        """
        Return registered commands metadata.

        Retrieve all loaded commands from the internal registry, skipping internal
        commands (those with double underscores). Each command is represented as a
        dictionary containing its signature and description.

        Returns
        -------
        list of dict
            List of dictionaries with 'signature' and 'description' for each command.
        """

    @abstractmethod
    async def call(
        self,
        signature: str,
        args: list[str] | None = None,
    ) -> int:
        """
        Execute a registered command by its signature.

        Parameters
        ----------
        signature : str
            Command signature to execute.
        args : list of str or None, optional
            Arguments to pass to the command.

        Returns
        -------
        int
            The output produced by the command execution.

        Raises
        ------
        ValueError
            If the command is not found.
        Exception
            If command execution fails.
        """
