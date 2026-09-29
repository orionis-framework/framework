from __future__ import annotations
from typing import TYPE_CHECKING, Any, Self
from orionis.console.args.argument import Argument
from orionis.console.entities.command import Command as CommandEntity
from orionis.console.fluent.contracts.command import ICommand

if TYPE_CHECKING:
    from collections.abc import Callable

class Command(ICommand):

    def __init__(
        self,
        signature: str,
        concrete: Callable[..., Any],
        method: str = "handle",
    ) -> None:
        """
        Initialize Command instance with signature, concrete class, and method.

        Validate input parameters and set up internal state for command execution.

        Parameters
        ----------
        signature : str
            Command signature for CLI invocation.
        concrete : Callable[..., Any]
            Class implementing command logic.
        method : str, default='handle'
            Method name to execute in concrete class.

        Returns
        -------
        None
            This constructor does not return a value.

        Raises
        ------
        TypeError
            If concrete is not a class or method is not a string.
        AttributeError
            If method does not exist or is not callable in concrete class.
        """
        # Validate that the concrete parameter is a class
        if not callable(concrete):
            error_msg = "The concrete parameter must be a callable class reference."
            raise TypeError(error_msg)

        # Validate that the method parameter is a string
        if not isinstance(method, str):
            error_msg = "The method name must be a string."
            raise TypeError(error_msg)

        # Validate that the specified method exists and is callable
        if not hasattr(concrete, method) or not callable(getattr(concrete, method)):
            error_msg = (
                f"The method '{method}' does not exist or is not callable in the "
                "provided concrete class."
            )
            raise AttributeError(error_msg)

        # Store the command signature
        self.__signature = signature

        # Store the concrete class reference
        self.__concrete = concrete

        # Store the method name
        self.__method = method

        # Enable timestamp display by default
        self.__timestamp = True

        # Set default description
        self.__description = "No description provided."

        # Initialize empty arguments list
        self.__arguments = []

    def timestamp(self, *, enabled: bool = True) -> Self:
        """
        Configure timestamp display for command output.

        Enable or disable timestamps in command results.

        Parameters
        ----------
        enabled : bool, default=True
            Enable or disable timestamp display.

        Returns
        -------
        Command
            Returns self for method chaining.

        Raises
        ------
        TypeError
            If enabled is not a boolean.
        """
        # Validate that enabled is a boolean
        if not isinstance(enabled, bool):
            error_msg = "The timestamp flag must be a boolean value."
            raise TypeError(error_msg)

        # Set the internal timestamp flag
        self.__timestamp = enabled

        # Return self for method chaining
        return self

    def description(self, desc: str) -> Self:
        """
        Set description for the command.

        Assign a descriptive text for help and documentation.

        Parameters
        ----------
        desc : str
            Description text for the command.

        Returns
        -------
        Command
            Returns self for method chaining.

        Raises
        ------
        TypeError
            If desc is not a string.
        """
        # Validate that desc is a string
        if not isinstance(desc, str):
            error_msg = "The description must be a string."
            raise TypeError(error_msg)

        # Set the internal description attribute
        self.__description = desc

        # Return self for method chaining
        return self

    def arguments(self, args: list[Argument]) -> Self:
        """
        Set CLI arguments for the command.

        Configure accepted command-line arguments.

        Parameters
        ----------
        args : list
            List of Argument instances.

        Returns
        -------
        Command
            Returns self for method chaining.

        Raises
        ------
        TypeError
            If args is not a list or contains non-Argument elements.
        """
        # Validate that args is a list
        if not isinstance(args, list):
            error_msg = "Arguments must be provided as a list."
            raise TypeError(error_msg)

        # Validate that each argument is a Argument instance
        for arg in args:
            if not isinstance(arg, Argument):
                error_msg = "All arguments must be instances of Argument."
                raise TypeError(error_msg)

        # Set the internal arguments list
        self.__arguments = args

        # Return self for method chaining
        return self

    def get(self) -> tuple[str, CommandEntity]:
        """
        Retrieve configured Command entity.

        Construct and return CommandEntity with all configuration.

        Returns
        -------
        tuple of (str, CommandEntity)
            Command signature and CommandEntity instance.
        """
        # Create and return a CommandEntity with configured properties
        return self.__signature, CommandEntity(
            obj=self.__concrete,
            method=self.__method,
            timestamps=self.__timestamp,
            signature=self.__signature,
            description=self.__description,
            args=self.__arguments,
        )
