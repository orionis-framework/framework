# ruff: noqa: ANN401, TC003
# Keep public callback and application annotations resolvable at runtime.
# Preserve heterogeneous template payload values.
"""Provide view globals operations through ``_global_stringable``."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from orionis.support.types.stringable import Stringable


def _global_stringable() -> Callable[..., Stringable]:
    """
    Build the ``stringable`` template global.

    Returns
    -------
    collections.abc.Callable
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
