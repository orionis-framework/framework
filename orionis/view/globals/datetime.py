from __future__ import annotations
from typing import TYPE_CHECKING, Any
from orionis.support.facades.datetime import DateTime

if TYPE_CHECKING:
    import pendulum

# ruff: noqa: ANN401

def _global_now() -> Any:
    """
    Build the ``now`` template global.

    Returns
    -------
    Any
        Callable returning the current date and time.
    """
    def now() -> pendulum.DateTime:
        """
        Return the current date and time.

        Returns
        -------
        DateTime
            The current date and time.
        """
        return DateTime.now()

    return now

def _global_today() -> Any:
    """
    Build the ``today`` template global.

    Returns
    -------
    Any
        Callable returning the current date without time component.
    """
    def today() -> pendulum.Date:
        """
        Return the current date without time component.

        Returns
        -------
        Date
            The current date in the configured timezone.
        """
        return DateTime.today()

    return today
