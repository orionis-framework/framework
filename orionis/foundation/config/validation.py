from __future__ import annotations
from http.cookies import CookieError, SimpleCookie
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from enum import Enum

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
        raise ValueError(error_msg + ".")

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
    # Match both member names and string representations without case.
    for member_name, member in enum_type.__members__.items():
        if normalized in {member_name.casefold(), str(member.value).casefold()}:
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
