from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.console.entities.command import Command
    from orionis.console.fluent.contracts.command import ICommand

class ILoader(ABC):

    @abstractmethod
    async def get(self, signature: str) -> Command | None:
        """
        Retrieve a command instance by its signature.

        Parameters
        ----------
        signature : str
            The unique signature identifying the command.

        Returns
        -------
        Command | None
            The Command instance if found, otherwise None.
        """

    @abstractmethod
    async def all(self) -> dict[str, Command]:
        """
        Return all loaded commands.

        Returns
        -------
        dict[str, Command]
            A dictionary mapping command signatures to Command instances.
        """

    @abstractmethod
    def addFluentCommand(
        self,
        signature: str,
        handler: list[type[Any], str | None],
    ) -> ICommand:
        """
        Define a new command using the fluent interface.

        Create a command with the given signature and handler. The handler must be
        a list containing the class and optionally the method name. Validate input
        types and conventions. Return the created ICommand instance.

        Parameters
        ----------
        signature : str
            Unique identifier for the command.
        handler : list of Any
            List containing the class and optionally the method name.

        Returns
        -------
        ICommand
            The created FluentCommand instance.

        Raises
        ------
        TypeError
            If the signature is not a string or the handler is not a valid list.
        ValueError
            If the signature does not meet naming conventions.
        """

    @abstractmethod
    async def load(self) -> None:
        """
        Load all command classes and their metadata.

        This method loads command metadata from cache if available, otherwise
        discovers core commands, custom commands, and fluent commands. It then
        builds Command instances for each command and populates the internal
        commands dictionary.

        Returns
        -------
        None
            This method populates the internal commands dictionary and does not
            return a value.
        """
