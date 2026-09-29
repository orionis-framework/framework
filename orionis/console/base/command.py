from __future__ import annotations
from typing import TYPE_CHECKING, Any, ClassVar
from orionis.console.base.contracts.command import IBaseCommand
from orionis.console.output.console import Console

# Sentinel object to distinguish between missing keys and keys with None values
_MISSING = object()

if TYPE_CHECKING:
    from orionis.console.args.argument import Argument

class BaseCommand(Console, IBaseCommand):

    # ruff: noqa: ANN401

    # Enable timestamps in console output by default
    timestamps: bool = True

    # Command signature string for registration and help text generation
    signature: str

    # Human-readable description for documentation and help display
    description: str

    # List of Argument instances defining command-line options and arguments
    arguments: ClassVar[list[Argument]] = []

    def __init__(self) -> None:
        """
        Initialize the BaseCommand instance.

        Calls the superclass initializer and sets up the internal argument
        storage.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Initialize internal argument storage for parsed CLI arguments
        self.__arguments__: dict[str, Any] = {}

    async def handle(self) -> None:
        """
        Run the main logic for the command.

        This method must be implemented by subclasses to define the command's
        behavior. It is called after argument parsing and validation.

        Returns
        -------
        None
            No value is returned. Output should be handled via console methods.

        Raises
        ------
        NotImplementedError
            Raised if not implemented in a subclass.
        """
        error_msg = "The 'handle' method must be implemented in the subclass."
        raise NotImplementedError(error_msg)

    def getArgument(self, key: str, default: Any | None = None) -> Any | None:
        """
        Retrieve the value of a command-line argument.

        Parameters
        ----------
        key : str
            The name of the argument to retrieve.
        default : Any or None, optional
            The value to return if the argument is not present. Defaults to None.

        Returns
        -------
        Any or None
            The value of the argument if present, otherwise the default value.
        """
        # Validate that the key is a string
        if not isinstance(key, str):
            error_msg = "Argument key must be a string."
            raise TypeError(error_msg)

        # Single dict lookup; local var avoids repeated LOAD_ATTR on self.__arguments__
        args = self.__arguments__
        value = args.get(key, _MISSING)
        return default if value is _MISSING else value

    def getArguments(self) -> dict[str, Any]:
        """
        Retrieve all parsed command-line arguments.

        Returns
        -------
        dict[str, Any]
            A copy of the dictionary containing all parsed arguments.
        """
        # Return a shallow copy to prevent external modification
        return self.__arguments__.copy()

    def setArguments(self, args: dict[str, Any]) -> None:
        """
        Set the internal arguments dictionary with the provided arguments.

        Parameters
        ----------
        args : dict[str, Any]
            Dictionary containing parsed command-line arguments.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        TypeError
            If the provided arguments are not a dictionary.
        """
        # Ensure the input is a dictionary of arguments
        if not isinstance(args, dict):
            error_msg = "Arguments must be provided as a dictionary."
            raise TypeError(error_msg)

        # Store the parsed arguments in the internal state for later retrieval
        if not hasattr(self, "__arguments__"):
            self.__arguments__ = {}

        # Update the internal arguments dictionary with the provided arguments
        self.__arguments__.update(args)
