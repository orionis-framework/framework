from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING
from orionis.console.enums.actions import ArgumentAction
from orionis.support.entities.base import BaseEntity
from orionis.support.types.sentinel import MISSING

if TYPE_CHECKING:
    import argparse
    from collections.abc import Callable, Iterable

# Valid nargs values for argparse
_VALID_NARGS: set[str] = {"?", "*", "+"}

# Actions that do not support type conversion and should not have a 'type_' parameter
_ACTIONS_WITHOUT_TYPE: frozenset[str] = frozenset({
    "store_true",
    "store_false",
    "append_const",
    "store_const",
})

@dataclass(kw_only=True, frozen=True, slots=True)
class Argument(BaseEntity):
    """
    Represent a command-line argument definition.

    This entity encapsulates the configuration required to register an argument
    in an ``argparse.ArgumentParser``.

    Parameters
    ----------
    name_or_flags : str | Iterable[str]
        Name or flags for the argument (e.g. "--file" or ("-f", "--file")).
    action : str | ArgumentAction | None, optional
        Action to perform when the argument is encountered.
    nargs : int | str | None, optional
        Number of arguments to consume ('?', '*', '+', or integer).
    const : Any, optional
        Constant value used by actions like 'store_const'.
    default : Any, optional
        Default value if the argument is not provided.
    type_ : Callable[[str], Any] | None, optional
        Function used to convert the argument value.
    choices : Iterable[Any] | None, optional
        Allowed values for the argument.
    required : bool, optional
        Whether the argument is required.
    help : str | None, optional
        Help text for the argument.
    metavar : str | tuple[str, ...] | None, optional
        Name used in help messages.
    dest : str | None, optional
        Attribute name where the parsed value is stored.
    version : str | None, optional
        Version string used with ``action="version"``.
    extra : dict[str, Any], optional
        Additional parameters forwarded to ``add_argument``.
    """

    # ruff: noqa: C901, PLR0915, PLR0912

    name_or_flags: str | Iterable[str]

    action: str | ArgumentAction | None = None

    nargs: int | str | None = None

    const: Any = MISSING

    default: Any = MISSING

    type_: Callable[[str], Any] | None = None

    choices: Iterable[Any] | None = None

    required: bool = False

    help: str | None = None

    metavar: str | tuple[str, ...] | None = None

    dest: str | None = None

    version: str | None = None

    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None: # NOSONAR
        """
        Validate and normalize the argument definition.

        Ensures that all fields are valid and normalized for use with
        argparse.ArgumentParser.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Normalize name_or_flags to tuple of strings
        if isinstance(self.name_or_flags, str):
            flags: tuple[str, ...] = (self.name_or_flags,)
        else:
            flags = tuple(self.name_or_flags)

        # Validate that at least one name or flag is provided
        if not flags:
            error_msg = "At least one name or flag must be provided."
            raise ValueError(error_msg)

        # Validate that all flags are strings
        if not all(isinstance(flag, str) for flag in flags):
            error_msg = "All name_or_flags must be strings."
            raise TypeError(error_msg)

        # Use object.__setattr__ to bypass frozen
        # dataclass restrictions for normalization
        object.__setattr__(self, "name_or_flags", flags)

        # Validate that custom help flags are not used
        if "-h" in self.name_or_flags or "--help" in self.name_or_flags:
            error_msg = "Custom help flags '-h' and '--help' are not allowed."
            raise ValueError(error_msg)

        # Validate action type
        if self.action is not None and not isinstance(
            self.action, (str, ArgumentAction),
        ):
            error_msg = "'action' must be a string, ArgumentAction, or None."
            raise TypeError(error_msg)

        # Validate nargs type and value
        if self.nargs is not None:
            if not isinstance(self.nargs, (int, str)):
                error_msg = "'nargs' must be int, str, or None."
                raise TypeError(error_msg)

            if isinstance(self.nargs, str) and self.nargs not in _VALID_NARGS:
                error_msg = (
                    f"'nargs' must be one of {_VALID_NARGS} or an integer."
                )
                raise ValueError(error_msg)

        # Validate type_ is callable if provided
        if self.type_ is not None and not callable(self.type_):
            error_msg = "'type_' must be callable."
            raise TypeError(error_msg)

        # Validate that type_ is not used with actions that don't support
        # type conversion (store_true, store_false, append_const, store_const)
        if self.type_ is not None and self.action is not None:
            _action_val = (
                self.action.value
                if isinstance(self.action, ArgumentAction)
                else self.action
            )
            if _action_val in _ACTIONS_WITHOUT_TYPE:
                error_msg = (
                    f"'type_' is not compatible with action='{_action_val}'. "
                    f"Actions {set(_ACTIONS_WITHOUT_TYPE)} handle their own "
                    "type conversion and do not accept a 'type_' parameter."
                )
                raise TypeError(error_msg)

        # Validate choices is iterable and not a string
        if self.choices is not None:
            if isinstance(self.choices, str):
                error_msg = "'choices' cannot be a string."
                raise TypeError(error_msg)

            try:
                iter(self.choices)
            except TypeError as exc:
                error_msg = "'choices' must be iterable."
                raise TypeError(error_msg) from exc

        # Validate required is bool
        if not isinstance(self.required, bool):
            error_msg = "'required' must be a bool."
            raise TypeError(error_msg)

        # Validate help is string if provided
        if self.help is not None and not isinstance(self.help, str):
            error_msg = "'help' must be a string."
            raise TypeError(error_msg)

        # Validate metavar type
        if self.metavar is not None:
            if isinstance(self.metavar, tuple):
                if not all(isinstance(m, str) for m in self.metavar):
                    error_msg = "'metavar' tuple must contain only strings."
                    raise TypeError(error_msg)
            elif not isinstance(self.metavar, str):
                error_msg = (
                    "'metavar' must be a string, tuple[str,...], or None."
                )
                raise TypeError(error_msg)

        # Validate dest is string if provided
        if self.dest is not None and not isinstance(self.dest, str):
            error_msg = "'dest' must be a string."
            raise TypeError(error_msg)

        # Validate version is string if provided
        if self.version is not None and not isinstance(self.version, str):
            error_msg = "'version' must be a string."
            raise TypeError(error_msg)

        # Validate extra is a dictionary
        if not isinstance(self.extra, dict):
            error_msg = "'extra' must be a dictionary."
            raise TypeError(error_msg)

        # Consistency check for version action
        action_value = (
            self.action.value if isinstance(self.action, ArgumentAction)
            else self.action
        )

        # If action is 'version', version must be provided
        if action_value == "version" and self.version is None:
            error_msg = "'version' must be provided when action='version'."
            raise ValueError(error_msg)

    def addToParser(self, parser: argparse.ArgumentParser) -> None: # NOSONAR
        """
        Add this argument to an ArgumentParser.

        Registers the argument with the provided parser using the stored
        configuration.

        Parameters
        ----------
        parser : argparse.ArgumentParser
            Parser instance where the argument will be registered.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Prepare parameters for add_argument
        params: dict[str, Any] = {}

        # Always include 'default'
        params["default"] = self.default

        # Determine the action value if it's an ArgumentAction enum
        if self.action is not None:
            params["action"] = (
                self.action.value
                if isinstance(self.action, ArgumentAction)
                else self.action
            )

        # Only include 'type' if it's not None and action is not a store_const variant
        if self.nargs is not None:
            params["nargs"] = self.nargs

        # Include 'type' if provided and the action doesn't
        # handle its own type conversion
        if self.type_ is not None and params.get("action") not in _ACTIONS_WITHOUT_TYPE:
            params["type"] = self.type_

        # Only include 'choices' if it's not None
        if self.choices is not None:
            params["choices"] = self.choices

        # If the argument is required and all flags
        # are optional (start with '-'), set required=True
        if self.required and all(flag.startswith("-") for flag in self.name_or_flags):
            params["required"] = True

        # Only include 'help' if it's not None
        if self.help is not None:
            params["help"] = self.help

        # Only include 'metavar' if it's not None
        if self.metavar is not None:
            params["metavar"] = self.metavar

        # Only include 'dest' if it's not None
        if self.dest is not None:
            params["dest"] = self.dest

        # Only include 'version' if it's not None
        if self.version is not None:
            params["version"] = self.version

        # Only include 'const' if it's not MISSING
        if not isinstance(self.const, type(MISSING)):
            params["const"] = self.const

        # Include any additional parameters from the extra dictionary
        if self.extra:
            params.update(self.extra)

        # Finally, add the argument to the parser
        parser.add_argument(
            *self.name_or_flags,
            **params,
        )
