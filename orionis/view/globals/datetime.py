# ruff: noqa: TC002, TC003
# Keep public callback and application annotations resolvable at runtime.
"""Provide view globals operations through ``_global_now``, ``_global_today``."""

from __future__ import annotations

from collections.abc import Callable

import pendulum

from orionis.support.facades.datetime import DateTime


def _global_now() -> Callable[[], pendulum.DateTime]:
    """
    Build the ``now`` template global.

    Returns
    -------
    collections.abc.Callable
        Callable returning the current date and time.
    """

    def now() -> pendulum.DateTime:
        """
        Return the current date and time.

        Returns
        -------
        pendulum.DateTime
            The current date and time.
        """
        return DateTime.now()

    return now


def _global_today() -> Callable[[], pendulum.DateTime]:
    """
    Build the ``today`` template global.

    Returns
    -------
    collections.abc.Callable
        Callable returning the current date at midnight.
    """

    def today() -> pendulum.DateTime:
        """
        Return midnight on the current date in the configured timezone.

        Returns
        -------
        pendulum.DateTime
            The current date in the configured timezone.
        """
        return DateTime.today()

    return today
