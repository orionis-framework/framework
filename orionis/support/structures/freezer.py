"""Convert nested mutable structures to immutable snapshots and back."""

from __future__ import annotations
from types import MappingProxyType
from typing import Any

_CONTAINER_TYPES: tuple[type, ...] = (dict, list, tuple, MappingProxyType)
"""Container types traversed when constructing a mutable snapshot."""
_MUTABLE_TYPES: tuple[type, ...] = (dict, list, tuple)
"""Mutable types definitions used by ``freezer``."""


def _mutable_graph(
    obj: object,
) -> tuple[dict[int, Any], list[tuple[Any, Any]]]:
    """Copy graph containers and record edges that require reference updates.

    Parameters
    ----------
    obj : object
        Root container to traverse without recursion.

    Returns
    -------
    tuple[dict[int, typing.Any], list[tuple[typing.Any, typing.Any]]]
        Mutable copies indexed by original identity and their pending edges.
    """
    stack = [obj]
    cache: dict[int, Any] = {}
    fixups: list[tuple[Any, Any]] = []
    while stack:
        current = stack.pop()
        current_id = id(current)
        if current_id in cache:
            continue
        new_obj = (
            dict(current)
            if isinstance(current, (MappingProxyType, dict))
            else list(current)
        )
        cache[current_id] = new_obj
        entries = new_obj.items() if isinstance(new_obj, dict) else enumerate(new_obj)
        for key, value in entries:
            if isinstance(value, _CONTAINER_TYPES):
                stack.append(value)
                fixups.append((new_obj, key))
    return cache, fixups


def _freeze_sequences(
    sequences: dict[int, list | tuple],
    cache: dict[int, Any],
) -> None:
    """Resolve sequence dependencies and cache their immutable tuple snapshots.

    Parameters
    ----------
    sequences : dict[int, list | tuple]
        Original sequences indexed by identity.
    cache : dict[int, typing.Any]
        Completed snapshots, including preallocated mapping proxies.

    Returns
    -------
    None
        No return value.

    Raises
    ------
    ValueError
        If a cycle consists entirely of sequences.
    """
    active: set[int] = set()
    for sequence_id in sequences:
        stack = [(sequence_id, False)]
        while stack:
            current_id, expanded = stack.pop()
            if current_id in cache:
                continue
            current = sequences[current_id]
            if expanded:
                cache[current_id] = tuple(
                    cache.get(id(value), value) for value in current
                )
                active.remove(current_id)
                continue
            if current_id in active:
                error_msg = "Cannot freeze a cycle containing only sequences."
                raise ValueError(error_msg)
            active.add(current_id)
            stack.append((current_id, True))
            stack.extend(
                (id(value), False)
                for value in current
                if id(value) in sequences and id(value) not in cache
            )


class FreezeThaw:
    """Convert nested mutable structures to immutable snapshots and back."""

    @staticmethod
    def thaw(obj: object) -> object:
        """
        Recursively convert frozen containers to mutable equivalents.

        Parameters
        ----------
        obj : object
            The object to thaw. Can be a MappingProxyType, dict, list, or tuple.

        Returns
        -------
        object
            A fully mutable object with preserved references. Non-container
            objects are returned unchanged.
        """
        if not isinstance(obj, _CONTAINER_TYPES):
            return obj

        # Fast-path: empty containers require no traversal or cache
        if not obj:
            return {} if isinstance(obj, (MappingProxyType, dict)) else []

        cache, fixups = _mutable_graph(obj)
        for container, key in fixups:
            container[key] = cache[id(container[key])]
        return cache[id(obj)]

    @staticmethod
    def freeze(obj: object) -> object:
        """
        Convert mutable containers to immutable equivalents recursively.

        Parameters
        ----------
        obj : object
            The object to freeze. Can be a dict, list, or tuple.

        Returns
        -------
        object
            A fully immutable object with preserved references. Non-container
            objects or MappingProxyType are returned unchanged.

        Raises
        ------
        ValueError
            If a cycle consists entirely of lists or tuples, which cannot be
            represented by immutable tuples. Cycles through dictionaries retain
            their references through mapping proxies.
        """
        # MappingProxyType is already immutable; not in _MUTABLE_TYPES -> return as-is
        if not isinstance(obj, _MUTABLE_TYPES):
            return obj

        # Fast-path: empty containers require no traversal
        if not obj:
            return MappingProxyType({}) if isinstance(obj, dict) else ()

        stack: list[object] = [obj]
        cache: dict[int, Any] = {}
        sequences: dict[int, list | tuple] = {}
        mappings: list[tuple[dict, dict]] = []

        while stack:
            current = stack.pop()
            c_id = id(current)
            if c_id in cache or c_id in sequences:
                continue

            if isinstance(current, dict):
                backing: dict[Any, Any] = {}
                cache[c_id] = MappingProxyType(backing)
                mappings.append((current, backing))
                values = current.values()
            else:
                sequences[c_id] = current
                values = current
            stack.extend(value for value in values if isinstance(value, _MUTABLE_TYPES))

        _freeze_sequences(sequences, cache)
        for original, backing in mappings:
            backing.update(
                (key, cache.get(id(value), value)) for key, value in original.items()
            )
        return cache[id(obj)]
