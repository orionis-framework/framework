# ruff: noqa: PLR0911
# Preserve the type parser's direct dispatch branches.
"""Load and cache values from a resolved dotenv file."""

from __future__ import annotations
import os
import ast
import threading
from pathlib import Path
from dotenv import dotenv_values, set_key, unset_key
from orionis.environment.enums import EnvironmentValueType
from orionis.environment.validators import ValidateKeyName, ValidateTypes
from orionis.support.patterns.singleton import Singleton
from orionis.environment.dynamic.caster import EnvironmentCaster

# Module-level constants computed once — eliminates per-call allocations
_NULL_VALUES: frozenset[str] = frozenset({"none", "null", "nan", "nil"})
"""Module-level constants computed once — eliminates per-call allocations."""
_ENV_TYPE_PREFIXES: frozenset[str] = frozenset(e.value for e in EnvironmentValueType)
"""Env type prefixes used by ``dot_env``."""
_DISABLED_VALUES = frozenset({"1", "true", "t", "yes", "y"})
"""Truthy values recognized by python-dotenv's process-loading switch."""
_WINDOWS_ENV_LIMIT = 32767
"""Maximum UTF-16 length of a Windows process assignment including its equals sign."""


class DotEnv(metaclass=Singleton):
    """Load and cache values from a resolved dotenv file."""

    __slots__ = ("__cache", "__resolved_path")
    """Declare the instance attribute slots reserved by this class."""

    # Lock to ensure thread safety during initialization and
    # operations that modify the .env file
    _lock = threading.Lock()
    """
    Lock to ensure thread safety during initialization and operations that modify
    the .env file.
    """

    def __init__(
        self,
        path: str | None = None,
    ) -> None:
        """
        Initialize the DotEnv service and prepare the ``.env`` file.

        Parameters
        ----------
        path : str or None, optional
            Path to the ``.env`` file. Defaults to ``.env`` in the current working
            directory.

        Raises
        ------
        OSError
            If the ``.env`` file cannot be created or accessed.
        RuntimeError
            If an unexpected error occurs during initialization.

        Returns
        -------
        None
            This method does not return a value.
        """
        requested_path = path or ".env"
        try:
            # Ensure thread-safe initialization to avoid race conditions.
            with self._lock:
                self.__resolved_path = Path(requested_path).expanduser().resolve()
                """Resolved backing file selected by the singleton's first caller."""

                # Create the .env file if it does not exist.
                if not self.__resolved_path.exists():
                    self.__resolved_path.touch()

                self.__cache: dict[str, str | None] = self.__loadValues()
                """Single parsed snapshot used for file-backed values."""

        except OSError as e:
            # Raise a specific error if the .env file cannot be created or accessed.
            error_msg = (  # NOSONAR(S1110) - Preserve multiline grouping.
                f"Failed to create or access the .env file at {requested_path}: {e}"
            )
            raise OSError(error_msg) from e

        except Exception as e:
            # Raise a general error for any other exceptions during initialization.
            error_msg = "An unexpected error occurred while initializing DotEnv"
            raise RuntimeError(error_msg) from e

    def set(
        self,
        key: str,
        value: object,
        type_hint: str | EnvironmentValueType | None = None,
        *,
        only_os: bool = False,
    ) -> bool:
        """
        Set an environment variable in the ``.env`` file and process environment.

        Parameters
        ----------
        key : str
            Name of the environment variable to set.
        value : object
            Value to serialize. Without a hint, strings, scalar values, None,
            and literal containers are supported; other objects use ``str``.
        type_hint : str | EnvironmentValueType | None, optional
            Type hint to guide serialization of the value.
        only_os : bool, optional
            If True, set only in the process environment, not in the ``.env`` file.

        Returns
        -------
        bool
            True if the environment variable was set successfully.

        Raises
        ------
        TypeError
            If ``key`` is not a string, an explicitly typed value is unsupported,
            or ``type_hint`` is neither a string nor an ``EnvironmentValueType``.
        ValueError
            If ``key`` is not a valid environment variable name, or if ``value``
            cannot be serialized for the requested type.
        RuntimeError
            If ``type_hint`` is a string that does not name a member of
            ``EnvironmentValueType``.

        Notes
        -----
        Ensures thread safety, validates the key, serializes the value, writes to
        the ``.env`` file, and updates the process environment.
        """
        __key: str = ValidateKeyName(key)
        # User-defined text conversion may itself read the environment.
        if type_hint is not None:
            __type = ValidateTypes(value=value, type_hint=type_hint)
            __value = self.__serializeValue(value, __type)
        else:
            __value = self.__serializeValue(value)
        self.__validateProcessValue(__key, __value)

        with self._lock:
            # Set the environment variable in the .env file unless only_os is True.
            if not only_os:
                set_key(self.__resolved_path, __key, __value)
                self.__cache[__key] = __value

            # Update the environment variable in the current process environment.
            os.environ[__key] = __value

            # Indicate successful operation.
            return True

    def get(
        self,
        key: str,
        default: object | None = None,
    ) -> object:
        """
        Retrieve the value of an environment variable.

        Parameters
        ----------
        key : str
            Name of the environment variable to retrieve.
        default : object | None, optional
            Value to return if the key is not found. Defaults to None.

        Returns
        -------
        object
            Parsed value of the environment variable if found, otherwise ``default``.

        Raises
        ------
        TypeError
            If ``key`` is not a string, or if the stored value is incompatible
            with its declared type.
        ValueError
            If ``key`` is not a valid environment variable name, or if the stored
            value cannot be decoded for its declared type.
        """
        __key = ValidateKeyName(key)
        with self._lock:
            # Process reads include external and process-only changes; the file
            # snapshot remains separate for all().
            value = os.environ.get(__key)

            # Parse and return the value if found, otherwise return the default.
            return self.__parseValue(value) if value is not None else default

    def unset(
        self,
        key: str,
        *,
        only_os: bool = False,
    ) -> bool:
        """
        Remove an environment variable from the ``.env`` file and process environment.

        Parameters
        ----------
        key : str
            Name of the environment variable to remove.
        only_os : bool, optional
            If True, remove only from the process environment, not from the ``.env``
            file.

        Returns
        -------
        bool
            True if the environment variable was removed or did not exist.

        Raises
        ------
        TypeError
            If ``key`` is not a string.
        ValueError
            If ``key`` is not a valid environment variable name.

        Notes
        -----
        This method is thread-safe. If the variable does not exist, returns True.
        """
        validated_key: str = ValidateKeyName(key)
        with self._lock:
            # Remove the key from the .env file unless only_os is True.
            if not only_os:
                unset_key(self.__resolved_path, validated_key)
                self.__cache.pop(validated_key, None)

            # Remove the key from the current process environment, if present.
            os.environ.pop(validated_key, None)

            # Indicate successful operation.
            return True

    def all(self) -> dict:
        """
        Return all environment variables from the resolved ``.env`` file.

        Returns
        -------
        dict
            Dictionary mapping environment variable names (str) to their parsed
            Python values. Only variables present in the ``.env`` file are included.
        """
        # Acquire lock for thread-safe access to the .env file.
        with self._lock:
            # Parse each value from the in-memory cache and return as a dictionary.
            return {k: self.__parseValue(v) for k, v in self.__cache.items()}

    @staticmethod
    def __validateProcessValue(key: str, value: str) -> None:
        """Reject a serialized value that cannot enter the process environment.

        Parameters
        ----------
        key : str
            Environment variable name included in the Windows size limit.
        value : str
            Serialized environment value to validate before any mutation.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        ValueError
            If the value contains a null byte or exceeds Windows' native
            assignment length limit.
        """
        if "\x00" in value:
            error_msg = "Environment values cannot contain null bytes."
            raise ValueError(error_msg)
        if os.name == "nt" and (
            len(key) + len(value) + 1 > _WINDOWS_ENV_LIMIT
            or len(f"{key}={value}".encode("utf-16-le", errors="surrogatepass")) // 2
            > _WINDOWS_ENV_LIMIT
        ):
            error_msg = "Environment assignment exceeds the Windows length limit."
            raise ValueError(error_msg)

    def __loadValues(self) -> dict[str, str | None]:
        """Parse the file once and publish its validated process values.

        Returns
        -------
        dict[str, str | None]
            The same resolved values used for the process and file snapshot.
            Entries without an assignment retain None in the snapshot.

        Raises
        ------
        OSError
            If the selected file cannot be read.
        ValueError
            If decoded entries cannot be assigned to the process environment.
        """
        with self.__resolved_path.open(encoding="utf-8") as source:
            values = dict(dotenv_values(stream=source))
        if os.environ.get("PYTHON_DOTENV_DISABLED", "").casefold() in _DISABLED_VALUES:
            return values
        updates = {}
        for key, value in values.items():
            if not key or "=" in key or "\x00" in key:
                error_msg = "The environment file contains an invalid variable name."
                raise ValueError(error_msg)
            if value is not None:
                self.__validateProcessValue(key, value)
                updates[key] = value
        os.environ.update(updates)
        return values

    def __serializeValue(
        self,
        value: object,
        type_hint: str | EnvironmentValueType | None = None,
    ) -> str:
        """
        Serialize a Python value for storage in a .env file.

        Parameters
        ----------
        value : object
            The value to serialize. Supported types include None, str, int, float,
            bool, list, dict, tuple, and set.
        type_hint : str | EnvironmentValueType | None, optional
            An explicit type hint to guide serialization.

        Returns
        -------
        str
            The serialized string representation of the input value, suitable for
            storage in a .env file. Returns "null" for None values.
        """
        # Handle None values explicitly
        if value is None:
            return "null"

        # Use EnvironmentCaster for serialization if a type hint is provided
        if type_hint:
            return EnvironmentCaster(value).to(type_hint)

        # Serialize strings by stripping whitespace
        if isinstance(value, str):
            return value.strip()

        # Serialize booleans as lowercase strings ("true" or "false")
        if isinstance(value, bool):
            return str(value).lower()

        # Serialize integers and floats as strings
        if isinstance(value, (int, float)):
            return str(value)

        # Serialize collections (list, dict, tuple, set) using repr
        if isinstance(value, (list, dict, tuple, set)):
            return repr(value)

        # Fallback: convert any other type to string
        return str(value)

    def __parseValue(
        self,
        value: object,
    ) -> object:
        """
        Parse a value from the .env file into its corresponding Python type.

        Parameters
        ----------
        value : object
            The value to parse, typically a string from the .env file or a Python
            object.

        Returns
        -------
        object
            The parsed Python value. Returns None for recognized null
            representations, a boolean for "true"/"false" strings, a Python
            literal (list, dict, int, etc.) if possible, or the original string
            if no conversion is possible.

        Notes
        -----
        Recognizes 'none', 'null', 'nan', 'nil' (case-insensitive) as null
        values. Attempts to use ``EnvironmentCaster`` for advanced type parsing.
        Falls back to ``ast.literal_eval`` for literal evaluation. Returns the
        original string if all parsing attempts fail.
        """
        # Return None if the value is None
        if value is None:
            return None

        # Return immediately if already a basic Python type
        if isinstance(value, (bool, int, float, dict, list, tuple, set)):
            return value

        # Use the string directly if already a str, otherwise convert once
        value_str: str = value if isinstance(value, str) else str(value)

        # Handle empty strings quickly
        if not value_str:
            return None

        # Compute normalized form once and reuse for all comparisons
        lower_stripped: str = value_str.lower().strip()

        # Recognize common null representations.
        if lower_stripped in _NULL_VALUES:
            return None

        # Boolean detection for string values (case-insensitive)
        if lower_stripped in ("true", "false"):
            return lower_stripped == "true"

        # Check the prefix before the first colon.
        if ":" in value_str:
            prefix, _ = value_str.split(":", 1)
            if prefix.strip().lower() in _ENV_TYPE_PREFIXES:
                return EnvironmentCaster.parseTyped(value_str)

        # Attempt to parse using ast.literal_eval for Python literals
        try:
            return ast.literal_eval(value_str)
        except ValueError, SyntaxError:
            # Return the original string if parsing fails
            return value_str

    def reload(self) -> bool:
        """
        Reload environment variables from the ``.env`` file.

        Reload all environment variables from the ``.env`` file into the current
        process environment, overriding any existing values.

        Returns
        -------
        bool
            True if environment variables were successfully reloaded.

        Raises
        ------
        RuntimeError
            If an error occurs during the reload operation.
        """
        try:
            # Ensure thread-safe operation during reload
            with self._lock:
                self.__cache = self.__loadValues()
                return True

        except Exception as e:
            # Raise a specific error if any exception occurs during the reload process.
            error_msg = "An error occurred while reloading environment variables"
            raise RuntimeError(error_msg) from e
