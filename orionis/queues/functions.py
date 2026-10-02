import math
import re
from orionis.queues.exceptions import QueueConfigurationError
from orionis.support.facades.datetime import DateTime

_NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")

def validate_name(value: str, label: str) -> str:
    """
    Validate a logical queue or connection name.

    Parameters
    ----------
    value : str
        Name supplied by configuration or a caller.
    label : str
        Description included in validation errors.

    Returns
    -------
    str
        The validated name.
    """
    if not isinstance(value, str) or _NAME_PATTERN.fullmatch(value) is None:
        message = f"{label} must contain 1-128 letters, digits, '.', '_' or '-'."
        raise QueueConfigurationError(message)
    return value


def validate_seconds(
    value: float,
    label: str,
    *,
    positive: bool = False,
) -> float:
    """
    Validate a finite duration in seconds.

    Parameters
    ----------
    value : float
        Duration to validate.
    label : str
        Description included in validation errors.
    positive : bool, optional
        Require a strictly positive duration.

    Returns
    -------
    float
        The normalized duration.
    """
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
        or (positive and value == 0)
    ):
        requirement = "positive" if positive else "nonnegative"
        message = f"{label} must be finite and {requirement}."
        raise QueueConfigurationError(message)
    return float(value)


def current_time() -> float:
    """
    Return wall-clock epoch seconds with sub-second precision.

    Returns
    -------
    float
        Current time from the framework's DateTime abstraction.
    """
    return DateTime.now().timestamp()
