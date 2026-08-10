from __future__ import annotations
from typing import Any
from orionis.support.types.stringable import Stringable

# ruff: noqa: ANN401

def _global_stringable() -> Any:
    """
    Build the ``stringable`` template global.

    Returns
    -------
    Any
        Callable wrapping a value in a :class:`Stringable` instance.
    """
    def stringable(value: Any = "") -> Stringable:
        """
        Wrap a value in a fluent :class:`Stringable` instance.

        Parameters
        ----------
        value : Any, optional
            Value to wrap.  Non-string values are converted with
            ``str()`` by the ``str`` constructor.

        Returns
        -------
        Stringable
            Fluent string wrapper exposing the string helper API.
        """
        return value if isinstance(value, Stringable) else Stringable(value)

    return stringable
