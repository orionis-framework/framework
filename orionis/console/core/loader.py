import argparse
import importlib
import re
from pathlib import Path
from typing import Any
from orionis.cache.contracts.file_based_cache import IFileBasedCache
from orionis.cache.file_based_cache import FileBasedCache
from orionis.console.args.argument import Argument
from orionis.console.base.command import BaseCommand
from orionis.console.base.contracts.command import IBaseCommand
from orionis.console.core.commands import CORE_COMMANDS
from orionis.console.core.contracts.loader import ILoader
from orionis.console.entities.command import Command
from orionis.console.enums.actions import ArgumentAction as _ArgumentAction
from orionis.console.fluent.command import Command as FluentCommand
from orionis.console.fluent.contracts.command import ICommand
from orionis.foundation.contracts.application import IApplication
from orionis.introspection.modules.inspector import ModuleInspector
from orionis.support.types.sentinel import MISSING as _MISSING

# Define the sentinel type and command signature pattern.
_MISSING_TYPE = type(_MISSING)
_CORE_COMMANDS_PATH = Path(__file__).with_name("commands.py").resolve()
_SIGNATURE_RE: re.Pattern[str] = re.compile(
    r"[a-z][a-z0-9]*(?::[a-z][a-z0-9]*(?:-[a-z0-9]+)*)?",
)

class Loader(ILoader):
    # ruff: noqa: TC001

    def __init__(self, app: IApplication) -> None:
        """
        Initialize the Loader instance.

        Parameters
        ----------
        app : IApplication
            The application instance providing configuration and paths.

        Returns
        -------
        None
            Initializes internal state and sets up command caching.
        """
        # Initialize internal lists and dictionaries for commands and metadata.
        self.__fluent_commands: list[ICommand] = []
        self.__commands: dict[str, Command] = {}
        self.__metadata: dict[str, Any] = {}
        self.__imported_modules: dict[str, Any] = {}
        self.__app: IApplication = app
        self.__all_loaded: bool = False
        self.__metadata_loaded: bool = False

        # Set up persistence for command caching.
        self.__use_cache: bool = False
        self.__persistence: IFileBasedCache | None = self.__getCachePersistence()

    def __getCachePersistence(self) -> IFileBasedCache | None:
        """
        Get the persistence mechanism for command caching.

        Returns
        -------
        FileBasedCache | None
            FileBasedCache instance for command caching, or None if no cache
            configuration is available.
        """
        # Extract cache configuration from application
        compiled = self.__app.compiled

        # Return None if no cache configuration is available
        if not compiled:
            return None

        # Enable caching
        self.__use_cache = True

        # Create and return FileBasedCache instance
        return FileBasedCache(
            path=self.__app.compiledPath,
            filename="commands",
            monitored_dirs=self.__app.compiledInvalidationPathsDirs,
            monitored_files=[
                *self.__app.compiledInvalidationPathsFiles,
                _CORE_COMMANDS_PATH,
            ],
        )

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
        # Load the command corresponding to the given signature
        await self.__load(signature)
        return self.__commands.get(signature)

    async def all(self) -> dict[str, Command]:
        """
        Return all loaded commands.

        Returns
        -------
        dict[str, Command]
            A dictionary mapping command signatures to Command instances.
        """
        # Load all commands into the internal dictionary if not already loaded
        await self.__load()
        return self.__commands

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
        await self.__load()

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
        # Validate that handler is a list with at least one element
        if not isinstance(handler, list) or len(handler) < 1:
            # Handler must be a list with at least one element (the callable)
            error_msg = (
                "Handler must be a list with at least one element (the callable)."
            )
            raise ValueError(error_msg)

        # Ensure the first element is a class
        if not callable(handler[0]) or not hasattr(handler[0], "__name__"):
            # The first element of handler must be a class
            error_msg = "The first element of handler must be a class."
            raise TypeError(error_msg)

        # Create a new FluentCommand instance
        f_command = FluentCommand(
            signature=signature,
            concrete=handler[0],
            method=handler[1] if len(handler) > 1 else "__call__",
        )

        # Add the new command to the internal list
        self.__fluent_commands.append(f_command)

        # Return the newly created command for further configuration
        return f_command

    async def __loadCoreCommands(self) -> None:
        """
        Load and register core command classes provided by the Orionis framework.

        Discover and register core command classes bundled with the Orionis framework.
        Validate required attributes for each command and add them to the internal
        registry.

        Returns
        -------
        None
            Registers core commands internally for later lookup and execution.
        """
        # Iterate and register each core command
        for obj in CORE_COMMANDS:
            sign = self.__getSignature(obj)
            self.__metadata[sign] = {
                "module_path": obj.__module__,
                "class": obj.__name__,
                "method": "handle",
                "signature": sign,
                "description": self.__getDescription(obj),
                "timestamps": self.__getTimestamps(obj),
                "arguments": self.__getArguments(obj),
            }

    async def __loadCustomCommands(self) -> None:
        """
        Load custom command classes from the commands directory.

        Walk through the commands directory, import Python modules, and register
        command classes that inherit from BaseCommand. Sanitize module paths and
        validate command structure before registration.

        Returns
        -------
        None
            Registers command classes internally in the reactor's command registry.
        """
        # Scan the commands directory for Python modules
        modules = ModuleInspector.discoverModules(
            base_path=self.__app.basePath,
            target_path=self.__app.path("app_console_commands"),
        )

        # Iterate through all module names discovered in the commands directory
        for module_name in modules:
            module = importlib.import_module(module_name)

            # Register command classes defined by the current module.
            for obj in vars(module).values():
                if (
                    isinstance(obj, type)
                    and obj.__module__ == module_name
                    and issubclass(obj, BaseCommand)
                    and obj is not BaseCommand
                    and obj is not IBaseCommand
                ):
                    sign = self.__getSignature(obj)
                    self.__metadata[sign] = {
                        "module_path": obj.__module__,
                        "class": obj.__name__,
                        "method": "handle",
                        "signature": sign,
                        "description": self.__getDescription(obj),
                        "timestamps": self.__getTimestamps(obj),
                        "arguments": self.__getArguments(obj),
                    }

    def __importFluentCommandRoutes(self) -> None:
        """
        Import fluent command route modules from application routing paths.

        Load and import all route modules defined in the application's console
        routing configuration. Convert file paths to module names and import
        them to register fluent commands.

        Returns
        -------
        None
            Imports route modules without returning a value.
        """
        # Retrieve the routes file paths from application configuration
        routes_path: list[Path] | Path = self.__app.routingPaths("console")
        routes_path = routes_path if isinstance(routes_path, list) else [routes_path]

        # Get the application root directory
        app_root: Path = self.__app.basePath

        # Iterate through each route file path
        for route_file in routes_path:
            # Convert file path to relative path from application root
            relative_path = route_file.relative_to(app_root)

            # Convert relative path to module name format
            full_module_name = ".".join(relative_path.with_suffix("").parts)

            # Import the module to register fluent commands
            importlib.import_module(full_module_name)

    def __loadFluentCommands(self) -> None:
        """
        Register commands defined via the fluent interface.

        Discover and register all commands created using the fluent API. Validate
        their structure and metadata before adding them to the internal registry.

        Returns
        -------
        None
            Registers fluent commands internally for later lookup and execution.
        """
        # Discover fluent commands defined in the routes directory
        self.__importFluentCommandRoutes()

        # Iterate through all fluent command definitions
        for f_command in self.__fluent_commands:
            # Retrieve signature and command entity
            signature, command = f_command.get()

            # Convert Argument instances to dictionaries for metadata storage
            arguments = (
                [self.__argToDict(arg) for arg in command.args] if command.args else []
            )

            # Register command metadata
            self.__metadata[signature] = {
                "module_path": command.obj.__module__,
                "class": command.obj.__name__,
                "method": command.method,
                "signature": signature,
                "description": command.description,
                "timestamps": command.timestamps,
                "arguments": arguments,
            }

    def __getSignature(self, obj: IBaseCommand) -> str:
        """
        Validate and return the 'signature' attribute of a command class.

        Parameters
        ----------
        obj : IBaseCommand
            Command class instance to validate.

        Returns
        -------
        str
            The validated signature string.

        Raises
        ------
        ValueError
            If the class lacks a 'signature' attribute, if the signature is empty,
            or if the signature does not match the required pattern.
        TypeError
            If the 'signature' attribute is not a string.
        """
        # Read the declared signature from the command class.
        try:
            signature = obj.signature
        except AttributeError as exc:
            error_msg = (
                f"Command class {obj.__name__} must have a 'signature' attribute."
            )
            raise ValueError(error_msg) from exc

        # Ensure the signature attribute is a string
        if not isinstance(signature, str):
            error_msg = f"Command class {obj.__name__} 'signature' must be a string."
            raise TypeError(error_msg)

        # Normalize whitespace around the declared signature.
        signature = signature.strip()
        if not signature:
            error_msg = (
                f"Command class {obj.__name__} 'signature' cannot be an empty string."
            )
            raise ValueError(error_msg)

        # Validate the complete signature against the required pattern.
        if _SIGNATURE_RE.fullmatch(signature) is None:
            error_msg = (
                f"Command class {obj.__name__} 'signature' must contain only "
                "alphanumeric characters with an optional colon and "
                "hyphen-separated suffix, and must start with a lowercase letter."
            )
            raise ValueError(error_msg)

        return signature

    def __getTimestamps(
        self,
        obj: IBaseCommand,
    ) -> bool:
        """
        Retrieve the 'timestamps' attribute from a command class.

        Parameters
        ----------
        obj : IBaseCommand
            Command class instance to inspect.

        Returns
        -------
        bool
            True if the 'timestamps' attribute exists and is a boolean, otherwise
            False.

        Raises
        ------
        TypeError
            If the 'timestamps' attribute exists but is not a boolean.
        """
        # Read the declared timestamp setting.
        timestamps = getattr(obj, "timestamps", _MISSING)
        if timestamps is _MISSING:
            return False

        # Ensure the 'timestamps' attribute is a boolean
        if not isinstance(timestamps, bool):
            error_msg = f"Command class {obj.__name__} 'timestamps' must be a boolean."
            raise TypeError(error_msg)

        # Return the value of the 'timestamps' attribute
        return timestamps

    def __getDescription(
        self,
        obj: IBaseCommand,
    ) -> str:
        """
        Retrieve and validate the 'description' attribute of a command class.

        Ensure the command class has a non-empty string 'description' attribute.
        If missing, set a default description. Raise an error if the attribute
        is not a string or is empty.

        Parameters
        ----------
        obj : IBaseCommand
            Command class instance to validate.

        Returns
        -------
        str
            The validated and stripped description string.

        Raises
        ------
        ValueError
            If the 'description' attribute is empty.
        TypeError
            If the 'description' attribute is not a string.
        """
        # Return default without mutating the class
        description = getattr(obj, "description", None)
        if description is None:
            return "No description provided."

        # Ensure the description is a string
        if not isinstance(description, str):
            error_msg = f"Command class {obj.__name__} 'description' must be a string."
            raise TypeError(error_msg)

        # Ensure the description is not empty
        stripped = description.strip()
        if not stripped:
            error_msg = (
                f"Command class {obj.__name__} 'description' cannot be an empty string."
            )
            raise ValueError(error_msg)

        # Return the validated description
        return stripped

    def __getArguments(
        self,
        obj: IBaseCommand,
    ) -> list[dict]:
        """
        Retrieve and validate Argument inputs for a command class.

        Parameters
        ----------
        obj : IBaseCommand
            Command class instance to validate.

        Returns
        -------
        list of dict
            List of Argument instances as dictionaries. Returns an empty list
            if no inputs are present.

        Raises
        ------
        TypeError
            If the 'inputs' method does not return a list or contains non-
            Argument instances.
        """
        # Read the declared arguments.
        inputs: list[Argument] = getattr(obj, "arguments", _MISSING)
        if inputs is _MISSING:
            return []

        # Ensure inputs is a list
        if not isinstance(inputs, list):
            error_msg = f"Command class {obj.__name__} 'inputs' must return a list."
            raise TypeError(error_msg)

        # Validate all items are Argument instances
        for idx, arg in enumerate(inputs):
            if not isinstance(arg, Argument):
                error_msg = (
                    f"Command class {obj.__name__} 'inputs' must contain only "
                    f"Argument instances, found '{type(arg).__name__}' at index "
                    f"{idx}."
                )
                raise TypeError(error_msg)

        # Return the list of Argument instances as serializable dictionaries
        return [self.__argToDict(arg) for arg in inputs]

    def __argToDict(self, arg: Argument) -> dict:
        """
        Convert an Argument instance to a JSON-compatible dictionary.

        Serialize argument metadata including name, action, type, and other
        properties into a dictionary suitable for caching or transport.

        Parameters
        ----------
        arg : Argument
            The Argument instance to serialize.

        Returns
        -------
        dict
            A dictionary with serialized argument properties.
        """
        # Read the argument fields used in the serialized metadata.
        action = arg.action
        const = arg.const
        default = arg.default
        type_ = arg.type_
        choices = arg.choices
        metavar = arg.metavar

        return {
            "name_or_flags": list(arg.name_or_flags),
            "action": action.value if isinstance(action, _ArgumentAction) else action,
            "nargs": arg.nargs,
            "const": "__MISSING__" if isinstance(const, _MISSING_TYPE) else const,
            "default": "__MISSING__" if isinstance(default, _MISSING_TYPE) else default,
            "type_": (
                f"{type_.__module__}.{type_.__qualname__}"
                if type_ is not None
                else None
            ),
            "choices": list(choices) if choices is not None else None,
            "required": arg.required,
            "help": arg.help,
            "metavar": list(metavar) if isinstance(metavar, tuple) else metavar,
            "dest": arg.dest,
            "version": arg.version,
            "extra": dict(arg.extra),
        }

    def __argFromDict(self, d: dict) -> Argument:
        """
        Reconstruct an Argument instance from a serialized dictionary.

        Deserialize argument metadata by restoring callable types, MISSING
        sentinels, and tuple metavar from their serialized representations.

        Parameters
        ----------
        d : dict
            Dictionary produced by __argToDict containing serialized argument
            properties.

        Returns
        -------
        Argument
            A reconstructed Argument instance with restored properties.
        """
        d = dict(d)

        # Restore callable type from module-qualified string.
        type_str = d.get("type_")
        if type_str is not None:
            parts = type_str.split(".")
            d["type_"] = None
            for index in range(len(parts) - 1, 0, -1):
                try:
                    resolved = importlib.import_module(".".join(parts[:index]))
                except ImportError:
                    continue
                try:
                    for attribute in parts[index:]:
                        resolved = getattr(resolved, attribute)
                except AttributeError:
                    continue
                d["type_"] = resolved
                break

        # Restore MISSING sentinel from string marker.
        if d.get("const") == "__MISSING__":
            d["const"] = _MISSING
        if d.get("default") == "__MISSING__":
            d["default"] = _MISSING

        # Restore tuple metavar from list.
        if isinstance(d.get("metavar"), list):
            d["metavar"] = tuple(d["metavar"])

        return Argument(**d)

    def __buildArgumentParser(
        self,
        arguments: list[dict],
        signature: str,
        description: str,
    ) -> argparse.ArgumentParser | None:
        """
        Construct and configure an ArgumentParser for a command class.

        Build an ArgumentParser using the provided Argument options. Returns
        the parser if arguments exist, otherwise returns None.

        Parameters
        ----------
        arguments : list[dict]
            List of Argument option dictionaries.
        signature : str
            Command signature.
        description : str
            Command description.

        Returns
        -------
        argparse.ArgumentParser | None
            ArgumentParser instance configured with the command's arguments, or None
            if no arguments are present.
        """
        # Build the ArgumentParser for the command
        arg_parser = argparse.ArgumentParser(
            epilog=(
                "To ensure the command definition is up to date, run "
                "'python reactor optimize:clear' to clear the command cache."
            ),
            usage=f"python reactor {signature}",
            description=f"Command [{signature}]: {description}",
            formatter_class=argparse.RawTextHelpFormatter,
            add_help=True,
            allow_abbrev=False,
            exit_on_error=True,
            prog=signature,
        )

        # Add each Argument to the ArgumentParser
        for arg in arguments:
            self.__argFromDict(arg).addToParser(arg_parser)

        # Return the constructed ArgumentParser
        return arg_parser

    def __buildCommand(self, meta: dict) -> Command:
        """
        Build a Command instance from metadata.

        Parameters
        ----------
        meta : dict
            Metadata dictionary containing command information.

        Returns
        -------
        Command
            The constructed Command instance.
        """
        # Import the module and retrieve the command class, caching imports
        module_path: str = meta["module_path"]
        module = self.__imported_modules.get(module_path)
        if module is None:
            module = importlib.import_module(module_path)
            self.__imported_modules[module_path] = module
        cls = getattr(module, meta["class"])

        # Build and return the Command instance using metadata
        return Command(
            obj=cls,
            method=meta["method"],
            signature=meta["signature"],
            description=meta["description"],
            timestamps=meta["timestamps"],
            args=self.__buildArgumentParser(
                meta["arguments"],
                meta["signature"],
                meta["description"],
            ),
        )

    async def __loadMetadata(self) -> None:
        """
        Load command metadata from cache or discover commands.

        Loads metadata from cache if available and caching is enabled. If no cached
        metadata exists, discovers all command types and optionally saves to cache.

        Returns
        -------
        None
            Populates the internal metadata dictionary.
        """
        # Return when command metadata has already been loaded.
        if self.__metadata_loaded:
            return

        # Load from cache if enabled
        if self.__use_cache and self.__persistence:
            self.__metadata = self.__persistence.get() or {}

        # Discover commands if no metadata available
        if not self.__metadata:
            await self.__loadCoreCommands()
            await self.__loadCustomCommands()
            self.__loadFluentCommands()

            # Save to cache if enabled
            if self.__use_cache and self.__persistence:
                self.__persistence.save(self.__metadata)

        self.__metadata_loaded = True

    async def __load(self, signature: str | None = None) -> None:
        """
        Load command classes from metadata and populate the commands dictionary.

        Parameters
        ----------
        signature : str | None
            The unique signature of the command to load, or None to load all.

        Returns
        -------
        None
            This method populates the internal commands dictionary and does not
            return a value.
        """
        # Load metadata if not already loaded
        await self.__loadMetadata()

        # Load specific command or all commands based on the signature parameter
        if signature:
            if signature in self.__commands:
                return
            meta = self.__metadata.get(signature)
            if not meta:
                return
            self.__commands[signature] = self.__buildCommand(meta)
        else:
            if self.__all_loaded:
                return
            # Load all commands from metadata
            for sig, meta in self.__metadata.items():
                if sig not in self.__commands:
                    self.__commands[sig] = self.__buildCommand(meta)
            self.__all_loaded = True
