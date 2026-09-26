_MISSING = object()

# Parse a value into a boolean using the supported truthy strings.
# This helper accepts native booleans and common truthy string variants.
def parse_bool(valor: object) -> bool:
    """Parse a value as a boolean.

    Parameters
    ----------
    valor : object
        Value to parse.

    Returns
    -------
    bool
        ``True`` when the value is a boolean true or a supported truthy
        string; otherwise ``False``.
    """
    if isinstance(valor, bool):
        return valor

    return str(valor).strip().lower() in (
        "true",
        "1",
        "yes",
        "si",
        "sí",
        "on",
    )

# Convert an integer-like value with optional strict validation.
def parse_int(
    value: object,
    default: int | None = None,
    *,
    strict: bool = False,
) -> int | None:
    """Convert a value to an integer when possible.

    Parameters
    ----------
    value : object
        Value to convert.
    default : int | None, optional
        Value to return when conversion fails and ``strict`` is ``False``.
    strict : bool, optional
        Whether to raise an error instead of returning ``default``.

    Returns
    -------
    int | None
        The converted integer, ``default`` when conversion fails in lax mode,
        or ``None`` when ``value`` is ``None`` and no default is provided.

    Raises
    ------
    ValueError
        If ``strict`` is ``True`` and the value cannot be converted to an
        integer.
    """
    converted_value = _coerce_int(value)

    if converted_value is _MISSING:
        if strict:
            error_msg = f"Could not convert {value!r} to int."
            raise ValueError(error_msg)
        return default

    return converted_value

# Convert supported numeric values to an integer without raising errors.
def _coerce_int(value: object) -> int | object:
    """Coerce a value into an integer when supported.

    Parameters
    ----------
    value : object
        Value to convert.

    Returns
    -------
    int | object
        The converted integer or ``_MISSING`` when conversion is not possible.
    """
    if value is None:
        return _MISSING

    if isinstance(value, bool):
        return int(value)

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return _coerce_float(value)

    if not isinstance(value, str):
        return _MISSING

    return _coerce_string(value)

# Convert float values to integers when they represent whole numbers.
def _coerce_float(value: float) -> int | object:
    """Convert a whole-number float to an integer.

    Parameters
    ----------
    value : float
        Floating-point value to inspect.

    Returns
    -------
    int | object
        The integer value or ``_MISSING`` when it is not a whole number.
    """
    if value.is_integer():
        return int(value)

    return _MISSING

# Convert string values to integers when they represent whole numbers.
def _coerce_string(value: str) -> int | object:
    """Convert a normalized string value to an integer when possible.

    Parameters
    ----------
    value : str
        String to parse.

    Returns
    -------
    int | object
        The converted integer or ``_MISSING`` when no conversion is possible.
    """
    normalized = value.strip()

    if not normalized:
        return _MISSING

    return _coerce_string_candidate(normalized)

# Parse a string candidate using integer and float conversions.
def _coerce_string_candidate(value: str) -> int | object:
    """Attempt integer conversion for a string candidate.

    Parameters
    ----------
    value : str
        Candidate value to convert.

    Returns
    -------
    int | object
        The converted integer or ``_MISSING`` when conversion fails.
    """
    try:
        return int(value)
    except ValueError:
        pass

    try:
        number = float(value)
        if number.is_integer():
            return int(number)
    except ValueError:
        pass

    return _MISSING
