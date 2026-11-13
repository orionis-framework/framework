# ruff: noqa: ANN401
# Preserve heterogeneous template payload values.
"""Provide view globals operations through ``_global_collect``."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from orionis.support.types.collection import Collection


def _global_collect() -> Callable[..., Collection]:
    """
    Build the ``collect`` template global.

    Returns
    -------
    collections.abc.Callable
        Callable wrapping a value in the framework collection type.
    """

    def collect(value: Any = None) -> Collection:
        """
        Wrap a value in a fluent framework collection.

        Parameters
        ----------
        value : typing.Any, optional
            Value to wrap.  Iterables are expanded into items, scalars
            are wrapped as a single-item collection, and ``None``
            produces an empty collection.

        Returns
        -------
        orionis.support.types.collection.Collection
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
