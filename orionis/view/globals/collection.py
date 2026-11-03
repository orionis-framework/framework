"""Provide view globals operations through ``_global_collect``."""

from __future__ import annotations
from collections.abc import Iterable
from typing import Any
from orionis.support.types.collection import Collection

# ruff: noqa: ANN401

def _global_collect() -> Any:
    """
    Build the ``collect`` template global.

    Returns
    -------
    typing.Any
        Callable wrapping a value in a :class:`collections.abc.Collection` instance.
    """
    def collect(value: Any = None) -> Collection:
        """
        Wrap a value in a fluent :class:`collections.abc.Collection` instance.

        Parameters
        ----------
        value : typing.Any, optional
            Value to wrap.  Iterables are expanded into items, scalars
            are wrapped as a single-item collection, and ``None``
            produces an empty collection.

        Returns
        -------
        collections.abc.Collection
            Fluent collection exposing the collection helper API.
        """
        if value is None:
            return Collection()
        if isinstance(value, Collection):
            return value
        if isinstance(value, list):
            return Collection(value)

        # Strings and bytes are iterable but must stay a single item
        if isinstance(value, str | bytes) or not isinstance(value, Iterable):
            return Collection([value])

        return Collection(list(value))

    return collect
