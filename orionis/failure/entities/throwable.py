# ruff: noqa: TC003
# Preserve the traceback type for runtime entity and constructor inspection.
"""Represent a throwable entity within the framework."""

from __future__ import annotations
from dataclasses import dataclass
from types import TracebackType


@dataclass(frozen=True, kw_only=True, slots=True)
class Throwable:
    """
    Represent a throwable entity within the framework.

    Attributes
    ----------
    classtype : type
        The class type of the throwable, typically an exception class.
    message : str
        The error message describing the throwable.
    args : tuple
        Arguments passed to the throwable, usually corresponding to the
        exception arguments.
    traceback : types.TracebackType | None, optional
        The native traceback object, if available. Defaults to None.

    Returns
    -------
    orionis.failure.entities.Throwable
        An instance encapsulating exception details.
    """

    # The type of the throwable (e.g., Exception class)
    classtype: type

    # The error message associated with the throwable
    message: str

    # Arguments passed to the throwable
    args: tuple

    # Optional native traceback object
    traceback: TracebackType | None = None
