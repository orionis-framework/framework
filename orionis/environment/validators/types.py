from __future__ import annotations
import functools
from orionis.environment.enums.value_type import EnvironmentValueType

# Pre-build allowed types list once — avoids repeated list comprehension in error paths
_ALLOWED_TYPE_HINT_VALUES: list[str] = [e.value for e in EnvironmentValueType]

@functools.lru_cache(maxsize=64)
def _normalize_type_hint(type_hint: str | EnvironmentValueType) -> str:
    """
    Normalize and validate a type hint, returning its canonical string value.

    Cached with lru_cache — type hints are a finite, known set so repeated
    calls with the same hint become O(1) dict lookups after the first call.

    Parameters
    ----------
    type_hint : str or EnvironmentValueType
        The type hint to normalize.

    Returns
    -------
    str
        The canonical string value of the type hint.

    Raises
    ------
    RuntimeError
        If the type hint string is not a valid EnvironmentValueType name.
    """
    if isinstance(type_hint, EnvironmentValueType):
        return type_hint.value
    # type_hint is str
    try:
        return EnvironmentValueType[type_hint.upper()].value
    except KeyError:
        error_msg = (
            f"Invalid type hint: {type_hint}. "
            f"Allowed types are: {_ALLOWED_TYPE_HINT_VALUES}"
        )
        raise RuntimeError(error_msg) from None


class __ValidateTypes:

    def __call__(
        self,
        *,
        value: str | float | bool | list | dict | tuple | set,
        type_hint: str | EnvironmentValueType | None = None,
    ) -> str:
        """
        Validate and determine the type of a given value.

        Parameters
        ----------
        value : str, int, float, bool, list, dict, tuple, or set
            The value whose type is to be validated and determined.
        type_hint : str or EnvironmentValueType, optional
            An optional type hint specifying the expected type. Can be a string
            or an EnvironmentValueType.

        Returns
        -------
        str
            The determined type as a string, either from the type hint or
            inferred from the value.

        Raises
        ------
        TypeError
            If value type is unsupported or type_hint has invalid type.
        RuntimeError
            If type_hint is not a valid EnvironmentValueType.
        """
        # Validate that the value is of a supported type
        if not isinstance(value, (str, int, float, bool, list, dict, tuple, set)):
            error_msg = (
                f"Unsupported value type: {type(value).__name__}. "
                f"Allowed types are str, int, float, bool, list, dict, tuple, set."
            )
            raise TypeError(error_msg)

        # Validate type hint if provided (use 'is not None' to avoid skipping
        # validation for falsy but invalid values such as 0 or empty string)
        if (
            type_hint is not None and
            not isinstance(type_hint, (str, EnvironmentValueType))
        ):
            error_msg = (
                f"Type hint must be a string or EnvironmentValueType, "
                f"got {type(type_hint).__name__}."
            )
            raise TypeError(error_msg)

        # Process type hint if provided and not None
        if type_hint is not None:
            # Cached normalization — O(1) after first call per unique type_hint
            return _normalize_type_hint(type_hint)

        # Use inferred type if no type hint provided
        return type(value).__name__.lower()

# Instance to be used for key name validation
ValidateTypes = __ValidateTypes()
