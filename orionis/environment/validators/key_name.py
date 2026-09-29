from __future__ import annotations
import re
import functools

# Precompile the regex pattern for validating environment variable names.
_pattern = re.compile(r"^[A-Z][A-Z0-9_]*$")

@functools.lru_cache(maxsize=512)
def _validate_key_name(key: str) -> str:
    """
    Validate that the provided environment variable name meets requirements.

    Parameters
    ----------
    key : str
        The environment variable name to validate.

    Returns
    -------
    str
        The validated environment variable name if it meets format requirements.

    Raises
    ------
    TypeError
        If the provided key is not a string.
    ValueError
        If the key does not match the required format (must start with an
        uppercase letter and contain only uppercase letters, digits, or
        underscores).

    Notes
    -----
    Pure function — safe to cache with lru_cache. After the first call per
    unique key, validation is an O(1) dict lookup instead of a regex match.
    """
    # Ensure the key is of type string
    if not isinstance(key, str):
        error_msg = (
            f"Environment variable name must be a string, got "
            f"{type(key).__name__}."
        )
        raise TypeError(error_msg)

    # Check if the key matches the required pattern for environment names
    if not _pattern.fullmatch(key):
        error_msg = (
            f"Invalid environment variable name '{key}'. It must start "
            "with an uppercase letter, contain only uppercase letters, "
            "numbers, or underscores. Example: 'MY_ENV_VAR'."
        )
        raise ValueError(error_msg)

    # Return the validated key if all checks pass
    return key

# Callable alias — preserves the original public interface
ValidateKeyName = _validate_key_name
