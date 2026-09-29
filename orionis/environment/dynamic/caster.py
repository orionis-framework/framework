from __future__ import annotations
import ast
import base64
from pathlib import Path
from typing import Any, ClassVar
from orionis.environment.contracts.caster import IEnvironmentCaster
from orionis.environment.enums.value_type import EnvironmentValueType

class EnvironmentCaster(IEnvironmentCaster):

    # Precompute the set of valid type hints from the
    # EnvironmentValueType enum for fast membership checks.
    OPTIONS: ClassVar[frozenset[str]] = frozenset(e.value for e in EnvironmentValueType)

    # Use __slots__ to prevent dynamic attribute creation and reduce memory overhead
    __slots__ = ("_EnvironmentCaster__type_hint", "_EnvironmentCaster__value_raw")

    @staticmethod
    def supportedTypes() -> frozenset[str]:
        """
        Return the set of valid type hints supported by this class.

        Returns
        -------
        set[str]
            Set of valid type hint strings that can be used for environment
            value casting.
        """
        return EnvironmentCaster.OPTIONS

    @staticmethod
    def parseTyped(value_str: str) -> object:
        """
        Parse a typed string (e.g. 'int:42') without full object construction.

        Provides a fast path for the common case where a string with a known
        type prefix must be parsed. Primitive types (int, float, bool, str) are
        handled inline without allocating an EnvironmentCaster instance. Complex
        types (list, dict, tuple, set, path, base64) fall back to full
        instantiation only when necessary.

        Parameters
        ----------
        value_str : str
            A string in the format ``<type_hint>:<value>``, e.g. ``int:42``.

        Returns
        -------
        object
            The parsed Python value according to the embedded type hint.

        Raises
        ------
        ValueError
            If the value cannot be converted to the indicated type.
        TypeError
            If the value is incompatible with the indicated type.
        """
        colon_idx = value_str.index(":")
        type_hint = value_str[:colon_idx].strip().lower()
        raw = value_str[colon_idx + 1:].lstrip()

        # Fast-path for primitives — no object construction
        if type_hint == "int":
            stripped = raw.strip()
            try:
                return int(stripped)
            except ValueError as e:
                error_msg = f"Cannot convert '{stripped}' to int: {e!s}"
                raise ValueError(error_msg) from e

        if type_hint == "float":
            stripped = raw.strip()
            try:
                return float(stripped)
            except ValueError as e:
                error_msg = f"Cannot convert '{stripped}' to float: {e!s}"
                raise ValueError(error_msg) from e

        if type_hint == "bool":
            return raw.strip().lower() in ("true", "1", "yes", "on", "enabled")

        if type_hint == "str":
            return raw

        # Complex types: delegate to full caster
        return EnvironmentCaster(value_str).get()

    def __init__(
        self,
        raw: str | object,
    ) -> None:
        """
        Initialize the caster by parsing input to extract type hint and value.

        Parameters
        ----------
        raw : str | object
            Input value to be parsed. If string containing a colon, the part
            before the colon is treated as type hint and after as value. If no
            colon is present, entire string is treated as value with no type
            hint. Non-string inputs are treated as values with no type hint.

        Returns
        -------
        None
            Does not return a value; initializes instance attributes.
        """
        # Initialize type hint and value to default None
        self.__type_hint: str | None = None
        self.__value_raw: str | Any = None

        # Process string inputs to extract type hint and value
        if isinstance(raw, str):

            # Remove leading whitespace from the input
            self.__value_raw = raw.lstrip()

            # Check if the string contains a colon, indicating a type hint
            if ":" in self.__value_raw:
                # Split at the first colon to separate type hint and value
                type_hint, value_str = raw.split(":", 1)

                # Validate the extracted type hint and set attributes if valid
                if type_hint.strip().lower() in self.OPTIONS:
                    # Set the type hint after stripping whitespace
                    self.__type_hint = type_hint.strip().lower()

                    # Remove leading whitespace from the value part
                    self.__value_raw = value_str.lstrip() if value_str else None
        else:

            # Treat non-string input as the value with no type hint
            self.__value_raw = raw

    def get(  # noqa: PLR0911, PLR0912, C901
        self,
    ) -> object:
        """
        Return the processed value according to the type hint.

        If a valid type hint is present, dispatch to the corresponding internal
        parsing method for that type. Supported type hints include: 'path', 'str',
        'int', 'float', 'bool', 'list', 'dict', 'tuple', 'set', and 'base64'.
        If no type hint is set, return the raw value.

        Parameters
        ----------
        self : EnvironmentCaster
            Instance of the EnvironmentCaster class.

        Returns
        -------
        object
            The value converted or processed according to the specified type hint.
            If no type hint is set, returns the raw value.

        Raises
        ------
        ValueError
            If an error occurs during type conversion or processing.
        TypeError
            If an error occurs during type conversion or processing.
        """
        try:
            # If no type hint is set, return the raw value
            th = self.__type_hint
            if not th:
                return self.__value_raw

            # if/elif dispatch — zero allocations, no bound-method creation per call
            if th == "str":
                return self.__parseStr()
            if th == "int":
                return self.__parseInt()
            if th == "float":
                return self.__parseFloat()
            if th == "bool":
                return self.__parseBool()
            if th == "list":
                return self.__parseList()
            if th == "dict":
                return self.__parseDict()
            if th == "tuple":
                return self.__parseTuple()
            if th == "set":
                return self.__parseSet()
            if th == "path":
                return self.__parsePath()
            if th == "base64":
                return self.__parseBase64()
            return self.__value_raw
        except (ValueError, TypeError) as e:
            error_msg = (
                f"Error processing value '{self.__value_raw}' with type hint "
                f"'{self.__type_hint}': {e!s}"
            )
            # Re-raise the same concrete type (ValueError or TypeError)
            if isinstance(e, TypeError):
                raise TypeError(error_msg) from e
            raise ValueError(error_msg) from e
        except Exception as e:
            error_msg = (
                f"Error processing value '{self.__value_raw}' with type hint "
                f"'{self.__type_hint}': {e!s}"
            )
            raise ValueError(error_msg) from e

    def to(  # noqa: PLR0911, PLR0912, C901
        self,
        type_hint: str | EnvironmentValueType,
    ) -> str:
        """
        Convert the internal value to the specified type and return as a string.

        Parameters
        ----------
        type_hint : str or EnvironmentValueType
            The type to which the internal value should be converted. Must be a
            valid option in `OPTIONS`.

        Returns
        -------
        str
            String representation of the value with the type hint prefix, e.g.,
            int:42, list:[1, 2, 3], etc.

        Raises
        ------
        ValueError
            If the provided type hint is invalid or conversion fails.
        """
        # Try to perform the conversion based on the provided type hint
        try:
            # Convert enum type_hint to its string value if necessary
            if isinstance(type_hint, EnvironmentValueType):
                type_hint = type_hint.value

            # Validate the type hint against supported options
            if type_hint not in self.OPTIONS:
                error_msg = (
                    f"Invalid type hint: {type_hint}. Must be one of {self.OPTIONS}."
                )
                raise ValueError(error_msg)

            # Set the type hint for conversion
            self.__type_hint = type_hint

            # if/elif dispatch — zero allocations, no bound-method creation per call
            if type_hint == "str":
                return self.__toStr()
            if type_hint == "int":
                return self.__toInt()
            if type_hint == "float":
                return self.__toFloat()
            if type_hint == "bool":
                return self.__toBool()
            if type_hint == "list":
                return self.__toList()
            if type_hint == "dict":
                return self.__toDict()
            if type_hint == "tuple":
                return self.__toTuple()
            if type_hint == "set":
                return self.__toSet()
            if type_hint == "path":
                return self.__toPath()
            if type_hint == "base64":
                return self.__toBase64()
            error_msg = (
                f"Type hint '{self.__type_hint}' is not supported for conversion."
            )
            raise ValueError(error_msg)

        except Exception as e:
            error_msg = (
                f"Error converting value '{self.__value_raw}' to type '{type_hint}': "
                f"{e!s}"
            )
            raise ValueError(error_msg) from e

    def __toBase64(
        self,
    ) -> str:
        """
        Convert internal value to Base64 encoded string with type hint prefix.

        If the value is already valid Base64, it is preserved as-is.
        Otherwise, the value is encoded to Base64 format.

        Returns
        -------
        str
            String in format "<type_hint>:<base64_value>" where base64_value
            is the Base64 encoded representation.

        Raises
        ------
        TypeError
            If the internal value is not a string or bytes type.
        ValueError
            If there's an error during Base64 encoding/decoding operations.
        """
        # Validate input type before processing
        if not isinstance(self.__value_raw, (str, bytes)):
            type_name = type(self.__value_raw).__name__
            msg = (
                "Value must be a string or bytes to convert to Base64, "
                f"got {type_name} instead."
            )
            raise TypeError(msg)

        # Normalize input to string for Base64 validation
        if isinstance(self.__value_raw, bytes):
            try:
                candidate = self.__value_raw.decode("utf-8")
            except UnicodeDecodeError as e:
                error_msg = f"Cannot decode bytes to UTF-8: {e}"
                raise ValueError(error_msg) from e
        else:
            candidate = self.__value_raw

        try:
            # Check if the value is already valid Base64
            base64.b64decode(candidate, validate=True)
            encoded_value = candidate
        except (base64.binascii.Error, ValueError):
            # Value is not valid Base64, encode it
            try:
                raw_bytes = (
                    self.__value_raw.encode("utf-8")
                    if isinstance(self.__value_raw, str)
                    else self.__value_raw
                )
                encoded_value = base64.b64encode(raw_bytes).decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError) as e:
                error_msg = f"Error during Base64 encoding: {e}"
                raise ValueError(error_msg) from e

        # Return formatted string with type hint prefix
        return f"{self.__type_hint}:{encoded_value}"

    def __parseBase64(
        self,
    ) -> str | bytes:
        """
        Decode the internal raw value from Base64 encoding.

        Returns
        -------
        str | bytes
            The decoded value. Returns a UTF-8 string if the decoded bytes
            represent valid UTF-8 text, otherwise returns the raw bytes.

        Raises
        ------
        ValueError
            If the internal value cannot be decoded from Base64.
        """
        try:
            # Normalize input to string for Base64 decoding
            raw_value = self.__value_raw
            if isinstance(raw_value, bytes):
                raw_value = raw_value.decode("utf-8", errors="ignore")

            # Decode the Base64 value with validation
            decoded = base64.b64decode(raw_value, validate=True)

            # Attempt to decode as UTF-8 string, fallback to raw bytes
            try:
                return decoded.decode("utf-8")
            except UnicodeDecodeError:
                return decoded

        except Exception as e:
            error_msg = f"Cannot decode Base64 value '{self.__value_raw}': {e!s}"
            raise ValueError(error_msg) from e

    def __parsePath(
        self,
    ) -> str:
        """
        Convert the internal raw value to a normalized POSIX path string.

        Process the internal value as a file system path. If the value is already
        a `Path` object, return its POSIX representation. If the value is a string,
        replace backslashes with forward slashes for normalization and return the
        POSIX path string.

        Returns
        -------
        str
            The normalized POSIX path string representing the file system path.

        Raises
        ------
        ValueError
            If the value cannot be processed as a valid path.
        """
        try:
            # If the value is already a Path object, return its POSIX representation
            if isinstance(self.__value_raw, Path):
                return self.__value_raw.as_posix()

            # Normalize the path by replacing backslashes with forward slashes
            normalized_path = str(self.__value_raw).replace("\\", "/")

            # Convert normalized string to Path object and return POSIX representation
            return Path(normalized_path).as_posix()

        except Exception as e:
            # Create error message for path conversion failure
            error_msg = f"Cannot convert '{self.__value_raw}' to path: {e!s}"
            raise ValueError(error_msg) from e

    def __toPath(
        self,
    ) -> str:
        """
        Convert internal value to absolute POSIX path string with type hint prefix.

        Parameters
        ----------
        self : EnvironmentCaster
            Instance of the EnvironmentCaster class.

        Returns
        -------
        str
            String in format "<type_hint>:<absolute_path>" where absolute_path
            is the normalized, absolute POSIX path representation.

        Raises
        ------
        TypeError
            If the internal value is not a string or pathlib.Path object.
        """
        # Validate input type
        if not isinstance(self.__value_raw, (str, Path)):
            error_msg = (
                f"Value must be a string or Path to convert to path, "
                f"got {type(self.__value_raw).__name__} instead."
            )
            raise TypeError(error_msg)

        # Normalize slashes and strip whitespace
        raw_path = str(self.__value_raw).replace("\\", "/").strip()

        # Create Path object from normalized string
        path_obj = Path(raw_path)

        # Convert relative paths to absolute paths
        if not path_obj.is_absolute():
            # Remove leading slash to avoid creating absolute path when joining
            raw_path_no_leading = raw_path.lstrip("/\\")

            # Combine with current working directory (Path.cwd() already returns Path)
            path_obj = Path.cwd() / raw_path_no_leading

        # Expand user home and convert to POSIX format
        abs_path = path_obj.expanduser().as_posix()

        # Return formatted string with type hint prefix
        return f"{self.__type_hint}:{abs_path!s}"

    def __parseStr(
        self,
    ) -> str:
        """
        Return the internal raw value as a string with leading whitespace removed.

        Returns
        -------
        str
            The internal value as a string with leading whitespace stripped.
        """
        # Remove leading whitespace from the internal value to clean the input
        return self.__value_raw.lstrip()

    def __toStr(
        self,
    ) -> str:
        """
        Return the internal value as a string prefixed by the type hint.

        Parameters
        ----------
        self : EnvironmentCaster
            Instance of the EnvironmentCaster class.

        Returns
        -------
        str
            String in the format "<type_hint>:<value>", where <type_hint> is the
            current type hint and <value> is the string value.

        Raises
        ------
        TypeError
            If the internal value is not a string.
        """
        # Ensure the internal value is a string before conversion
        if not isinstance(self.__value_raw, str):
            error_msg = (
                f"Value must be a string to convert to str, got "
                f"{type(self.__value_raw).__name__} instead."
            )
            raise TypeError(error_msg)

        # Return the formatted string with type hint and value
        return f"{self.__type_hint}:{self.__value_raw}"

    def __parseInt(
        self,
    ) -> int:
        """
        Convert the internal raw value to an integer.

        Strip leading and trailing whitespace from the internal raw value and
        attempt to convert it to an integer.

        Returns
        -------
        int
            The internal value converted to an integer.

        Raises
        ------
        ValueError
            If the value cannot be converted to an integer due to invalid format
            or type.
        """
        # Remove leading and trailing whitespace from the raw value
        value = self.__value_raw.strip()

        # Attempt to convert the value to an integer
        try:
            return int(value)
        except ValueError as e:
            error_msg = f"Cannot convert '{value}' to int: {e!s}"
            raise ValueError(error_msg) from e

    def __toInt(
        self,
    ) -> str:
        """
        Convert the internal value to a string with the integer type hint prefix.

        Supports conversion from string values to integers for usability.

        Returns
        -------
        str
            String in the format "<type_hint>:<value>", where <type_hint> is the
            current type hint and <value> is the integer value.

        Raises
        ------
        ValueError
            If the internal value cannot be converted to an integer.
        """
        # Use the value directly if it is already an integer
        if isinstance(self.__value_raw, int):
            return f"{self.__type_hint}:{self.__value_raw!s}"

        # Try to convert string values to integer
        if isinstance(self.__value_raw, str):
            try:
                converted_value = int(self.__value_raw.strip())
                return f"{self.__type_hint}:{converted_value!s}"
            except ValueError as e:
                error_msg = (
                    f"Cannot convert string '{self.__value_raw}' to integer. "
                    "Value must be a valid integer representation."
                )
                raise ValueError(error_msg) from e

        # Attempt direct conversion for other types
        try:
            converted_value = int(self.__value_raw)
            return f"{self.__type_hint}:{converted_value!s}"
        except (ValueError, TypeError) as e:
            error_msg = (
                f"Value must be convertible to integer, got "
                f"{type(self.__value_raw).__name__} with value '{self.__value_raw}'."
            )
            raise ValueError(error_msg) from e

    def __parseFloat(
        self,
    ) -> float:
        """
        Convert the internal raw value to a float.

        Strips leading and trailing whitespace from the internal raw value and
        attempts to convert it to a float.

        Parameters
        ----------
        self : EnvironmentCaster
            Instance of the EnvironmentCaster class.

        Returns
        -------
        float
            The internal value converted to a float.

        Raises
        ------
        ValueError
            If the value cannot be converted to a float due to invalid format or type.
        """
        # Remove leading and trailing whitespace from the raw value
        value = self.__value_raw.strip()

        # Attempt to convert the value to a float
        try:
            return float(value)
        except ValueError as e:
            error_msg = f"Cannot convert '{value}' to float: {e!s}"
            raise ValueError(error_msg) from e

    def __toFloat(
        self,
    ) -> str:
        """
        Convert the internal value to a string with the float type hint prefix.

        Parameters
        ----------
        self : EnvironmentCaster
            Instance of the EnvironmentCaster class.

        Returns
        -------
        str
            String in the format "<type_hint>:<value>", where <type_hint> is the
            current type hint and <value> is the float value.

        Raises
        ------
        TypeError
            If the internal value cannot be converted to a float.
        ValueError
            If the internal value cannot be converted to a float due to invalid format.
        """
        # Use the value directly if it is already a float
        if isinstance(self.__value_raw, float):
            return f"{self.__type_hint}:{self.__value_raw!s}"

        # Try to convert string values to float
        if isinstance(self.__value_raw, str):
            try:
                converted_value = float(self.__value_raw.strip())
                return f"{self.__type_hint}:{converted_value!s}"
            except ValueError as e:
                error_msg = (
                    f"Cannot convert string '{self.__value_raw}' to float. "
                    "Value must be a valid floating-point representation."
                )
                raise ValueError(error_msg) from e

        # Attempt direct conversion for other types (e.g., int)
        try:
            converted_value = float(self.__value_raw)
            return f"{self.__type_hint}:{converted_value!s}"
        except (ValueError, TypeError) as e:
            error_msg = (
                f"Value must be convertible to float, got "
                f"{type(self.__value_raw).__name__} with value '{self.__value_raw}'."
            )
            raise TypeError(error_msg) from e

    def __parseBool(
        self,
    ) -> bool:
        """
        Convert the internal raw value to a boolean.

        Strips leading and trailing whitespace, converts to lowercase, and checks
        for common boolean representations. Returns True for 'true', '1', 'yes',
        'on', 'enabled'. Returns False for 'false', '0', 'no', 'off', 'disabled'.
        Raises ValueError if the value does not match any valid representation.

        Returns
        -------
        bool
            True or False based on the value's representation.

        Raises
        ------
        ValueError
            If the value cannot be converted to a boolean.
        """
        # Normalize and check common boolean representations
        value = self.__value_raw.strip().lower()

        if value in ("true", "1", "yes", "on", "enabled"):
            return True

        if value in ("false", "0", "no", "off", "disabled"):
            return False

        error_msg = (
            f"Cannot convert '{value}' to bool. Valid representations are: "
            "true/false, 1/0, yes/no, on/off, enabled/disabled."
        )
        raise ValueError(error_msg)

    def __toBool(
        self,
    ) -> str:
        """
        Convert the internal value to a boolean string with type hint prefix.

        Converts the internal value to a string representation of a boolean,
        prefixed by the type hint. Accepts common boolean representations for
        string inputs.

        Parameters
        ----------
        self : EnvironmentCaster
            Instance of the EnvironmentCaster class.

        Returns
        -------
        str
            String in the format "<type_hint>:<value>", where <value> is
            'true' or 'false' in lowercase.

        Raises
        ------
        ValueError
            If the internal value cannot be converted to a boolean.
        TypeError
            If the value type is not convertible to boolean.
        """
        # Use the value directly if it is already a boolean
        if isinstance(self.__value_raw, bool):
            return f"{self.__type_hint}:{str(self.__value_raw).lower()}"

        # Handle string inputs with common boolean representations
        if isinstance(self.__value_raw, str):
            str_value = self.__value_raw.strip().lower()
            if str_value in ("true", "1", "yes", "on", "enabled"):
                return f"{self.__type_hint}:true"
            if str_value in ("false", "0", "no", "off", "disabled"):
                return f"{self.__type_hint}:false"
            error_msg = (
                f"Cannot convert string '{self.__value_raw}' to boolean. "
                "Valid representations: "
                "true/false, 1/0, yes/no, on/off, enabled/disabled."
            )
            raise ValueError(error_msg)

        # For other types, use Python's truthiness
        try:
            boolean_value = bool(self.__value_raw)
            return f"{self.__type_hint}:{str(boolean_value).lower()}"
        except Exception as e:
            error_msg = (
                f"Value must be convertible to boolean, got "
                f"{type(self.__value_raw).__name__} with value '{self.__value_raw}'."
            )
            raise TypeError(error_msg) from e

    def __parseList(
        self,
    ) -> list:
        """
        Parse the internal raw value and convert it to a Python list.

        Strips leading and trailing whitespace from the internal raw value,
        then safely evaluates the string as a Python list using `ast.literal_eval`.
        Raises an exception if the conversion fails or the result is not a list.

        Returns
        -------
        list
            The internal value converted to a list.

        Raises
        ------
        ValueError
            If the value cannot be converted to a list due to invalid format.
        SyntaxError
            If the value contains invalid Python syntax.
        TypeError
            If the evaluated value is not a list.
        """
        # Clean input by stripping whitespace
        value = self.__value_raw.strip()

        try:
            # Safely evaluate the string to a Python object
            parsed = ast.literal_eval(value)
            if not isinstance(parsed, list):
                error_msg = "Value is not a list"
                raise TypeError(error_msg)
            return parsed
        except (ValueError, SyntaxError, TypeError) as e:
            error_msg = str(e)
            raise type(e)(error_msg) from e

    def __toList(
        self,
    ) -> str:
        """
        Convert the internal value to a string representation with list type hint.

        Returns
        -------
        str
            String in the format "<type_hint>:<value>", where <type_hint> is the
            current type hint and <value> is the string representation of the list.

        Raises
        ------
        TypeError
            If the internal value is not a list.
        """
        # Ensure the internal value is a list before conversion
        if not isinstance(self.__value_raw, list):
            error_msg = (
                f"Value must be a list to convert to list, got "
                f"{type(self.__value_raw).__name__} instead."
            )
            raise TypeError(error_msg)

        # Return the formatted string with type hint and list value
        return f"{self.__type_hint}:{self.__value_raw!r}"

    def __parseDict(
        self,
    ) -> dict:
        """
        Parse the internal raw value and convert it to a Python dictionary.

        Strips leading and trailing whitespace from the internal raw value,
        then safely evaluates the string as a Python dictionary using
        `ast.literal_eval`. Raises an error if the conversion fails or the
        result is not a dictionary.

        Returns
        -------
        dict
            The internal value converted to a dictionary.

        Raises
        ------
        ValueError
            If the value cannot be converted to a dictionary due to invalid
            format or type.
        """
        # Clean input by stripping whitespace
        value = self.__value_raw.strip()

        try:
            # Safely evaluate the string to a Python object
            parsed = ast.literal_eval(value)
            if not isinstance(parsed, dict):
                error_msg = "Value is not a dict"
                raise TypeError(error_msg)
            return parsed
        except (ValueError, SyntaxError, TypeError) as e:
            error_msg = f"Cannot convert '{value}' to dict: {e!s}"
            raise ValueError(error_msg) from e

    def __toDict(
        self,
    ) -> str:
        """
        Convert the internal value to a string with dictionary type hint prefix.

        Parameters
        ----------
        self : EnvironmentCaster
            Instance of the EnvironmentCaster class.

        Returns
        -------
        str
            String in the format "<type_hint>:<value>", where <type_hint> is the
            current type hint and <value> is the string representation of the dict.

        Raises
        ------
        TypeError
            If the internal value is not a dictionary.
        """
        # Ensure the internal value is a dictionary before conversion
        if not isinstance(self.__value_raw, dict):
            error_msg = (
                f"Value must be a dict to convert to dict, got "
                f"{type(self.__value_raw).__name__} instead."
            )
            raise TypeError(error_msg)

        # Return the formatted string with type hint and dictionary value
        return f"{self.__type_hint}:{self.__value_raw!r}"

    def __parseTuple(
        self,
    ) -> tuple:
        """
        Parse the internal raw value and convert it to a Python tuple.

        Remove leading and trailing whitespace from the internal raw value,
        then safely evaluate the string as a Python tuple using `ast.literal_eval`.
        Raise a ValueError if conversion fails or the result is not a tuple.

        Returns
        -------
        tuple
            The internal value converted to a tuple.

        Raises
        ------
        ValueError
            If the value cannot be converted to a tuple due to invalid format or type.
        TypeError
            If the evaluated value is not a tuple.
        """
        # Clean input by stripping whitespace
        value = self.__value_raw.strip()

        try:
            # Safely evaluate the string to a Python object
            parsed = ast.literal_eval(value)
            if not isinstance(parsed, tuple):
                error_msg = "Value is not a tuple"
                raise TypeError(error_msg)
            return parsed
        except (ValueError, SyntaxError, TypeError) as e:
            error_msg = f"Cannot convert '{value}' to tuple: {e!s}"
            raise ValueError(error_msg) from e

    def __toTuple(
        self,
    ) -> str:
        """
        Convert the internal value to a string with the tuple type hint prefix.

        Parameters
        ----------
        self : EnvironmentCaster
            Instance of the EnvironmentCaster class.

        Returns
        -------
        str
            String in the format "<type_hint>:<value>", where <type_hint> is the
            current type hint and <value> is the string representation of the tuple.

        Raises
        ------
        TypeError
            If the internal value is not a tuple.
        """
        # Ensure the internal value is a tuple before conversion
        if not isinstance(self.__value_raw, tuple):
            error_msg = (
                f"Value must be a tuple to convert to tuple, got "
                f"{type(self.__value_raw).__name__} instead."
            )
            raise TypeError(error_msg)

        # Return the formatted string with type hint and tuple value
        return f"{self.__type_hint}:{self.__value_raw!r}"

    def __parseSet(
        self,
    ) -> set:
        """
        Parse the internal raw value and convert it to a Python set.

        Remove leading and trailing whitespace from the internal raw value,
        then safely evaluate the string as a Python set using `ast.literal_eval`.
        Raise a TypeError if the result is not a set, or a ValueError if the
        conversion fails.

        Returns
        -------
        set
            The internal value converted to a set.

        Raises
        ------
        TypeError
            If the evaluated value is not a set.
        ValueError
            If the value cannot be converted to a set due to invalid format or type.
        """
        # Strip whitespace from the raw value before evaluation
        value = self.__value_raw.strip()

        try:
            # Safely evaluate the string to a Python object
            parsed = ast.literal_eval(value)
            if not isinstance(parsed, set):
                error_msg = "Value is not a set"
                raise TypeError(error_msg)
            return parsed
        except (ValueError, SyntaxError, TypeError) as e:
            error_msg = f"Cannot convert '{value}' to set: {e!s}"
            raise ValueError(error_msg) from e

    def __toSet(
        self,
    ) -> str:
        """
        Convert the internal value to a string with the set type hint prefix.

        Parameters
        ----------
        self : EnvironmentCaster
            Instance of the EnvironmentCaster class.

        Returns
        -------
        str
            String in the format "<type_hint>:<value>", where <type_hint> is the
            current type hint and <value> is the string representation of the set.

        Raises
        ------
        TypeError
            If the internal value is not a set.
        """
        # Ensure the internal value is a set before conversion
        if not isinstance(self.__value_raw, set):
            error_msg = (
                f"Value must be a set to convert to set, got "
                f"{type(self.__value_raw).__name__} instead."
            )
            raise TypeError(error_msg)

        # Return the formatted string with type hint and set value
        return f"{self.__type_hint}:{self.__value_raw!r}"
