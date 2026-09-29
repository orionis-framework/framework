from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.environment.enums.value_type import EnvironmentValueType

class IEnv(ABC):

    # ruff: noqa: FBT001

    __slots__ = ()

    @classmethod
    @abstractmethod
    def get(
        cls,
        key: str,
        default: object | None = None,
    ) -> object:
        """
        Get the value of an environment variable by key.

        Parameters
        ----------
        key : str
            Name of the environment variable to retrieve.
        default : object | None, optional
            Value to return if the environment variable is not found.
            Defaults to None.

        Returns
        -------
        object
            Value of the environment variable if it exists, otherwise the
            provided default value.
        """

    @classmethod
    @abstractmethod
    def set(
        cls,
        key: str,
        value: str | float | bool | list | dict | tuple | set,
        type_hint: str | EnvironmentValueType | None = None,
        *,
        only_os: bool = False,
    ) -> bool:
        """
        Set or update an environment variable.

        Parameters
        ----------
        key : str
            Name of the environment variable to set or update.
        value : str | float | bool | list | dict | tuple | set
            Value to assign to the environment variable.
        type_hint : str | EnvironmentValueType | None, optional
            Type hint for the variable. Supported types: 'str', 'int', 'float',
            'bool', 'list', 'dict', 'tuple', 'set', 'base64', 'path'.
        only_os : bool, optional
            If True, set the variable only in the OS environment.

        Returns
        -------
        bool
            True if the environment variable was set successfully, otherwise
            False.
        """

    @classmethod
    @abstractmethod
    def unset(
        cls,
        key: str,
        *,
        only_os: bool = False,
    ) -> bool:
        """
        Remove an environment variable from the .env file.

        Parameters
        ----------
        key : str
            Name of the environment variable to remove.
        only_os : bool, optional
            If True, remove the variable only from the OS environment.
            Defaults to False.

        Returns
        -------
        bool
            True if the environment variable was removed successfully,
            False otherwise.
        """

    @classmethod
    @abstractmethod
    def all(
        cls,
    ) -> dict[str, Any]:
        """
        Retrieve all environment variables as a dictionary.

        Access the shared DotEnv singleton instance and return all loaded
        environment variables in dictionary format for inspecting current
        environment configuration.

        Returns
        -------
        dict[str, Any]
            Dictionary containing all environment variables loaded by DotEnv.
        """

    @classmethod
    @abstractmethod
    def reload(cls) -> bool:
        """
        Reload environment variables from the .env file.

        Refresh the shared DotEnv singleton in place: the file is read again
        into the process environment and the in-memory snapshot is rebuilt,
        keeping the same instance. Useful when the .env file has been modified
        externally and the latest values need to be reflected in the application.

        Returns
        -------
        bool
            True if the environment variables were reloaded successfully,
            False if the shared DotEnv instance could not be built because of
            an OSError or a ValueError.

        Raises
        ------
        RuntimeError
            If the reload itself fails. DotEnv.reload wraps every failure in
            this type, which is deliberately left to propagate.
        """
