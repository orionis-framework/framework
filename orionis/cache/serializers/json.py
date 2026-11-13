# ruff: noqa: ANN401
# Match the backend serializer protocol for arbitrary decoded cache values.
"""Serialize cache payloads through msgspec JSON encoding."""

from __future__ import annotations
from typing import Any
import msgspec.json as _msgjson
from aiocache.serializers import BaseSerializer


class MsgspecSerializer(BaseSerializer):
    """Serialize cache payloads through msgspec JSON encoding."""

    DEFAULT_ENCODING = None  # raw bytes — no UTF-8 decoding overhead
    """Default encoding used by ``MsgspecSerializer``."""

    def dumps(self, value: Any) -> bytes:
        """
        Serialize *value* to UTF-8 encoded JSON bytes.

        Parameters
        ----------
        value : typing.Any
            A JSON-serializable Python object.

        Returns
        -------
        bytes
            msgspec-encoded JSON payload.
        """
        return _msgjson.encode(value)

    def loads(self, data: object) -> Any:
        """
        Deserialize JSON *data* back to a Python object.

        Parameters
        ----------
        data : object
            Raw JSON text or byte buffer returned by the backend, a native
            counter value, or None when no stored payload exists.

        Returns
        -------
        typing.Any
            Decoded Python object, None when *data* is None, or *data*
            unchanged when the backend stored a native value.
        """
        if data is None:
            return None
        if isinstance(data, str):
            data = data.encode()
        elif not isinstance(data, (bytes, bytearray, memoryview)):
            # SimpleMemoryCache.increment() stores raw ints, skipping dumps().
            return data
        return _msgjson.decode(data)
