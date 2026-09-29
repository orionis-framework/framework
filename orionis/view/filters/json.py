from __future__ import annotations
from typing import Any
import msgspec
import msgspec.json as msgspec_json

# ruff: noqa: ANN401

def _filter_json() -> Any:
    """
    Build the ``json`` template filter.

    Returns
    -------
    Any
        Callable serialising a value to a JSON string.
    """
    def jsonify(value: Any, indent: int | None = None) -> str:
        """
        Serialise a value to a JSON string.

        Parameters
        ----------
        value : Any
            Value to serialise.  Must be JSON-serialisable.
        indent : int | None, optional
            If provided, pretty-prints the output with the given
            indentation.

        Returns
        -------
        str
            JSON-encoded string, or ``str(value)`` when the value cannot
            be encoded.
        """
        try:
            encoded = msgspec_json.encode(value)
            if indent is not None:
                encoded = msgspec_json.format(encoded, indent=indent)
            return encoded.decode()
        except (TypeError, ValueError, msgspec.EncodeError):
            return str(value)

    return jsonify
