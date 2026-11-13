# ruff: noqa: TC003
# Expose the callable return type to runtime annotation inspection.

"""Provide view filters operations through ``_filter_json``."""

from __future__ import annotations
from collections.abc import Callable
import msgspec
import msgspec.json as msgspec_json


def _filter_json() -> Callable[..., str]:
    """
    Build the ``json`` template filter.

    Returns
    -------
    collections.abc.Callable[``...``, str]
        Callable serialising a value to a JSON string.
    """

    def jsonify(value: object, indent: int | None = None) -> str:
        """
        Serialise a value to a JSON string.

        Parameters
        ----------
        value : object
            Value to serialise or represent as text when encoding fails.
        indent : int | None, optional
            If provided, pretty-prints the output with the given
            indentation.

        Returns
        -------
        str
            JSON-encoded string, or ``str(value)`` when encoding or
            formatting fails.
        """
        try:
            encoded = msgspec_json.encode(value)
            if indent is not None:
                encoded = msgspec_json.format(encoded, indent=indent)
            return encoded.decode()
        except TypeError, ValueError, msgspec.EncodeError:
            return str(value)

    return jsonify
