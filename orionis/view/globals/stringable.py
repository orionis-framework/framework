"""Provide view globals operations through ``_global_stringable``."""

from __future__ import annotations
from typing import Any
from orionis.support.types.stringable import Stringable

# ruff: noqa: ANN401

def _global_stringable() -> Any:
    """
    Build the ``stringable`` template global.

    Returns
    -------
    typing.Any
        Callable wrapping a value in a :class:`orionis.support.types.Stringable`
        instance.
    """
    def stringable(value: Any = "") -> Stringable:
        """
        Wrap a value in a fluent :class:`orionis.support.types.Stringable` instance.

        Parameters
        ----------
        value : typing.Any, optional
            Value to wrap.  Non-string values are converted with
            ``str()`` by the ``str`` constructor.

        Returns
        -------
        orionis.support.types.Stringable
            Fluent string wrapper exposing the string helper API.
        """
        return value if isinstance(value, Stringable) else Stringable(value)

    return stringable
