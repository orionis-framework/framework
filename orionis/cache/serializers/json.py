from __future__ import annotations
from typing import Any
import msgspec.json as _msgjson
from aiocache.serializers import BaseSerializer

class MsgspecSerializer(BaseSerializer):

    # ruff: noqa: ANN401

    DEFAULT_ENCODING = None  # raw bytes — no UTF-8 decoding overhead

    def dumps(self, value: Any) -> bytes:
        """
        Serialize *value* to UTF-8 encoded JSON bytes.

        Parameters
        ----------
        value : Any
            A JSON-serializable Python object.

        Returns
        -------
        bytes
            msgspec-encoded JSON payload.
        """
        return _msgjson.encode(value)

    def loads(self, data: bytes | str | float | None) -> Any:
        """
        Deserialize JSON *data* back to a Python object.

        Parameters
        ----------
        data : bytes | str | float | None
            Raw payload returned by the backend. Returns None when *data*
            is None (key not found).

        Returns
        -------
        Any
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
