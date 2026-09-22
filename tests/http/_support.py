from __future__ import annotations
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

_MISSING = object()

@contextmanager
def replace_attribute(target: object, name: str, value: object) -> Iterator[None]:
    """
    Replace an attribute and restore its original ownership on exit.

    Parameters
    ----------
    target : object
        Object or class receiving the temporary attribute.
    name : str
        Attribute name to replace.
    value : object
        Value to expose inside the context.

    Yields
    ------
    None
        Control while the replacement is active.
    """
    try:
        original = vars(target).get(name, _MISSING)
    except TypeError:
        original = getattr(target, name, _MISSING)
    setattr(target, name, value)
    try:
        yield
    finally:
        if original is _MISSING:
            delattr(target, name)
        else:
            setattr(target, name, original)
