from __future__ import annotations
import re
from functools import lru_cache
from http.cookies import CookieError, SimpleCookie
from math import isfinite
from types import MappingProxyType
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from enum import Enum
    from orionis.foundation.config.queue.enums.drivers import Drivers

_NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")
_TABLE_PATTERN = re.compile(r"[A-Za-z_]\w*", re.ASCII)
_STORE_TABLE_PATTERN = re.compile(r"[a-z_]+")
_MAX_STORE_PORT = 65535
_ENUM_SCALAR_TYPES = frozenset({str, bytes, int, float, complex, bool, type(None)})

def validate_integer(
    value: object,
    name: str,
    *,
    minimum: int = 0,
    maximum: int | None = None,
) -> None:
    """
    Validate an integer within an inclusive range.

    Parameters
    ----------
    value : object
        Value to validate.
    name : str
        Field name used in validation errors.
    minimum : int, optional
        Minimum allowed value, inclusive.
    maximum : int | None, optional
        Maximum allowed value, inclusive, or ``None`` for no upper bound.

    Returns
    -------
    None
        This function validates the value without returning a result.

    Raises
    ------
    TypeError
        If ``value`` is not an integer or is a boolean.
    ValueError
        If ``value`` is outside the configured range.
    """
    # Booleans are integers in Python, so reject them explicitly.
    if not isinstance(value, int) or isinstance(value, bool):
        error_msg = f"'{name}' must be an integer."
        raise TypeError(error_msg)
    if value < minimum or (maximum is not None and value > maximum):
        error_msg = f"'{name}' must be at least {minimum}"
        if maximum is not None:
            error_msg += f" and at most {maximum}"
        error_msg = error_msg + "."
        raise ValueError(error_msg)

def validate_string(value: object, name: str, *, allow_empty: bool = False) -> None:
    """
    Validate a string and optionally allow blank values.

    Parameters
    ----------
    value : object
        Value to validate.
    name : str
        Field name used in validation errors.
    allow_empty : bool, optional
        Whether to allow strings containing only whitespace.

    Returns
    -------
    None
        This function validates the value without returning a result.

    Raises
    ------
    TypeError
        If ``value`` is not a string.
    ValueError
        If ``value`` is blank and empty strings are not allowed.
    """
    # Check the type before calling string methods on the value.
    if not isinstance(value, str):
        error_msg = f"'{name}' must be a string."
        raise TypeError(error_msg)
    if not allow_empty and not value.strip():
        error_msg = f"'{name}' cannot be empty."
        raise ValueError(error_msg)

def validate_boolean(value: object, name: str) -> None:
    """
    Require a boolean without coercing truthy values.

    Parameters
    ----------
    value : object
        Value to validate.
    name : str
        Field name used in validation errors.

    Returns
    -------
    None
        This function validates the value without returning a result.

    Raises
    ------
    TypeError
        If ``value`` is not a boolean.
    """
    # Require the exact boolean type rather than truthiness.
    if not isinstance(value, bool):
        error_msg = f"'{name}' must be a boolean."
        raise TypeError(error_msg)

@lru_cache(maxsize=64)
def _enum_values(
    enum_type: type[Enum],
    _member_count: int,
) -> MappingProxyType | None:
    """
    Index enum names and values in declaration order.

    Parameters
    ----------
    enum_type : type[Enum]
        Enum class defining the accepted names and values.
    _member_count : int
        Number of declared names, including aliases, used as a cache revision.

    Returns
    -------
    MappingProxyType or None
        Read-only scalar lookup preserving declaration order, or None when values
        require their current string representation on every lookup.
    """
    values = {}
    for member_name, member in enum_type.__members__.items():
        if type(member.value) not in _ENUM_SCALAR_TYPES:
            return None
        values.setdefault(member_name.casefold(), member.value)
        values.setdefault(str(member.value).casefold(), member.value)
    return MappingProxyType(values)

def normalize_enum(value: object, enum_type: type[Enum], name: str) -> object:
    """
    Normalize an enum member, member name, or string value.

    Parameters
    ----------
    value : object
        Enum member, member name, or string value to normalize.
    enum_type : type[Enum]
        Enum class that defines the accepted members.
    name : str
        Field name used in validation errors.

    Returns
    -------
    object
        The normalized enum member value.

    Raises
    ------
    TypeError
        If ``value`` is neither an enum member nor a string.
    ValueError
        If the string does not match an enum member or value.
    """
    if isinstance(value, enum_type):
        return value.value
    if not isinstance(value, str):
        error_msg = f"'{name}' must be a string or {enum_type.__name__}."
        raise TypeError(error_msg)
    normalized = value.strip().casefold()
    values = _enum_values(enum_type, len(enum_type.__members__))
    if values is not None:
        try:
            return values[normalized]
        except KeyError:
            pass
    else:
        for member_name, member in enum_type.__members__.items():
            if (
                normalized == member_name.casefold()
                or normalized == str(member.value).casefold()
            ):
                return member.value
    error_msg = f"'{name}' must be one of {list(enum_type.__members__)}."
    raise ValueError(error_msg)

def copy_string_list(value: object, name: str) -> list[str]:
    """
    Validate a list of non-empty strings and return an independent copy.

    Parameters
    ----------
    value : object
        List to validate and copy.
    name : str
        Field name used in validation errors.

    Returns
    -------
    list[str]
        A new list containing the validated strings.

    Raises
    ------
    TypeError
        If ``value`` is not a list or an item is not a string.
    ValueError
        If an item is blank.
    """
    # Validate every item before returning a separate list.
    if not isinstance(value, list):
        error_msg = f"'{name}' must be a list of strings."
        raise TypeError(error_msg)
    for item in value:
        validate_string(item, name)
    return list(value)

def validate_cookie_name(value: object, name: str) -> None:
    """
    Validate a cookie name with the HTTP response serializer.

    Parameters
    ----------
    value : object
        Cookie name to validate.
    name : str
        Field name used in validation errors.

    Returns
    -------
    None
        This function validates the name without returning a result.

    Raises
    ------
    TypeError
        If ``value`` is not a non-empty string.
    ValueError
        If the serializer rejects ``value`` as a cookie name.
    """
    # Use the response serializer so accepted names match HTTP behavior.
    validate_string(value, name)
    try:
        cookie = SimpleCookie()
        cookie[value] = ""
    except CookieError as exc:
        error_msg = f"'{name}' must be a valid cookie name."
        raise ValueError(error_msg) from exc

def validate_name(value: object, name: str, *, table: bool = False) -> None:
    """
    Require a safe connection, queue, or SQL table identifier.

    Parameters
    ----------
    value : object
        Identifier to validate.
    name : str
        Configuration field used in errors.
    table : bool, optional
        Restrict the identifier to an unqualified SQL table name.

    Returns
    -------
    None
        Validate the identifier without changing it.

    Raises
    ------
    TypeError
        If the identifier is not a string.
    ValueError
        If the identifier is empty or unsafe.
    """
    validate_string(value, name)
    pattern = _TABLE_PATTERN if table else _NAME_PATTERN
    if pattern.fullmatch(value) is None:
        error_msg = f"'{name}' must be a valid identifier."
        raise ValueError(error_msg)

def validate_seconds(value: object, name: str, *, positive: bool = False) -> None:
    """
    Require finite nonnegative or strictly positive seconds.

    Parameters
    ----------
    value : object
        Numeric duration to validate.
    name : str
        Configuration field used in errors.
    positive : bool, optional
        Reject zero when true.

    Returns
    -------
    None
        Validate the duration without coercion.

    Raises
    ------
    TypeError
        If the duration is not numeric or is a boolean.
    ValueError
        If the duration is nonfinite or outside its allowed range.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        error_msg = f"'{name}' must be a number of seconds."
        raise TypeError(error_msg)
    if not isfinite(value) or value < 0 or (positive and value == 0):
        constraint = "positive" if positive else "nonnegative"
        error_msg = f"'{name}' must contain finite {constraint} seconds."
        raise ValueError(error_msg)

def validate_driver(value: object, expected: Drivers) -> None:
    """
    Require the driver implemented by a connection entity.

    Parameters
    ----------
    value : object
        Configured driver name or enum member.
    expected : Drivers
        Driver supported by the entity.

    Returns
    -------
    None
        Validate the driver without changing its representation.

    Raises
    ------
    TypeError
        If the driver is not a string or string enum.
    ValueError
        If the driver does not match the connection entity.
    """
    validate_string(value, "driver")
    if value != expected:
        error_msg = f"'driver' must be '{expected}' for this queue connection."
        raise ValueError(error_msg)

def validate_http_origin(origin: str) -> None:
    """
    Require an explicit serialized HTTP(S) origin without wildcards.

    Parameters
    ----------
    origin : str
        One trusted browser origin from configuration.

    Returns
    -------
    None
        Accept the validated origin without changing its spelling.

    Raises
    ------
    TypeError
        If the configured origin is not a string.
    ValueError
        If its syntax could permit ambiguous or unrestricted matching.
    """
    if not isinstance(origin, str):
        error_msg = "allowed_origins entries must be strings"
        raise TypeError(error_msg)
    if (
        not origin
        or not origin.isascii()
        or any(
            char.isspace() or not char.isprintable() or char in "*\\" for char in origin
        )
    ):
        error_msg = "allowed_origins entries must be explicit ASCII HTTP(S) origins"
        raise ValueError(error_msg)
    parsed = urlsplit(origin)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or "?" in origin
        or "#" in origin
    ):
        error_msg = "allowed_origins entries must contain only scheme and authority"
        raise ValueError(error_msg)
    if parsed.port == 0 or parsed.netloc.endswith(":"):
        error_msg = "allowed_origins entries must use a valid nonzero port"
        raise ValueError(error_msg)

def validate_store_table(
    value: object,
    name: str = "table",
    *,
    optional: bool = False,
) -> None:
    """
    Validate cache/scheduler table names without widening their accepted syntax.

    Parameters
    ----------
    value : object
        Configured table name.
    name : str
        Property reported in validation errors.
    optional : bool
        Whether None is accepted for an optional lock table.

    Returns
    -------
    None
        Accept lowercase letters and underscores, preserving store diagnostics.
    """
    if optional and value is None:
        return
    if not isinstance(value, str):
        suffix = " or None" if optional else ""
        error_msg = f"The '{name}' property must be a string{suffix}."
        raise TypeError(error_msg)
    if not _STORE_TABLE_PATTERN.fullmatch(value):
        error_msg = (
            f"The '{name}' property must be a valid table name: contain "
            "only lowercase letters or underscores (no numbers allowed)."
        )
        raise ValueError(error_msg)

def validate_store_port(value: object) -> None:
    """
    Validate Redis/Memcached ports using the existing store error messages.

    Parameters
    ----------
    value : object
        TCP port, excluding booleans.

    Returns
    -------
    None
        Accept integers from one through 65535.
    """
    if not isinstance(value, int) or isinstance(value, bool):
        error_msg = "The 'port' property must be an integer."
        raise TypeError(error_msg)
    if not 1 <= value <= _MAX_STORE_PORT:
        error_msg = f"The 'port' property must be between 1 and {_MAX_STORE_PORT}."
        raise ValueError(error_msg)

def validate_store_db(value: object) -> None:
    """
    Validate the Redis database index for cache and scheduler stores.

    Parameters
    ----------
    value : object
        Redis database index, excluding booleans.

    Returns
    -------
    None
        Accept nonnegative integers.
    """
    if not isinstance(value, int) or isinstance(value, bool):
        error_msg = "The 'db' property must be an integer."
        raise TypeError(error_msg)
    if value < 0:
        error_msg = "The 'db' property cannot be negative."
        raise ValueError(error_msg)

def normalize_optional_store(owner: object, name: str, cls: type) -> None:
    """
    Convert optional cache/scheduler store dictionaries into typed entities.

    Parameters
    ----------
    owner : object
        Configuration entity whose field is normalized during initialization.
    name : str
        Field containing an entity, dict or None.
    cls : type
        Expected store entity type.

    Returns
    -------
    None
        Preserve disabled stores and assign converted entities to frozen owners.
    """
    value = getattr(owner, name)
    if value is None:
        return
    if not isinstance(value, (cls, dict)):
        error_msg = (
            f"The '{name}' attribute must be an instance of "
            f"{cls.__name__}, a dict, or None, but got "
            f"{type(value).__name__}."
        )
        raise TypeError(error_msg)
    if isinstance(value, dict):
        object.__setattr__(owner, name, cls(**value))
