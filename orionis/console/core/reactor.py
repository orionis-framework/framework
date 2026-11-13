# ruff: noqa: BLE001, C901, PLR0912, PLR0913, PLR0915, SLF001, TC001, TRY400
# Keep runtime reflection annotations and intentionally deferred imports.
# Keep established public and external protocol names and signatures.
# Preserve error ownership, cleanup, and non-recursive failure reporting.
"""Resolve and execute registered console commands."""

import argparse
import operator
import sys
from typing import Any
from orionis.console.base.contracts.command import IBaseCommand
from orionis.console.core.contracts.reactor import IReactor
from orionis.console.core.loader import Loader
from orionis.console.entities.command import Command
from orionis.console.fluent.contracts.command import ICommand
from orionis.console.output.executor import Executor
from orionis.console.output.help_command import HelpCommand
from orionis.failure.contracts.catch import ICatch
from orionis.failure.enums.kernel_type import KernelContext
from orionis.failure.runtime import capture, capture_result, operation
from orionis.foundation.contracts.application import IApplication
from orionis.logging.contracts.logger import ILogger
from orionis.support.performance.counter import PerformanceCounter
from orionis.support.types.sentinel import MISSING


class Reactor(IReactor):
    """Resolve and execute registered console commands."""

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
        Initialize the command dispatcher and its services.

        Parameters
        ----------
        app : orionis.foundation.contracts.application.IApplication
            Application container used to resolve and invoke command handlers.
        loader : orionis.console.core.loader.Loader
            Loader used to register and discover commands.
        executer : orionis.console.output.executor.Executor
            Output service used to display command execution status.
        logger : orionis.logging.contracts.logger.ILogger
            Logger used to record command outcomes.
        catch : orionis.failure.contracts.catch.ICatch
            Exception handler used to present command failures.
        performance_counter : orionis.support.performance.counter.PerformanceCounter
            Timer used to measure command execution.

        Returns
        -------
        None
            Initialize the dispatcher with an empty metadata cache.
        """
        # Set the application instance for command processing
        self.__app = app
        """Application instance for command processing."""

        # Initialize the list for fluent command definitions
        self.__loader = loader
        """Loader instance for managing command loading."""

        # Initialize the executor for command output management
        self.__executer = executer
        """Executor instance for managing command output."""

        # Initialize the logger service for logging command execution details
        self.__logger = logger
        """Logger instance for logging command execution details."""

        # Initialize the performance counter for measuring command execution time
        self.__performance_counter = performance_counter
        """PerformanceCounter instance for measuring command execution time."""

        # Store the catch instance for exception handling
        self.__catch = catch
        """Catch instance for handling exceptions."""

        # Initialize cache for command information
        self.__cache_info: list[dict] | None = None
        """Initialize cache for command information."""

    def __parseCommandArgs(
        self,
        command: Command,
        args: list[str] | None = None,
    ) -> dict:
        """
        Parse command arguments and omit values marked as missing.

        Parameters
        ----------
        command : orionis.console.entities.command.Command
            Command whose argument parser supplies the parsed values.
        args : list[str] or None, optional
            Command-line tokens to parse; use an empty list when ``None``.

        Returns
        -------
        dict
            Parsed arguments without ``MISSING`` values, or an empty dictionary
            when the command has no argument parser.

        Raises
        ------
        SystemExit
            If argument parsing fails or help is requested.
        """
        # Initialize parsed_args to None
        parsed_args = None

        # Parse arguments only if the command expects them and has an ArgumentParser
        if command.args is not None and isinstance(
            command.args,
            argparse.ArgumentParser,
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
        Register a command and return its fluent configuration.

        Parameters
        ----------
        signature : str
            Signature used to identify the command.
        handler : list[type[typing.Any] | str | None] | str
            Handler definition forwarded to the loader; default the method to
            ``__call__`` when omitted.

        Returns
        -------
        orionis.console.fluent.contracts.command.ICommand
            Fluent command definition for further configuration.

        Raises
        ------
        TypeError
            If the handler class or method name has an invalid type.
        ValueError
            If the handler list is empty.
        AttributeError
            If the handler method is missing or not callable.
        """
        # Normalize handler to list format and register with loader
        normalized_handler = (
            handler if isinstance(handler, list) else [handler, "__call__"]
        )
        return self.__loader.addFluentCommand(signature, normalized_handler)

    async def hasCommand(self, signature: str) -> bool:
        """
        Check whether a command signature is registered.

        Parameters
        ----------
        signature : str
            Signature of the command to locate.

        Returns
        -------
        bool
            ``True`` if the loader finds the command, otherwise ``False``.
        """
        return await self.__loader.get(signature) is not None

    async def info(self) -> list[dict]:
        """
        Return cached metadata for non-internal commands.

        Exclude signatures enclosed in double underscores and cache the result
        after the first lookup.

        Returns
        -------
        list[dict]
            Dictionaries containing ``timestamps``, ``signature``, ``description``,
            ``arguments``, ``object``, and ``method``, sorted by signature.
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
            commands_info.append(
                {
                    "timestamps": command.timestamps,
                    "signature": command.signature,
                    "description": command.description,
                    "arguments": command.args,
                    "object": command.obj,
                    "method": command.method,
                },
            )

        # Return the sorted list of command information by signature
        # Sort command metadata by its signature.
        self.__cache_info = sorted(commands_info, key=operator.itemgetter("signature"))
        return self.__cache_info

    async def call(
        self,
        signature: str,
        args: list[str] | None = None,
    ) -> int:
        """
        Execute a command in an isolated failure-reporting context.

        Parameters
        ----------
        signature : str
            Registered command signature to execute.
        args : list[str] or None, optional
            Command-line tokens to parse; use an empty list when ``None``.

        Returns
        -------
        int
            Handler exit code, ``0`` for non-integer results, or ``1`` for
            failures handled during dispatch.

        Raises
        ------
        SystemExit
            If argument parsing fails or command help is requested.
        Exception
            If dispatch or failure reporting raises an unhandled error.
        """
        with operation(self.__app, flow="console", operation=signature, isolated=True):
            try:
                return await self.__call(signature, args)
            except Exception as error:
                await capture(
                    error,
                    app=self.__app,
                    flow="console",
                    phase="dispatch",
                )
                raise

    async def __call(  # NOSONAR
        self,
        signature: str,
        args: list[str] | None = None,
    ) -> int:
        """
        Execute a command within a scoped application context.

        Parse arguments, resolve the handler, and report execution status and
        handled failures.

        Parameters
        ----------
        signature : str
            Registered command signature to execute.
        args : list[str] or None, optional
            Command-line tokens to parse; use an empty list when ``None``.

        Returns
        -------
        int
            Handler exit code, ``0`` for non-integer results, or ``1`` after
            handling a dispatch or execution error.

        Raises
        ------
        SystemExit
            If argument parsing fails or command help is requested.
        Exception
            If scope management, initial timing, or failure reporting fails.
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
            target_class: str | None = None
            target_method: str | None = None

            try:
                # Validate that the command signature is a string
                if not isinstance(signature, str):
                    error_msg: str = "Command signature must be a string."
                    raise TypeError(error_msg)

                # Validate that the command signature is not empty
                if not signature:
                    error_msg: str = "Command signature cannot be empty."
                    raise ValueError(error_msg)

                # Retrieve the command from the registry by its signature
                command = await self.__loader.get(signature)
                if command is None:
                    error_msg: str = f"Command '{signature}' not found."
                    raise ValueError(error_msg)

                # Retire launcher feedback before command code can write through
                # native file descriptors, child processes, or interactive tools.
                # Only launchers load feedback; programmatic dispatch does not
                # introduce its imports into HTTP or scheduler runtimes.
                feedback = sys.modules.get("orionis.console.startup")
                if feedback is not None:
                    feedback.stop_startup_feedback()

                # Determine if timestamps should be logged based
                # on command settings and help flags
                # Use an empty argument sequence when none was provided.
                _safe_args = args or []
                timestamps = (
                    command.timestamps
                    and "-h" not in _safe_args
                    and "--help" not in _safe_args
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
                        instance,
                        command.method,
                        **dict_args,
                    )

                # If the instance implements the IBaseCommand interface,
                else:
                    # Inject the parsed arguments into the instance for use
                    # in command execution
                    instance.setArguments(dict_args)

                    # Execute the command's handle method and capture its output
                    result = await self.__app.call(instance, command.method)

                # Stop the timer and log completion if timestamps are enabled
                await self.__performance_counter.astop()
                elapsed_time = round(await self.__performance_counter.agetSeconds(), 2)
                exit_code = result if isinstance(result, int) else 0
                if exit_code != 0:
                    if timestamps:
                        self.__executer.fail(program=signature, time=f"{elapsed_time}s")
                    receipt = await capture_result(
                        exit_code,
                        app=self.__app,
                        flow="console",
                        phase="result",
                        operation=signature,
                    )
                    if receipt is None:
                        error_message = (
                            f"Command '{signature}' failed with exit code {exit_code} "
                            f"in ({elapsed_time}) seconds."
                        )
                        self.__logger.error(error_message)
                    return exit_code
                if timestamps:
                    self.__executer.done(program=signature, time=f"{elapsed_time}s")

                # Record completed commands without recreating cleared log files.
                if signature != "clear:logs":
                    info_msg = (
                        f"Command '{signature}' executed successfully in "
                        f"({elapsed_time}) seconds."
                    )
                    self.__logger.info(info_msg)

                return exit_code

            except Exception as e:
                target = signature
                if target_class and target_method:
                    target = f"{target_class}.{target_method}"
                receipt = await capture(
                    e,
                    app=self.__app,
                    flow="console",
                    operation=target,
                )
                try:
                    feedback = sys.modules.get("orionis.console.startup")
                    if feedback is not None:
                        feedback.stop_startup_feedback()
                except Exception as feedback_error:
                    await capture(
                        feedback_error,
                        app=self.__app,
                        flow="console",
                        phase="feedback",
                        operation=target,
                    )
                if receipt is None:
                    try:
                        error_message = f"Command '{signature}' execution failed: {e}"
                        self.__logger.error(error_message)
                    except Exception as log_error:
                        await capture(
                            log_error,
                            app=self.__app,
                            flow="console",
                            phase="report",
                            operation=target,
                        )
                try:
                    await self.__performance_counter.astop()
                    elapsed_time = round(
                        await self.__performance_counter.agetSeconds(),
                        2,
                    )
                    if command and command.timestamps:
                        self.__executer.fail(program=signature, time=f"{elapsed_time}s")
                except Exception as feedback_error:
                    await capture(
                        feedback_error,
                        app=self.__app,
                        flow="console",
                        phase="feedback",
                        operation=target,
                    )
                try:
                    await self.__catch.exception(e)
                except Exception as handler_error:
                    await capture(
                        handler_error,
                        app=self.__app,
                        flow="console",
                        phase="presentation",
                        operation=target,
                    )
                return 1
