# ruff: noqa: PLR0911, TC003
# Structural dispatch returns early; public Callable hints resolve at runtime.
"""Provide support types operations through ``unique_items``."""

from __future__ import annotations
from collections.abc import Callable

_UNSUPPORTED = object()
"""Sentinel distinguishing unsupported from ordinary values."""
_SCALARS = {str, bytes, int, float, complex, bool, type(None)}
"""Exact scalar types whose native equality supports structural indexing."""
_SMALL_INPUT = 128
"""Maximum input size for which linear unhashable comparison avoids index overhead."""


def _structural_key(value: object, active: set[int]) -> object:
    """
    Build equality-compatible keys only for exact built-in value trees.

    Parameters
    ----------
    value : object
        Value to represent with a structural equality key.
    active : set[int]
        Container identities on the current recursion path.

    Returns
    -------
    object
        Equality key, or the unsupported sentinel for custom or cyclic values.
    """
    kind = type(value)
    if kind in _SCALARS:
        return value
    if kind is bytearray:
        return bytes(value)
    if kind not in (list, tuple, dict, set, frozenset) or id(value) in active:
        return _UNSUPPORTED
    active.add(id(value))
    try:
        if kind is dict:
            pairs = []
            for key, item in value.items():
                left = _structural_key(key, active)
                right = _structural_key(item, active)
                if left is _UNSUPPORTED or right is _UNSUPPORTED:
                    return _UNSUPPORTED
                pairs.append((left, right))
            return (dict, frozenset(pairs))
        children = []
        for item in value:
            key = _structural_key(item, active)
            if key is _UNSUPPORTED:
                return _UNSUPPORTED
            children.append(key)
        if kind in (set, frozenset):
            return (frozenset, frozenset(children))
        return (kind, tuple(children))
    finally:
        active.remove(id(value))


def unique_items[T](
    items: list[T],
    selector: Callable[[T], object],
) -> list[T]:
    """
    Preserve the first item for each equality key, with a safe tree fast path.

    Parameters
    ----------
    items : list[``T``]
        Values whose order and identity are preserved.
    selector : collections.abc.Callable[[``T``], object]
        Explicit business identity, or the value itself.

    Returns
    -------
    list[``T``]
        First representatives. Arbitrary unhashable objects and cycles retain
        Python equality fallback; no universal hash is assumed for custom types.
    """
    comparisons = [selector(item) for item in items]
    keys = _comparison_keys(comparisons)
    if keys is None:
        seen_values = []
        result = []
        for item, value in zip(items, comparisons, strict=True):
            if value not in seen_values:
                seen_values.append(value)
                result.append(item)
        return result
    seen = set()
    result = []
    for item, key in zip(items, keys, strict=True):
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _comparison_keys(comparisons: list[object]) -> list[object] | None:
    """
    Build hashable equality keys or select the linear comparison fallback.

    Parameters
    ----------
    comparisons : list[object]
        Selector results in input order.

    Returns
    -------
    list[object] or None
        Hashable keys, or None for custom, cyclic or small unhashable inputs.
    """
    try:
        set(comparisons)
    except TypeError:
        if len(comparisons) <= _SMALL_INPUT:
            return None
        try:
            keys = [_structural_key(value, set()) for value in comparisons]
        except RecursionError:
            return None
        return None if any(key is _UNSUPPORTED for key in keys) else keys
    return comparisons
