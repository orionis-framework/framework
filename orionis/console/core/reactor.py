import argparse
import operator
import sys
from typing import Any
from orionis.console.base.contracts.command import IBaseCommand
from orionis.console.core.loader import Loader
from orionis.console.core.contracts.reactor import IReactor
from orionis.console.entities.command import Command
from orionis.console.fluent.contracts.command import ICommand
from orionis.console.output.executor import Executor
from orionis.console.output.help_command import HelpCommand
from orionis.failure.contracts.catch import ICatch
from orionis.failure.enums.kernel_type import KernelContext
from orionis.foundation.contracts.application import IApplication
from orionis.logging.contracts.logger import ILogger
from orionis.support.performance.counter import PerformanceCounter
from orionis.support.types.sentinel import MISSING

class Reactor(IReactor):

    # ruff: noqa: PLR0913, SLF001, BLE001,TRY400, TC001, C901

    def __init__(
        self,
        app: IApplication,
        loader: Loader,
        executer: Executor,
        logger: ILogger,
        catch: ICatch,
        performance_counter: PerformanceCounter,
    ) -> None:
        """
        Initialize Reactor instance for command discovery and management.

        Set up the command processing environment, establish the application context,
        and initialize internal registries for command lookup and execution.

        Parameters
        ----------
        app : IApplication
            Application instance for command processing.

        Returns
        -------
        None
            This constructor does not return any value.
        """
        # Set the application instance for command processing
        self.__app = app

        # Initialize the list for fluent command definitions
        self.__loader = loader

        # Initialize the executor for command output management
        self.__executer = executer

        # Initialize the logger service for logging command execution details
        self.__logger = logger

        # Initialize the performance counter for measuring command execution time
        self.__performance_counter = performance_counter

        # Store the catch instance for exception handling
        self.__catch = catch

        # Initialize cache for command information
        self.__cache_info: list[dict] | None = None

    def __parseCommandArgs(
        self,
        command: Command,
        args: list[str] | None = None,
    ) -> dict:
        """
        Parse command-line arguments for a command using its ArgumentParser.

        Parameters
        ----------
        command : Command
            Command object containing the argument parser and metadata.
        args : Optional[list[str]], default None
            List of command-line arguments to parse. If None, an empty list is used.

        Returns
        -------
        dict
            Dictionary with parsed argument names and values. Returns an empty dict
            if no arguments are expected or provided.

        Raises
        ------
        SystemExit
            Raised by argparse if argument parsing fails or help is requested.
        RuntimeError
            Raised if argument parsing fails for reasons other than SystemExit.
        """
        # Initialize parsed_args to None
        parsed_args = None

        # Parse arguments only if the command expects them and has an ArgumentParser
        if (
            command.args is not None and
            isinstance(command.args, argparse.ArgumentParser)
        ):

            # Use an empty list if no arguments are provided
            if args is None:
                args = []

            # Try to parse the provided arguments using the command's ArgumentParser
            try:

                # Parse the arguments and store the result in parsed_args
                parsed_args = command.args.parse_args(args)

            except SystemExit as e:

                # Print help information for the command when argparse raises
                # SystemExit, which occurs on parsing errors or when help is requested
                HelpCommand.printActions(
                    command.signature,
                    command.args._actions,
                    is_error=e.code != 0,
                )

                # If the exit code is non-zero,
                # it indicates an error in argument parsing
                if e.code != 0:
                    self.__executer.fail(program=command.signature, time="0s")
                    sys.exit(e.code)

                # Exit with success code if help was requested
                sys.exit(0)

        # Convert parsed_args to dict if necessary
        if isinstance(parsed_args, argparse.Namespace):
            args = vars(parsed_args)
        elif isinstance(parsed_args, dict):
            args = parsed_args
        else:
            args = {}

        # Filter out any arguments that were not provided (those with value MISSING)
        return {k: v for k, v in args.items() if v is not MISSING}

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
        # Normalize handler to list format and register with loader
        normalized_handler = (
            handler if isinstance(handler, list)
            else [handler, "__call__"]
        )
        return self.__loader.addFluentCommand(signature, normalized_handler)

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
        # None = not yet built; [] = empty but valid
        if self.__cache_info is not None:
            return self.__cache_info

        # Prepare a list to hold command information
        commands_info = []

        # Ensure all commands are loaded before retrieving their information
        all_commands: dict[str, Command] = await self.__loader.all()

        # Iterate through all registered commands in the internal registry
        for command in all_commands.values():

            # Skip internal commands (those with double underscores)
            if command.signature.startswith("__") and command.signature.endswith("__"):
                continue

            # Append command information to the list
            commands_info.append({
                "timestamps": command.timestamps,
                "signature": command.signature,
                "description": command.description,
                "arguments" : command.args,
                "object": command.obj,
                "method": command.method,
            })

        # Return the sorted list of command information by signature
        # operator.itemgetter runs at C level, faster than a Python lambda
        self.__cache_info = sorted(commands_info, key=operator.itemgetter("signature"))
        return self.__cache_info

    async def call( # NOSONAR
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
        # Create a new scope for the command execution context
        async with self.__app.beginScope() as scope:

            # Set the kernel type in the scope for contextual awareness
            # during command execution
            scope.set("kernel", KernelContext.CONSOLE)

            # Start execution timer for performance measurement
            await self.__performance_counter.astart()

            # Initialize a variable to track whether timestamps should be logged
            timestamps = False

            # Initialize command to None so the except block can safely reference it
            command = None

            # Initialize a variable to hold the target class name for logging purposes
            target_class : str | None = None
            target_method : str | None = None

            try:

                # Validate that the command signature is a string
                if not isinstance(signature, str):
                    error_msg = "Command signature must be a string."
                    raise TypeError(error_msg)

                # Validate that the command signature is not empty
                if not signature:
                    error_msg = "Command signature cannot be empty."
                    raise ValueError(error_msg)

                # Retrieve the command from the registry by its signature
                command = await self.__loader.get(signature)
                if command is None:
                    error_msg = f"Command '{signature}' not found."
                    raise ValueError(error_msg)

                # Determine if timestamps should be logged based
                # on command settings and help flags
                # Evaluate (args or []) once to avoid creating two temporary lists
                _safe_args = args or []
                timestamps = (
                    command.timestamps and
                    "-h" not in _safe_args and
                    "--help" not in _safe_args
                )

                # Log the command execution start if timestamps are enabled
                if timestamps:
                    self.__executer.running(program=signature)

                # Parse and deep copy the arguments to avoid side effects
                dict_args = self.__parseCommandArgs(command, args)

                # Initialize the instance using the application container
                instance = await self.__app.build(command.obj)
                target_class = instance.__class__.__name__
                target_method = command.method

                # If the command object is not an instance of IBaseCommand,
                if not isinstance(instance, IBaseCommand):

                    # Call the specified method on the instance with parsed arguments
                    result = await self.__app.call(
                        instance, command.method, **dict_args,
                    )

                # If the instance implements the IBaseCommand interface,
                elif isinstance(instance, IBaseCommand):

                    # Inject the parsed arguments into the instance for use
                    # in command execution
                    instance.setArguments(dict_args)

                    # Execute the command's handle method and capture its output
                    result = await self.__app.call(instance, command.method)

                # Stop the timer and log completion if timestamps are enabled
                await self.__performance_counter.astop()
                elapsed_time = round(await self.__performance_counter.agetSeconds(), 2)
                if timestamps:
                    self.__executer.done(program=signature, time=f"{elapsed_time}s")

                # Log successful execution
                info_msg = (
                    f"Command '{signature}' executed successfully in "
                    f"({elapsed_time}) seconds."
                )
                self.__logger.info(info_msg)

                # Return the result of the command execution, ensuring
                # it is an integer exit code
                if isinstance(result, int):
                    return result
                return 0

            except Exception as e:

                # Log the error in the logger service
                error_msg = f"Command '{signature}' execution failed: {e}"
                self.__logger.error(error_msg)

                # Stop the timer and log failure if timestamps are enabled
                await self.__performance_counter.astop()
                elapsed_time = round(await self.__performance_counter.agetSeconds(), 2)
                if command and command.timestamps:
                    self.__executer.fail(program=signature, time=f"{elapsed_time}s")

                # Delegate exception handling to the catch service
                if target_class and target_method:
                    e.args = (f"[{target_class}.{target_method}] {e}",)
                await self.__catch.exception(e)

                # Return a failure code
                return 1
